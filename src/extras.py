# -*- coding: utf-8 -*-
import pickle, json, math, os, re
import numpy as np, pandas as pd
from ledger_parser import read_rows, find_header, header_roles, s as pstr

from paths import DATA as D, RESULTS as OUT, CACHE
CLEANERS = ['rules', 'fuzzy', 'ml', 'hybrid']
DEV = ['harborview_dental', 'brightleaf_organics', 'lumen_software', 'sunrise_property']
TEST = ['northgate_construction', 'alder_finch_llp', 'rivera_restaurants', 'kestrel_logistics']
CONF_MIN, FIX_MIN, ERR_MIN = 0.1, 0.6, 8.0   # default economics: minutes to confirm a correct suggestion / fix a wrong or missing one / minutes-equivalent per uncaught error

rm = pd.read_csv(f'{D}/truth/row_truth_map.csv', keep_default_na=False, dtype={'row_number': int, 'sheet': str})
tr = pd.read_csv(f'{D}/truth/clean_ledger_all_clients.csv', dtype={'std_account_code': str}, keep_default_na=False)
tr['net_cents'] = ((tr.debit - tr.credit) * 100).round().astype(int)
coa = pd.read_csv(f'{D}/standard_chart_of_accounts.csv', dtype={'std_account_code': str})
man = pd.read_csv(f'{D}/manifest.csv', keep_default_na=False)
NAME = dict(zip(coa.std_account_code, coa.std_account_name)); W = dict(zip(coa.std_account_code, coa.error_cost_weight))
FY0 = {r.client_id: pd.Timestamp(r.fiscal_year_start) for r in man.itertuples()}
LABEL_TAGS = {'label_variant', 'missing_account', 'uncategorized_label', 'legacy_label', 'mojibake'}


def load(name):
    df = pd.DataFrame(pickle.load(open(f'{CACHE}/{name}.pkl', 'rb')))
    df['sheet'] = df.sheet.fillna('').astype(str)
    df = df.merge(rm, on=['file', 'sheet', 'row_number'], how='left')
    t = tr[['line_id', 'posting_date', 'std_account_code', 'net_cents']].rename(columns={'std_account_code': 'true_code'})
    df = df.merge(t, on='line_id', how='left')
    df['tags'] = df.error_types.map(lambda s: [x for x in s.split(';') if x] if isinstance(s, str) else [])
    return df


frames = {n: load(n) for n in CLEANERS}
base = frames['hybrid']
key = lambda d: d.client_id + '|' + d.file + '|' + d.sheet + '|' + d.row_number.astype(str)

# ------------------------------------------------------------------ evaluation table (original data rows)
B = base[(base.row_kind == 'data') & (base.is_duplicate == 0)][['client_id', 'file', 'sheet', 'row_number', 'ref_key', 'true_code', 'posting_date', 'net_cents', 'line_id']].copy()
B['rk'] = key(B)
B['w'] = B.true_code.map(W).astype(float)
B['abs_net'] = B.net_cents.abs().astype(float)
B['grp'] = np.where(B.ref_key != '', B.client_id + '|' + B.ref_key, B.rk)
for n, df in frames.items():
    d = df[(df.row_kind == 'data') & (df.is_duplicate == 0)].copy(); d['rk'] = key(d)
    d = d.set_index('rk').reindex(B.rk)
    B[f'c_{n}'] = (d.pred_code.values == B.true_code.values)
    dt = d.date.map(lambda x: str(x) if x is not None and not pd.isna(x) else None).values == B.posting_date.values
    am = d.net.notna().values & ((d.net.fillna(0).values - B.net_cents.values).__abs__() <= 1)
    B[f'a_{n}'] = B[f'c_{n}'] & dt & am
    B[f'conf_{n}'] = d.conf.values
    B[f'um_{n}'] = d.pred_code.isna().values

