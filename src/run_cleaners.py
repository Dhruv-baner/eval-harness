# -*- coding: utf-8 -*-
import os, pickle, sys, time
import pandas as pd
import cleaners as C

from paths import DATA as D, CACHE
man = pd.read_csv(f'{D}/manifest.csv', keep_default_na=False)
paths = {r.messy_file: f"{D}/messy/{r.messy_file}" for r in man.itertuples()}
file2client = {r.messy_file: r.client_id for r in man.itertuples()}
DEV = {'harborview_dental', 'brightleaf_organics', 'lumen_software', 'sunrise_property'}
which = sys.argv[1:] or ['rules', 'fuzzy', 'ml', 'hybrid']


def slim(out):
    for o in out:
        r = o.pop('_raw', None)
        o['cells'] = r['cells'] if r else []
        o['ref_key'] = C.norm_key(r.get('ref')) if r and r.get('kind') == 'data' else ''
        o['in_dict'] = bool(r and r.get('kind') == 'data' and C.norm_label(r.get('label', ''), fix=True) in C.LABEL_DICT)
        o['label_norm'] = C.norm_label(r.get('label', ''), fix=True) if r and r.get('kind') == 'data' else ''
    return out


t0 = time.time()
if 'rules' in which:
    out = slim(C.run_rules(paths))
    pickle.dump(out, open(f'{CACHE}/rules.pkl', 'wb')); print('rules done', round(time.time() - t0), 's', flush=True)

if set(which) & {'fuzzy', 'ml', 'hybrid'}:
    allrows = C.prepare(paths)
    print('prepared', round(time.time() - t0), 's', flush=True)
    rm = pd.read_csv(f'{D}/truth/row_truth_map.csv', keep_default_na=False, dtype={'row_number': int, 'sheet': str})
    tr = pd.read_csv(f'{D}/truth/clean_ledger_all_clients.csv', dtype={'std_account_code': str}, keep_default_na=False)
    l2c = dict(zip(tr.line_id, tr.std_account_code))
    rmd = rm[rm.row_kind == 'data']
    lab = {(a, b, c): l2c[d] for a, b, c, d in zip(rmd.file, rmd.sheet, rmd.row_number, rmd.line_id)}
    data_by_file = {f: [r for r in rows if r['kind'] == 'data'] for f, rows in allrows.items()}
    dev_files = [f for f in allrows if file2client[f] in DEV]
    tuning = {'dev_clients': sorted(DEV)}
    def dev_acc(fn):
        ok = n = 0
        for f in dev_files:
            for r, p in zip(data_by_file[f], fn(f, data_by_file[f])):
                n += 1; ok += (p[0] == lab[(r['file'], r['sheet'], r['row_number'])])
        return ok / n
    if 'fuzzy' in which or 'hybrid' in which:
        grid = {}
        for c in (78, 82, 86, 90, 94):
            fzc = C.FuzzyMapper(cutoff=c)
            grid[c] = dev_acc(lambda f, data: [fzc.map(r) for r in data])
        best = max(grid, key=grid.get); tuning['fuzzy_cutoff_grid_dev_acc'] = grid; tuning['fuzzy_cutoff_chosen'] = best
        print('fuzzy cutoff grid (dev acc):', {k: round(v, 4) for k, v in grid.items()}, '-> chosen', best, flush=True)
        fz = C.FuzzyMapper(cutoff=best)
        out = C.finish(allrows, lambda f, data: [fz.map(r) for r in data])
        pickle.dump(slim(out), open(f'{CACHE}/fuzzy.pkl', 'wb')); print('fuzzy done', round(time.time() - t0), 's', flush=True)
    if 'ml' in which or 'hybrid' in which:
        models = {}
        for f in allrows:
            cl = file2client[f]
            pool = [g for g in allrows if g != f and (file2client[g] in DEV)]   # test clients: train on dev only; dev clients: leave-one-out within dev
            train = [r for g in pool for r in data_by_file[g]]
            y = [lab[(r['file'], r['sheet'], r['row_number'])] for r in train]
            m = C.MLMapper(); m.fit(train, y); models[f] = m
            print('  trained', ('DEV ' if cl in DEV else 'TEST'), cl, 'on', len(pool), 'dev clients,', len(train), 'rows', round(time.time() - t0), 's', flush=True)
        mlp = {f: models[f].predict(data_by_file[f]) for f in allrows}
        if 'ml' in which:
            out = C.finish(allrows, lambda f, data: mlp[f])
            pickle.dump(slim(out), open(f'{CACHE}/ml.pkl', 'wb')); print('ml done', round(time.time() - t0), 's', flush=True)
        # tune hybrid fuzzy cutoff on dev only
        fzh = C.FuzzyMapper(cutoff=70)
        hgrid = {}
        for c in (86, 90, 94, 98):
            hgrid[c] = dev_acc(lambda f, data, c=c: [C.hybrid_map(fzh, r, p, c) for r, p in zip(data, mlp[f])])
        hbest = max(hgrid, key=hgrid.get); tuning['hybrid_cutoff_grid_dev_acc'] = hgrid; tuning['hybrid_cutoff_chosen'] = hbest
        print('hybrid cutoff grid (dev acc):', {k: round(v, 4) for k, v in hgrid.items()}, '-> chosen', hbest, flush=True)
        out = C.finish(allrows, lambda f, data: [C.hybrid_map(fzh, r, p, hbest) for r, p in zip(data, mlp[f])])
        pickle.dump(slim(out), open(f'{CACHE}/hybrid.pkl', 'wb')); print('hybrid done', round(time.time() - t0), 's', flush=True)
    import json; json.dump(tuning, open(f'{CACHE}/tuning.json', 'w'), indent=1)
