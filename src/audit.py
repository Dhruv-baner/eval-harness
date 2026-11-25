"""Audit trail data: for every client and account, the cleaned trial-balance figure, the true figure,
where the difference comes from, and the raw rows behind the number (hybrid cleaner)."""
import json, pickle, os
import numpy as np, pandas as pd
from paths import DATA as D, RESULTS, CACHE

rm = pd.read_csv(f'{D}/truth/row_truth_map.csv', keep_default_na=False, dtype={'row_number': int, 'sheet': str})
tr = pd.read_csv(f'{D}/truth/clean_ledger_all_clients.csv', dtype={'std_account_code': str}, keep_default_na=False)
tb = pd.read_csv(f'{D}/truth/trial_balance_truth.csv', dtype={'std_account_code': str})
coa = pd.read_csv(f'{D}/standard_chart_of_accounts.csv', dtype={'std_account_code': str})
man = pd.read_csv(f'{D}/manifest.csv', keep_default_na=False)
NAME = dict(zip(coa.std_account_code, coa.std_account_name)); NAME['UNMAPPED'] = 'Unmapped'
CUR = dict(zip(man.client_id, man.currency))
df = pd.DataFrame(pickle.load(open(f'{CACHE}/hybrid.pkl', 'rb'))); df['sheet'] = df.sheet.fillna('').astype(str)
df = df.merge(rm, on=['file', 'sheet', 'row_number'], how='left').merge(tr[['line_id', 'std_account_code']].rename(columns={'std_account_code': 'true_code'}), on='line_id', how='left')
df['tags'] = df.error_types.map(lambda s: [x for x in s.split(';') if x] if isinstance(s, str) else [])
g_all = df[(df.kind_pred == 'data') & df.net.notna()].copy()
g_all['pred'] = g_all.pred_code.where(g_all.pred_code.notna(), 'UNMAPPED')
g_all['amt'] = g_all.net / 100.0
cut = lambda c: [str(x)[:46] for x in c[:12]]

def sample(r):
    return dict(n=int(r.row_number), sheet=r.sheet, cells=cut(list(r.cells)), true=r.true_code, pred=r.pred, conf=round(float(r.conf), 3), src=r.src or '', tags=list(r.tags), amt=round(float(r.amt), 2))

out = {}
for cid, g in g_all.groupby('client_id'):
    t = tb[tb.client_id == cid].set_index('std_account_code').net_in_export
    cleaned = g.groupby('pred').amt.sum()
    accts = []
    for code in sorted(set(cleaned.index) | set(t.index)):
        rin = g[g.pred == code]; rtrue = g[g.true_code == code]
        w_in = rin[rin.true_code != code]; w_out = rtrue[rtrue.pred != code]
        gi = w_in.groupby(['label_norm', 'true_code']).agg(n=('amt', 'size'), amount=('amt', lambda x: x.abs().sum())).reset_index().sort_values('amount', ascending=False).head(4)
        go = w_out.groupby(['label_norm', 'pred']).agg(n=('amt', 'size'), amount=('amt', lambda x: x.abs().sum())).reset_index().sort_values('amount', ascending=False).head(4)
        s = []
        if len(rin):
            s += list(rin.assign(a=rin.amt.abs()).sort_values('a', ascending=False).head(2).itertuples())
            s += list(rin.sort_values('conf').head(2).itertuples())
            s += list(w_in.assign(a=w_in.amt.abs()).sort_values('a', ascending=False).head(2).itertuples())
        seen, samp = set(), []
        for r in s:
            if r.row_number in seen: continue
            seen.add(r.row_number); samp.append(sample(r))
            if len(samp) == 5: break
        c = float(cleaned.get(code, 0.0)); tv = float(t.get(code, 0.0))
        accts.append(dict(code=code, name=NAME.get(code, code), cleaned=round(c, 2), truth=round(tv, 2), diff=round(c - tv, 2), rows=int(len(rin)),
                          conf=round(float(rin.conf.mean()), 3) if len(rin) else None, src={k: int(v) for k, v in rin.src.value_counts().items()},
                          wrong_in=[dict(label=r.label_norm, true=r.true_code, n=int(r.n), amount=round(float(r.amount), 2)) for r in gi.itertuples()],
                          wrong_out=[dict(label=r.label_norm, pred=r.pred, n=int(r.n), amount=round(float(r.amount), 2)) for r in go.itertuples()],
                          samples=samp))
    accts.sort(key=lambda a: -abs(a['diff']))
    out[cid] = dict(currency=CUR[cid], accounts=accts)
json.dump(out, open(f'{RESULTS}/audit.json', 'w'), separators=(',', ':'), default=lambda o: o.item() if hasattr(o, 'item') else str(o))
print('audit.json', os.path.getsize(f'{RESULTS}/audit.json') // 1024, 'KB', {k: len(v['accounts']) for k, v in out.items()})