# ------------------------------------------------------------------ bootstrap (resample documents within client)
def bootstrap(clients, reps=400, seed=7):
    rng = np.random.default_rng(seed)
    parts = []
    for c in clients:
        g = B[B.client_id == c]
        agg = g.groupby('grp').agg(n=('w', 'size'), w=('w', 'sum'), ab=('abs_net', 'sum'),
                                   **{f'c_{n}': (f'c_{n}', 'sum') for n in CLEANERS},
                                   **{f'a_{n}': (f'a_{n}', 'sum') for n in CLEANERS})
        for n in CLEANERS:
            agg[f'wc_{n}'] = g.assign(x=g.w * g[f'c_{n}']).groupby('grp').x.sum().reindex(agg.index).values
            agg[f'ac_{n}'] = g.assign(x=g.abs_net * g[f'c_{n}']).groupby('grp').x.sum().reindex(agg.index).values
        parts.append(agg)
    draws = {k: [] for k in ['acc', 'cost', 'dollar', 'fully']}
    for _ in range(reps):
        tot = dict(n=0.0, w=0.0, **{f'c_{n}': 0.0 for n in CLEANERS}, **{f'wc_{n}': 0.0 for n in CLEANERS}, **{f'a_{n}': 0.0 for n in CLEANERS})
        dol = {n: [] for n in CLEANERS}
        for agg in parts:
            cnt = rng.multinomial(len(agg), np.full(len(agg), 1 / len(agg)))
            tot['n'] += float(cnt @ agg.n.values); tot['w'] += float(cnt @ agg.w.values)
            ab = float(cnt @ agg.ab.values)
            for n in CLEANERS:
                tot[f'c_{n}'] += float(cnt @ agg[f'c_{n}'].values); tot[f'wc_{n}'] += float(cnt @ agg[f'wc_{n}'].values)
                tot[f'a_{n}'] += float(cnt @ agg[f'a_{n}'].values)
                dol[n].append(float(cnt @ agg[f'ac_{n}'].values) / max(ab, 1))
        draws['acc'].append([tot[f'c_{n}'] / tot['n'] for n in CLEANERS])
        draws['cost'].append([tot[f'wc_{n}'] / tot['w'] for n in CLEANERS])
        draws['dollar'].append([np.mean(dol[n]) for n in CLEANERS])
        draws['fully'].append([tot[f'a_{n}'] / tot['n'] for n in CLEANERS])
    res = {}
    for k, v in draws.items():
        v = np.array(v)
        res[k] = {n: dict(mean=float(v[:, i].mean()), lo=float(np.percentile(v[:, i], 2.5)), hi=float(np.percentile(v[:, i], 97.5))) for i, n in enumerate(CLEANERS)}
        hi = CLEANERS.index('hybrid')
        res[k]['hybrid_minus'] = {n: dict(mean=float((v[:, hi] - v[:, i]).mean()), lo=float(np.percentile(v[:, hi] - v[:, i], 2.5)),
                                          hi=float(np.percentile(v[:, hi] - v[:, i], 97.5))) for i, n in enumerate(CLEANERS) if n != 'hybrid'}
    return res


boot = {'test': bootstrap(TEST), 'dev': bootstrap(DEV)}
print('bootstrap done', flush=True)

# ------------------------------------------------------------------ fine threshold curves (for the economics slider)
TH = np.round(np.arange(0, 1.0001, 0.01), 2)
def curves(clients):
    out = {}
    sub = B[B.client_id.isin(clients)]
    for n in CLEANERS:
        conf = sub[f'conf_{n}'].fillna(0).values; um = sub[f'um_{n}'].values; ok = sub[f'c_{n}'].values; w = sub.w.values
        N = len(sub); ct = int(ok.sum()); pts = []
        for t in TH:
            acc_mask = (conf >= t) & ~um if t > 0 else ~um
            wrong = acc_mask & ~ok
            qc = ct - (int(acc_mask.sum()) - int(wrong.sum()))     # correct suggestions left in the review queue
            pts.append([float(t), int(acc_mask.sum()), int(wrong.sum()), float(w[wrong].sum()), int(qc)])
        out[n] = dict(rows=int(N), weight_total=float(w.sum()), correct_total=ct, points=pts)   # [threshold, auto_accepted, wrong_auto, wrong_auto_weight, queue_correct]
    return out

