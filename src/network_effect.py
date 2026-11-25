"""Network effect: how does account accuracy change with the number of other firms the agent has learned from?
Leave-one-firm-out. For each target firm, train the ML fallback on k other firms (at most 5,000 rows per firm),
average over random subsets, and score the hybrid cleaner on the target. Separate from the dev/test split."""
import json, os, sys, time
import numpy as np, pandas as pd
import cleaners as C
from paths import DATA as D, RESULTS

CAP, KS, REPS = 5000, [0, 1, 2, 4, 7], {0: 1, 1: 3, 2: 3, 4: 2, 7: 1}
man = pd.read_csv(f'{D}/manifest.csv', keep_default_na=False)
paths = {r.messy_file: f"{D}/messy/{r.messy_file}" for r in man.itertuples()}
f2c = {r.messy_file: r.client_id for r in man.itertuples()}
allrows = C.prepare(paths)
rm = pd.read_csv(f'{D}/truth/row_truth_map.csv', keep_default_na=False, dtype={'row_number': int, 'sheet': str})
tr = pd.read_csv(f'{D}/truth/clean_ledger_all_clients.csv', dtype={'std_account_code': str}, keep_default_na=False)
l2c = dict(zip(tr.line_id, tr.std_account_code))
rd = rm[rm.row_kind == 'data']
lab = {(a, b, c): l2c[d] for a, b, c, d in zip(rd.file, rd.sheet, rd.row_number, rd.line_id)}
meta = {(a, b, c): (dup, et) for a, b, c, dup, et in zip(rd.file, rd.sheet, rd.row_number, rd.is_duplicate, rd.error_types)}
LABEL_TAGS = {'label_variant', 'missing_account', 'uncategorized_label', 'legacy_label', 'mojibake'}
data = {f: [r for r in rows if r['kind'] == 'data'] for f, rows in allrows.items()}
rng = np.random.default_rng(5)
fz = C.FuzzyMapper(cutoff=70)
todo = sys.argv[1:]
PART = os.path.join(RESULTS, '.network_parts'); os.makedirs(PART, exist_ok=True)
t0 = time.time()
for f in allrows:
    cid = f2c[f]; others = [g for g in allrows if g != f]
    if (todo and cid not in todo) or os.path.exists(f'{PART}/{cid}.json'): continue
    out = {cid: {k: [] for k in KS}}
    rows = [r for r in data[f] if meta[(r['file'], r['sheet'], r['row_number'])][0] == 0]
    truth = [lab[(r['file'], r['sheet'], r['row_number'])] for r in rows]
    tags = [[x.split(':')[0] for x in meta[(r['file'], r['sheet'], r['row_number'])][1].split(';') if x] for r in rows]
    cs = np.array([(not C.norm_label(r.get('label', ''), fix=True) in C.LABEL_DICT) and not any(t in LABEL_TAGS for t in tg) for r, tg in zip(rows, tags)])
    for k in KS:
        for rep in range(REPS[k]):
            if k == 0:
                preds = [(None, 0.0, 'ml')] * len(rows)
            else:
                subset = others if k == 7 else list(rng.choice(others, k, replace=False))
                train = []
                for g in subset:
                    idx = rng.permutation(len(data[g]))[:CAP]; train += [data[g][i] for i in idx]
                y = [lab[(r['file'], r['sheet'], r['row_number'])] for r in train]
                m = C.MLMapper(n_train=len(train) + 1); m.fit(train, y)
                preds = m.predict(rows)
            hp = [C.hybrid_map(fz, r, p, 86) for r, p in zip(rows, preds)]
            ok = np.array([p[0] == t for p, t in zip(hp, truth)]); conf = np.array([p[1] for p in hp]); mapped = np.array([p[0] is not None for p in hp])
            hi = (conf >= 0.8) & mapped
            out[cid][k].append(dict(acc=float(ok.mean()), acc_client_vocab=float(ok[cs].mean()) if cs.any() else None,
                                    coverage_80=float(hi.mean()), acc_at_80=float(ok[hi].mean()) if hi.any() else None))
        print(cid, k, round(out[cid][k][0]['acc'], 4), round(time.time() - t0), 's', flush=True)
    json.dump({str(k): v for k, v in out[cid].items()}, open(f'{PART}/{cid}.json', 'w'))
parts = {c: json.load(open(f'{PART}/{c}.json')) for c in f2c.values() if os.path.exists(f'{PART}/{c}.json')}
if len(parts) < len(set(f2c.values())):
    print('waiting for', sorted(set(f2c.values()) - set(parts))); sys.exit(0)
res = {'ks': KS, 'cap_rows_per_firm': CAP, 'reps': REPS, 'clients': {}}
for cid, d in parts.items():
    res['clients'][cid] = {k: {m: (float(np.mean([x[m] for x in v if x[m] is not None])) if any(x[m] is not None for x in v) else None) for m in v[0]} for k, v in d.items()}
res['mean'] = {str(k): {m: float(np.mean([res['clients'][c][str(k)][m] for c in res['clients'] if res['clients'][c][str(k)][m] is not None])) for m in ('acc', 'acc_client_vocab', 'coverage_80', 'acc_at_80')} for k in KS}
json.dump(res, open(f'{RESULTS}/network.json', 'w'))
print('network.json written', json.dumps(res['mean']))
