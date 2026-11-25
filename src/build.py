# -*- coding: utf-8 -*-
import os, csv, json, sys
from collections import defaultdict, Counter
from datetime import timedelta
import numpy as np
from refdata import *
from sim import Sim
from clients import CLIENTS
import export as ex

from paths import DATA as OUT, CACHE
for sub in ('messy', 'truth'):
    os.makedirs(f'{OUT}/{sub}', exist_ok=True)

only = sys.argv[1:]  # optional client ids for quick iterations
truth_all, rowmap, tb_rows, manifest, stats = [], [], [], [], {}

for cfg in CLIENTS:
    if only and cfg['id'] not in only:
        continue
    sim = Sim(cfg).run()
    ents = sorted(sim.ents, key=lambda e: (e['date'], e['seq']))
    truth = []
    for i, e in enumerate(ents, 1):
        txn = f"{cfg['pfx']}-{i:06d}"
        for k, (code, dr, cr, desc, cp) in enumerate(e['lines'], 1):
            truth.append(dict(client_id=cfg['id'], txn_id=txn, line_id=f"{txn}-{k}", date=e['date'], src=e['src'], ref=e['ref'],
                              code=code, dr=dr, cr=cr, desc=desc, cp=cp, in_export=True, note='',
                              ambig=int(code in cfg['merged'])))
    used = {t['code'] for t in truth}
    rng = np.random.default_rng(cfg['seed'] + 999)
    L = ex.build_labels(cfg, used, rng)
    M = ex.LEVELS[cfg['mess']]
    fmt = cfg['fmt']

    if fmt == 'cashbook':
        for t in truth:
            if t['src'] == 'OPEN': t['in_export'], t['note'] = False, 'opening_balance_not_in_cashbook'
            elif t['code'] == '1000': t['in_export'], t['note'] = False, 'implied_cashbook_offset'
        path = f"{OUT}/messy/{cfg['id']}_cashbook.xlsx"
        ex.build_cashbook(cfg, truth, rng, M, rowmap, path)
        fname = os.path.basename(path)
    else:
        recs = ex.make_recs(cfg, truth, L)
        # randomly drop a few rows from the export (lost in export) - never the opening entry
        kept = []
        for r in recs:
            if r['t']['src'] != 'OPEN' and rng.random() < M['drop']:
                r['t']['in_export'], r['t']['note'] = False, 'dropped_row'
            else:
                kept.append(r)
        moji = []
        if cfg.get('moji'):
            for _ in range(2):
                a = cfg['fy0'] + timedelta(days=int(rng.integers(20, 300)))
                moji.append((a, a + timedelta(days=45)))
        for r in kept:
            ex.corrupt(r, cfg, L, rng, M, fmt != 'qb', moji)
        rows = ex.build_qb(cfg, kept, rng, M) if fmt == 'qb' else ex.build_flat(cfg, kept, rng, M)
        fname = f"{cfg['id']}_gl_export.csv"
        ex.write_csv(f"{OUT}/messy/{fname}", rows, cfg, rowmap)

    # trial balance truth
    full, expd = defaultdict(lambda: [0, 0]), defaultdict(lambda: [0, 0])
    for t in truth:
        full[t['code']][0] += t['dr']; full[t['code']][1] += t['cr']
        if t['in_export']:
            expd[t['code']][0] += t['dr']; expd[t['code']][1] += t['cr']
    for code in sorted(full):
        tb_rows.append([cfg['id'], code, SYN[code][0], f"{full[code][0]/100:.2f}", f"{full[code][1]/100:.2f}",
                        f"{(full[code][0]-full[code][1])/100:.2f}", f"{expd[code][0]/100:.2f}", f"{expd[code][1]/100:.2f}",
                        f"{(expd[code][0]-expd[code][1])/100:.2f}"])
    truth_all += truth

    # stats
    rev = sum(t['cr'] - t['dr'] for t in truth if t['code'][0] == '4')
    exp_ = sum(t['dr'] - t['cr'] for t in truth if t['code'][0] in '567')
    n_rows = sum(1 for r in rowmap if r['client_id'] == cfg['id'])
    n_data = sum(1 for r in rowmap if r['client_id'] == cfg['id'] and r['row_kind'] == 'data')
    errs = Counter()
    for r in rowmap:
        if r['client_id'] == cfg['id'] and r['error_types']:
            for e in r['error_types'].split(';'):
                errs[e.split(':')[0]] += 1
    stats[cfg['id']] = dict(entries=len(ents), lines=len(truth), file_rows=n_rows, data_rows=n_data, revenue=rev / 100, net=(rev - exp_) / 100,
                            dropped=sum(1 for t in truth if t['note'] == 'dropped_row'), errs=dict(errs.most_common()))
    manifest.append([cfg['id'], cfg['name'], cfg['industry'], cfg['cur'], fmt, cfg['mess'], fname, len(ents), len(truth), n_rows, n_data,
                     cfg['fy0'].isoformat(), (cfg['fy0'].replace(year=cfg['fy0'].year + 1) - timedelta(days=1)).isoformat()])
    print(cfg['id'], stats[cfg['id']]['lines'], 'lines', n_rows, 'rows', 'rev', round(rev / 100), 'net', round((rev - exp_) / 100), flush=True)

# ---- write global files
def w(path, header, rows):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        cw = csv.writer(f); cw.writerow(header); cw.writerows(rows)

w(f'{OUT}/standard_chart_of_accounts.csv', ['std_account_code', 'std_account_name', 'account_class', 'normal_balance', 'risk_tier', 'error_cost_weight'], coa_rows())
names = {c: s[0] for c, s in SYN.items()}
w(f'{OUT}/truth/clean_ledger_all_clients.csv',
  ['client_id', 'txn_id', 'line_id', 'posting_date', 'period', 'source', 'doc_ref', 'std_account_code', 'std_account_name', 'description',
   'counterparty', 'debit', 'credit', 'inherently_ambiguous_label', 'in_export', 'export_note'],
  [[t['client_id'], t['txn_id'], t['line_id'], t['date'].isoformat(), t['date'].strftime('%Y-%m'), t['src'], t['ref'], t['code'], names[t['code']],
    t['desc'], t['cp'], f"{t['dr']/100:.2f}", f"{t['cr']/100:.2f}", t['ambig'], int(t['in_export']), t['note']] for t in truth_all])
w(f'{OUT}/truth/row_truth_map.csv', ['client_id', 'file', 'sheet', 'row_number', 'row_kind', 'line_id', 'is_duplicate', 'error_types'],
  [[r['client_id'], r['file'], r['sheet'], r['row_number'], r['row_kind'], r['line_id'], r['is_duplicate'], r['error_types']] for r in rowmap])
w(f'{OUT}/truth/trial_balance_truth.csv',
  ['client_id', 'std_account_code', 'std_account_name', 'debit_full', 'credit_full', 'net_full', 'debit_in_export', 'credit_in_export', 'net_in_export'], tb_rows)
w(f'{OUT}/manifest.csv', ['client_id', 'client_name', 'industry', 'currency', 'export_layout', 'messiness', 'messy_file', 'journal_entries', 'truth_lines',
                          'file_rows', 'data_rows', 'fiscal_year_start', 'fiscal_year_end'], manifest)
json.dump(stats, open(os.path.join(CACHE, 'stats.json'), 'w'), indent=1, default=str)
print('done')