fine = {'test': curves(TEST), 'dev': curves(DEV)}
def cost_pt(c, p, conf=CONF_MIN, fix=FIX_MIN, err=ERR_MIN):
    q = c['rows'] - p[1]
    return p[4] * conf + (q - p[4]) * fix + p[2] * err
def best_t(n, split):
    c = fine[split][n]; costs = [(p[0], cost_pt(c, p)) for p in c['points']]
    return min(costs, key=lambda z: z[1])
op = {n: dict(dev_best_threshold=best_t(n, 'dev')[0], dev_cost_per_row=best_t(n, 'dev')[1] / fine['dev'][n]['rows']) for n in CLEANERS}
T_OP = op['hybrid']['dev_best_threshold']
print('operating threshold (hybrid, chosen on dev):', T_OP, flush=True)
for n in CLEANERS:
    c = fine['test'][n]; p = [z for z in c['points'] if abs(z[0] - op[n]['dev_best_threshold']) < 1e-9][0]
    op[n].update(test_review_rate=1 - p[1] / c['rows'], test_wrong_auto_rate=p[2] / c['rows'], test_accuracy_of_auto=1 - p[2] / max(p[1], 1),
                 test_queue_suggestion_correct=p[4] / max(c['rows'] - p[1], 1))

# ------------------------------------------------------------------ cold-start replay
def cold_start(n, clients, T, audit_p=0.05):
    df = frames[n]
    M = df[(df.row_kind == 'data') & (df.is_duplicate == 0) & df.client_id.isin(clients)].copy()
    M['pd'] = pd.to_datetime(M.posting_date)
    months, per_client = {}, {}
    for cid, g in M.groupby('client_id'):
        g = g.sort_values(['pd', 'line_id']); mem, mem_a, amb = {}, {}, set()
        rng = np.random.default_rng(abs(hash(cid)) % (2 ** 32) if False else sum(map(ord, cid)))
        f0 = FY0[cid]
        for r in g.itertuples():
            mi = (r.pd.year - f0.year) * 12 + r.pd.month - f0.month + 1
            if mi < 1 or mi > 12: continue
            k = r.label_norm if r.label_norm else None
            pred = r.pred_code if isinstance(r.pred_code, str) else None
            conf = r.conf if pred is not None else 0.0
            m = months.setdefault(mi, dict(n=0, rev_base=0, wrong_base=0, rev_mem=0, wrong_mem=0, learned=0, rev_audit=0, wrong_audit=0, audit_flagged=0))
            pc = per_client.setdefault(cid, {}).setdefault(mi, dict(n=0, rev_mem=0, rev_base=0, rev_audit=0))
            m['n'] += 1; pc['n'] += 1
            confident = pred is not None and conf >= T
            # 1) baseline: no memory
            if confident:
                m['wrong_base'] += int(pred != r.true_code)
            else:
                m['rev_base'] += 1; pc['rev_base'] += 1
            # 2) client memory (human confirms an unfamiliar label once)
            if k is not None and k in mem:
                m['wrong_mem'] += int(mem[k] != r.true_code)
            elif confident:
                m['wrong_mem'] += int(pred != r.true_code)
            else:
                m['rev_mem'] += 1; pc['rev_mem'] += 1
                if k is not None: mem[k] = r.true_code; m['learned'] += 1
            # 3) memory + audit sampling (contradicted labels are retired from memory)
            if k is not None and k in mem_a and k not in amb:
                if rng.random() < audit_p:
                    m['rev_audit'] += 1; pc['rev_audit'] += 1
                    if mem_a[k] != r.true_code: amb.add(k); m['audit_flagged'] += 1
                else:
                    m['wrong_audit'] += int(mem_a[k] != r.true_code)
            elif confident:
                m['wrong_audit'] += int(pred != r.true_code)
            else:
                m['rev_audit'] += 1; pc['rev_audit'] += 1
                if k is not None and k not in amb: mem_a[k] = r.true_code
    return dict(months=[dict(month=k, **months[k]) for k in sorted(months)],
                per_client={c: [dict(month=k, **v) for k, v in sorted(d.items())] for c, d in per_client.items()})

