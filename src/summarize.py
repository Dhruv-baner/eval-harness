"""Flat comparison table (one row per cleaner and split) -> results/cleaner_comparison.csv"""
import json, os
import pandas as pd
from paths import RESULTS

R = json.load(open(os.path.join(RESULTS, 'results.json')))
X = json.load(open(os.path.join(RESULTS, 'extras.json')))
rows = []
for sp in ('test', 'dev', 'all'):
    for n, r in R['cleaners'].items():
        g = r[sp]; o = g['overall']; d = g['duplicates']; t = g['trial_balance_overall']
        rc = {c['labels_reviewed']: c['accuracy'] for c in g['review_curve']}
        ci = X['bootstrap'].get(sp, {}).get('acc', {}).get(n)
        rows.append(dict(split=sp, cleaner=n, rows=o['n'], account_accuracy=o['acc'], acc_ci_lo=ci['lo'] if ci else None, acc_ci_hi=ci['hi'] if ci else None,
                         cost_weighted_accuracy=o['acc_cost_weighted'], dollar_weighted_accuracy=o['acc_dollar_weighted_macro'], unmapped_rate=o['unmapped'],
                         date_accuracy=o['date_acc'], amount_accuracy=o['amount_acc'], fully_correct_rows=o['fully_correct'],
                         dup_precision=d['precision'], dup_recall=d['recall'], imbalance_recall=g['imbalance']['recall'],
                         calibration_ece=g['calibration']['ece'], tb_accounts_within_1pct=t['within_1pct_macro'], tb_misposted_share=t['misstatement_macro'],
                         accuracy_after_reviewing_10_labels=rc.get(10)))
pd.DataFrame(rows).to_csv(os.path.join(RESULTS, 'cleaner_comparison.csv'), index=False)
print('wrote results/cleaner_comparison.csv')
