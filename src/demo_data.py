"""Live console data: per client, a curated sample of raw rows with every pipeline stage precomputed (hybrid cleaner),
file-level baseline stats, and the effect of confirming each unfamiliar client label."""
import json, pickle, os
import numpy as np, pandas as pd
from paths import DATA as D, RESULTS, CACHE

rm = pd.read_csv(f'{D}/truth/row_truth_map.csv', keep_default_na=False, dtype={'row_number': int, 'sheet': str})
tr = pd.read_csv(f'{D}/truth/clean_ledger_all_clients.csv', dtype={'std_account_code': str}, keep_default_na=False)
coa = pd.read_csv(f'{D}/standard_chart_of_accounts.csv', dtype={'std_account_code': str})
man = pd.read_csv(f'{D}/manifest.csv', keep_default_na=False)
ext = json.load(open(f'{RESULTS}/extras.json'))
T = ext['operating']['hybrid']['dev_best_threshold']
NAME = dict(zip(coa.std_account_code, coa.std_account_name))
tr['net'] = ((tr.debit - tr.credit) * 100).round().astype(int)
df = pd.DataFrame(pickle.load(open(f'{CACHE}/hybrid.pkl', 'rb'))); df['sheet'] = df.sheet.fillna('').astype(str)
df = df.merge(rm, on=['file', 'sheet', 'row_number'], how='left').merge(
    tr[['line_id', 'std_account_code', 'posting_date', 'net']].rename(columns={'std_account_code': 'true_code', 'net': 'true_net'}), on='line_id', how='left')
df['tags'] = df.error_types.map(lambda s: [x for x in s.split(';') if x] if isinstance(s, str) else [])
df['conf'] = df.conf.fillna(0.0)
rng = np.random.default_rng(3)
cut = lambda c: [str(x)[:54] for x in c[:14]]
s_ = lambda v: None if v is None or (isinstance(v, float) and np.isnan(v)) else str(v)

out = dict(threshold=T, accounts=[[c, NAME[c]] for c in coa.std_account_code], clients={})
for m in man.itertuples():
    f, cid = m.messy_file, m.client_id
    d = df[df.file == f].sort_values(['sheet', 'row_number'])
    sheet0 = sorted(d.sheet.unique())[0]
    meta = ext['headers'][f][sheet0]; roles = meta['roles']; hdr_row = meta['header_row'] or 1
    o = d[(d.row_kind == 'data') & (d.is_duplicate == 0)]
    # ---- label memory effects (whole file)
    labels = []
    for L, g in o[o.label_norm != ''].groupby('label_norm'):
        bt = g.true_code.value_counts()
        correct = int((g.pred_code == g.true_code).sum()); review = int((g.conf < T).sum()); wa = int(((g.conf >= T) & (g.pred_code != g.true_code)).sum())
        if review + (len(g) - correct) == 0: continue
        pm = g.pred_code.dropna().value_counts()
        labels.append(dict(label=L, n=int(len(g)), by_true={k: int(v) for k, v in bt.head(6).items()}, correct=correct, review=review, wrong_auto=wa,
                           pred=(pm.index[0] if len(pm) else None), conf=round(float(g.conf.mean()), 3),
                           amount=round(float(g.true_net.abs().sum()) / 100, 0)))
    labels.sort(key=lambda x: -(x['review'] + x['n'] - x['correct']))
    labels = labels[:40]
    base = dict(n=int(len(o)), correct=int((o.pred_code == o.true_code).sum()), review=int((o.conf < T).sum()),
                wrong_auto=int(((o.conf >= T) & (o.pred_code != o.true_code)).sum()))
    # ---- sample windows (all from the first sheet)
    d0 = d[d.sheet == sheet0].reset_index(drop=True); pos = {n: i for i, n in enumerate(d0.row_number)}
    picks = set(range(1, min(hdr_row + 3, 9)))
    def around(rn, r=1):
        i = pos[rn]; return {d0.row_number[j] for j in range(max(0, i - r), min(len(d0), i + r + 1))}
    D0 = d0[d0.row_kind == 'data']
    for lb in [x['label'] for x in labels[:4]]:
        c = D0[(D0.label_norm == lb) & (D0.is_duplicate == 0)]
        if len(c): picks |= around(int(c.iloc[int(rng.integers(len(c)))].row_number))
    dups = D0[D0.is_duplicate == 1]
    if len(dups):
        r = dups.iloc[int(rng.integers(len(dups)))]; picks |= around(int(r.row_number))
        orig = D0[(D0.line_id == r.line_id) & (D0.is_duplicate == 0)]
        if len(orig): picks |= {int(orig.iloc[0].row_number)}
    fl = D0[(D0.flag_unbalanced == True) | (D0.flip_repaired == True)] if 'flag_unbalanced' in D0 else D0.iloc[0:0]
    if len(fl):
        r = fl.iloc[int(rng.integers(len(fl)))]; picks |= set(int(x) for x in D0[(D0.ref_key == r.ref_key)].row_number.head(6))
    for tag in ('uncategorized_label', 'missing_account', 'date_alt_format', 'credit_as_negative_debit', 'amount_format', 'missing_date', 'sign_flip'):
        c = D0[D0.tags.map(lambda t, tag=tag: any(x.split(':')[0] == tag for x in t))]
        if len(c): picks |= around(int(c.iloc[int(rng.integers(len(c)))].row_number), 0)
    junk = d0[(d0.row_kind.isin(['subtotal', 'section_total', 'section_header', 'repeat_header', 'grand_total'])) & (d0.row_number > hdr_row)]
    if len(junk): picks |= around(int(junk.iloc[min(2, len(junk) - 1)].row_number), 1)
    picks = sorted(p for p in picks if p in pos)[:46]
    rows = []
    for rn in picks:
        r = d0.iloc[pos[rn]]; data = r.row_kind == 'data'
        rec = dict(n=int(rn), cells=cut(list(r.cells)), kind=r.row_kind, tags=list(r.tags) if data else [])
        if data:
            rec.update(label=r.label_norm, pred=r.pred_code if isinstance(r.pred_code, str) else None, conf=round(float(r.conf), 3), src=r.src or '',
                       date=s_(r.date), net=None if pd.isna(r.net) else round(float(r.net) / 100, 2), dup=bool(r.kind_pred == 'dup'),
                       flag=bool(r.flag_unbalanced), fixed=bool(r.flip_repaired), filled=bool(r.date_filled), ref=r.ref_key,
                       true=r.true_code, true_date=r.posting_date, true_net=round(float(r.true_net) / 100, 2))
        rows.append(rec)
    out['clients'][cid] = dict(file=f, sheet=sheet0, layout=m.export_layout, currency=m.currency, messiness=m.messiness, roles=roles, header=meta['header'],
                               base=base, labels=labels, rows=rows)
    print(cid, len(rows), 'rows', len(labels), 'labels', base)
json.dump(out, open(f'{RESULTS}/demo.json', 'w'), separators=(',', ':'), default=lambda o: o.item() if hasattr(o, 'item') else str(o))
print('demo.json', os.path.getsize(f'{RESULTS}/demo.json') // 1024, 'KB')