cold = {n: {sp: cold_start(n, cl, op['hybrid']['dev_best_threshold'] if n == 'hybrid' else op[n]['dev_best_threshold'])
            for sp, cl in (('all', DEV + TEST), ('test', TEST))} for n in ['rules', 'hybrid']}
print('cold-start done', flush=True)

# ------------------------------------------------------------------ header/role helpers
def file_meta(fname):
    path = f"{D}/messy/{fname}"; out = {}
    for sheet, rows in read_rows(path):
        hi, roles = find_header(rows)
        out[sheet] = dict(header_row=rows[hi][0] if hi is not None else None, roles=roles or {},
                          header=[pstr(c) for c in rows[hi][1]] if hi is not None else [])
        if len(out) >= 1: break
    return out

META = {f: file_meta(f) for f in man.messy_file}
TAGROLE = lambda t: (['label', 'code', 'section'] if t.split(':')[0] in ('label_variant', 'missing_account', 'uncategorized_label', 'legacy_label') else
                     ['label', 'desc', 'name'] if t == 'mojibake' else
                     ['date'] if t.startswith('date') or t == 'missing_date' else
                     ['debit', 'credit', 'amount'] if t in ('sign_flip', 'amount_digit_error', 'amount_format', 'credit_as_negative_debit', 'drcr_suffix', 'swapped_direction') else
                     ['desc'] if t in ('blank_description', 'whitespace') else [])

def highlights(file, sheet, tags, cells):
    roles = (META[file].get(sheet) or list(META[file].values())[0])['roles']
    hl = []
    for t in tags:
        cols = [roles[r] for r in TAGROLE(t) if r in roles and roles[r] < len(cells)]
        if t.startswith('duplicate'): hl.append([-1, t]); continue
        for c in cols:
            if not any(h[0] == c for h in hl): hl.append([c, t])
    return hl

# ------------------------------------------------------------------ messy-file viewer
viewer = {}
rmi = rm.set_index(['file', 'sheet', 'row_number'])
for f in man.messy_file:
    d = base[base.file == f]
    first_sheet = sorted(d.sheet.unique())[0]
    d = d[d.sheet == first_sheet].sort_values('row_number')
    d = d[d.row_number <= 4000]
    head = d[d.row_number <= 12]
    # most varied 26-row window of visible injected errors after the header
    INT = lambda tags: {t.split(':')[0] for t in tags} - {'whitespace', 'blank_description', 'legacy_label'}
    sets = [INT(t) for t in d.tags]
    best, bs = 0, -1
    for i in range(14, max(15, len(d) - 26)):
        ws = sets[i:i + 26]
        sc_ = sum(1 for s_ in ws if s_) + 3 * len(set().union(*ws))
        if sc_ > bs: bs, best = sc_, i
    win = d.iloc[best:best + 26]
    def pack(x):
        return [dict(n=int(r.row_number), cells=list(r.cells), kind=r.row_kind, tags=list(r.tags), hl=highlights(f, first_sheet, r.tags, list(r.cells))) for r in x.itertuples()]
    viewer[f] = dict(sheet=first_sheet, header=META[f][first_sheet]['header'], head=pack(head), window=pack(win), window_start=int(win.row_number.min()) if len(win) else 0)

# ------------------------------------------------------------------ inspector sample
rng = np.random.default_rng(11)
allrows = base[(base.row_kind == 'data')].copy(); allrows['rk'] = key(allrows)
ins = []
for cid, g in allrows.groupby('client_id'):
    g = g.copy()
    g['wrong_h'] = False
    orig = g[g.is_duplicate == 0]
    wrong_ix = orig.index[(orig.pred_code.values != orig.true_code.values)]
    nl = g.index[g.tags.map(lambda t: any(x.split(':')[0] not in LABEL_TAGS and x != 'legacy_label' for x in t))]
    dups = g.index[g.is_duplicate == 1]
    clean = g.index[g.tags.map(lambda t: len(t) == 0)]
    take = []
    for ix, k in ((wrong_ix, 26), (nl, 22), (dups, 5), (clean, 14)):
        ix = [i for i in ix if i not in take]
        if len(ix): take += list(rng.choice(ix, min(k, len(ix)), replace=False))
    for i in take:
        r = g.loc[i]; k = r.client_id + '|' + r.file + '|' + r.sheet + '|' + str(r.row_number)
        preds = {}
        for n in CLEANERS:
            q = frames[n]; row = q[(q.file == r.file) & (q.sheet == r.sheet) & (q.row_number == r.row_number)].iloc[0]
            preds[n] = [row.pred_code if isinstance(row.pred_code, str) else None, round(float(row.conf), 3), row.kind_pred]
        t = tr[tr.line_id == r.line_id].iloc[0]
        h = frames['hybrid']
        ins.append(dict(client=cid, file=r.file, sheet=r.sheet, row=int(r.row_number), cells=list(r.cells), tags=list(r.tags),
                        hl=highlights(r.file, r.sheet, r.tags, list(r.cells)), dup=int(r.is_duplicate),
                        truth=dict(code=r.true_code, name=NAME[r.true_code], date=t.posting_date, net=float(t.net_cents) / 100),
                        preds=preds, hyb_date=str(r.date) if r.date is not None and not pd.isna(r.date) else None,
                        hyb_net=None if pd.isna(r.net) else float(r.net) / 100))
print('inspector rows', len(ins), flush=True)

tag_counts = {}
for s_ in rm[rm.row_kind == 'data'].error_types:
    for t_ in set(x.split(':')[0] for x in s_.split(';') if x): tag_counts[t_] = tag_counts.get(t_, 0) + 1
extras = dict(tagCounts=tag_counts, bootstrap=boot, fine_curves=fine, operating=op, economics_defaults=dict(confirm_min=CONF_MIN, fix_min=FIX_MIN, error_min_each=ERR_MIN),
              cold_start=cold, viewer=viewer, inspector=ins, headers={f: META[f] for f in META}, coa={c: NAME[c] for c in NAME})
json.dump(extras, open(f'{OUT}/extras.json', 'w'), default=lambda o: o.item() if hasattr(o, 'item') else str(o))
print('extras.json', os.path.getsize(f'{OUT}/extras.json') // 1024, 'KB')
for sp in ('test', 'dev'):
    print(sp, {n: (round(boot[sp]['acc'][n]['mean'], 4), round(boot[sp]['acc'][n]['lo'], 4), round(boot[sp]['acc'][n]['hi'], 4)) for n in CLEANERS})
print('hybrid minus others (test acc):', {k: (round(v['mean'], 4), round(v['lo'], 4), round(v['hi'], 4)) for k, v in boot['test']['acc']['hybrid_minus'].items()})
print('operating:', json.dumps(op, default=float)[:900])
for n in ('hybrid', 'rules'):
    m = cold[n]['all']['months']
    print(n, 'review base/mem by month:', [(x['month'], round(x['rev_base'] / x['n'], 3), round(x['rev_mem'] / x['n'], 3)) for x in m])
    print(n, 'wrong base/mem/audit m12:', round(m[-1]['wrong_base']/m[-1]['n'],4), round(m[-1]['wrong_mem']/m[-1]['n'],4), round(m[-1]['wrong_audit']/m[-1]['n'],4), '| review audit by month:', [round(x['rev_audit']/x['n'],3) for x in m])
