# -*- coding: utf-8 -*-
import pickle, json, math, os, gzip
import numpy as np, pandas as pd

from paths import DATA as D, RESULTS as OUT, CACHE
CLEANERS = ['rules', 'fuzzy', 'ml', 'hybrid']
DEV = ['harborview_dental', 'brightleaf_organics', 'lumen_software', 'sunrise_property']
TEST = ['northgate_construction', 'alder_finch_llp', 'rivera_restaurants', 'kestrel_logistics']

rm = pd.read_csv(f'{D}/truth/row_truth_map.csv', keep_default_na=False, dtype={'row_number': int, 'sheet': str})
tr = pd.read_csv(f'{D}/truth/clean_ledger_all_clients.csv', dtype={'std_account_code': str}, keep_default_na=False)
tr['net_cents'] = ((tr.debit - tr.credit) * 100).round().astype(int)
tb = pd.read_csv(f'{D}/truth/trial_balance_truth.csv', dtype={'std_account_code': str})
coa = pd.read_csv(f'{D}/standard_chart_of_accounts.csv', dtype={'std_account_code': str})
man = pd.read_csv(f'{D}/manifest.csv', keep_default_na=False)
NAME = dict(zip(coa.std_account_code, coa.std_account_name))
W = dict(zip(coa.std_account_code, coa.error_cost_weight))
TIER = dict(zip(coa.std_account_code, coa.risk_tier))
CLS = dict(zip(coa.std_account_code, coa.account_class))

LABEL_TAGS = {'label_variant', 'missing_account', 'uncategorized_label', 'legacy_label', 'mojibake'}
DATE_TAGS = {'date_alt_format', 'date_alt_format:ambiguous', 'missing_date', 'date_excel_serial', 'date_no_year', 'date_text_ordinal', 'date_text_string'}
AMT_TAGS = {'sign_flip', 'amount_digit_error', 'credit_as_negative_debit', 'drcr_suffix', 'amount_format', 'swapped_direction'}
tr_idx = tr.set_index('line_id')
norm = lambda x: (x or '').strip().upper()


def tags_of(s):
    return [t for t in s.split(';') if t] if isinstance(s, str) else []


def r4(x): return None if x is None or (isinstance(x, float) and math.isnan(x)) else round(float(x), 4)


def load(name):
    df = pd.DataFrame(pickle.load(open(f'{CACHE}/{name}.pkl', 'rb')))
    df['sheet'] = df.sheet.fillna('').astype(str)
    df = df.merge(rm, on=['file', 'sheet', 'row_number'], how='left')
    t = tr[['line_id', 'posting_date', 'std_account_code', 'net_cents', 'doc_ref', 'inherently_ambiguous_label']].rename(columns={'std_account_code': 'true_code'})
    df = df.merge(t, on='line_id', how='left')
    df['tags'] = df.error_types.map(tags_of)
    df['is_data_true'] = df.row_kind == 'data'
    df['pred_code'] = df.pred_code.where(df.pred_code.notna(), None)
    return df


def grp_acc(sub, col='correct'):
    return dict(n=int(len(sub)), acc=r4(sub[col].mean()) if len(sub) else None)


def tag_table(M, col, tagsets, clean_name, clean_pred):
    rows = []
    for tag in tagsets:
        sub = M[M.tags.map(lambda t: tag in t)]
        if len(sub): rows.append(dict(tag=tag, **grp_acc(sub, col)))
    sub = M[M.tags.map(clean_pred)]
    rows.append(dict(tag=clean_name, **grp_acc(sub, col)))
    return rows


def score(name, clients=None, outputs=False):
    df = load(name)
    if clients is not None: df = df[df.client_id.isin(clients)].copy()
    R = dict(name=name)
    pd_ = df.kind_pred.isin(['data', 'dup']); td = df.is_data_true
    tp, fp, fn = int((pd_ & td).sum()), int((pd_ & ~td).sum()), int((~pd_ & td).sum())
    R['row_classification'] = dict(precision=r4(tp / max(tp + fp, 1)), recall=r4(tp / max(tp + fn, 1)), missed_data_rows=fn, junk_kept=fp)
    # duplicates
    tdup = td & (df.is_duplicate == 1); pdup = df.kind_pred == 'dup'
    dtp = int((tdup & pdup).sum())
    exact = tdup & df.tags.map(lambda t: 'duplicate_exact' in t); near = tdup & df.tags.map(lambda t: 'duplicate_near' in t)
    R['duplicates'] = dict(precision=r4(dtp / max(int(pdup.sum()), 1)), recall=r4(dtp / max(int(tdup.sum()), 1)),
                           recall_exact=r4((exact & pdup).sum() / max(int(exact.sum()), 1)), recall_near=r4((near & pdup).sum() / max(int(near.sum()), 1)),
                           false_dups=int((pdup & ~tdup).sum()), true_dups=int(tdup.sum()))
    # evaluation set = original (non-duplicate) data rows
    M = df[td & (df.is_duplicate == 0)].copy()
    M['correct'] = (M.pred_code == M.true_code)
    M['w'] = M.true_code.map(W)
    M['abs_net'] = M.net_cents.abs()
    M['date_ok'] = M.date.map(lambda d: str(d) if d is not None and not pd.isna(d) else None) == M.posting_date
    M['amt_ok'] = M.net.notna() & ((M.net.fillna(0) - M.net_cents).abs() <= 1)
    M['all_ok'] = M.correct & M.date_ok & M.amt_ok
    M['in_dict'] = M.in_dict.fillna(False).astype(bool)
    M['label_clean'] = M.tags.map(lambda t: not any(x.split(':')[0] in LABEL_TAGS for x in t))
    M['unmapped'] = M.pred_code.isna()
    # per client
    cl = []
    for cid, g in M.groupby('client_id'):
        cl.append(dict(client_id=cid, n=int(len(g)), acc=r4(g.correct.mean()), acc_cost_weighted=r4((g.w * g.correct).sum() / g.w.sum()),
                       acc_dollar_weighted=r4((g.abs_net * g.correct).sum() / max(g.abs_net.sum(), 1)), unmapped=r4(g.unmapped.mean()),
                       date_acc=r4(g.date_ok.mean()), amount_acc=r4(g.amt_ok.mean()), fully_correct=r4(g.all_ok.mean())))
    R['by_client'] = cl
    macro = lambda k: r4(np.mean([c[k] for c in cl]))
    R['overall'] = dict(n=int(len(M)), acc=r4(M.correct.mean()), acc_cost_weighted=r4((M.w * M.correct).sum() / M.w.sum()),
                        acc_dollar_weighted_macro=macro('acc_dollar_weighted'), unmapped=r4(M.unmapped.mean()),
                        date_acc=r4(M.date_ok.mean()), amount_acc=r4(M.amt_ok.mean()), fully_correct=r4(M.all_ok.mean()),
                        acc_macro_client=macro('acc'))
    # by error tag
    sub_tags = sorted({t for ts in M.tags for t in ts if t.startswith('label_variant:')})
    R['by_label_tag'] = tag_table(M, 'correct', ['label_variant', 'missing_account', 'uncategorized_label', 'legacy_label', 'mojibake'] + sub_tags,
                                  'clean_label', lambda t: not any(x.split(':')[0] in LABEL_TAGS for x in t))
    cv = M[M.label_clean & ~M.in_dict.astype(bool)]
    sv = M[M.label_clean & M.in_dict.astype(bool)]
    R['by_label_tag'].append(dict(tag='client_specific_vocabulary', **grp_acc(cv)))
    R['by_label_tag'].append(dict(tag='standard_vocabulary', **grp_acc(sv)))
    ul = cv.groupby(['client_id', 'label_norm', 'true_code']).agg(n=('correct', 'size'), acc=('correct', 'mean')).reset_index().sort_values('n', ascending=False).head(14)
    R['top_client_labels'] = [dict(client_id=r.client_id, label=r.label_norm, true=r.true_code, true_name=NAME[r.true_code], n=int(r.n), acc=r4(r.acc)) for r in ul.itertuples()]
    amb = M[M.inherently_ambiguous_label == 1]
    R['by_label_tag'].append(dict(tag='inherently_ambiguous_label', **grp_acc(amb)))
    R['by_date_tag'] = tag_table(M, 'date_ok', sorted(DATE_TAGS), 'clean_date', lambda t: not any(x in DATE_TAGS for x in t))
    R['by_amount_tag'] = tag_table(M, 'amt_ok', sorted(AMT_TAGS), 'clean_amount', lambda t: not any(x in AMT_TAGS for x in t))
    R['by_tier'] = [dict(tier=k, **grp_acc(g)) for k, g in M.groupby(M.true_code.map(TIER))]
    R['by_class'] = [dict(cls=k, **grp_acc(g)) for k, g in M.groupby(M.true_code.map(CLS))]
    R['by_source'] = [dict(src=k, **grp_acc(g)) for k, g in M.groupby('src')]
    # imbalance / repair
    bad_amt = M.tags.map(lambda t: 'sign_flip' in t or 'amount_digit_error' in t)
    flip = M.tags.map(lambda t: 'sign_flip' in t)
    flagged_rows = df[(df.flag_unbalanced == True) | (df.flip_repaired == True)] if 'flag_unbalanced' in df else df.iloc[0:0]
    Q = {(c, k) for c, k in zip(flagged_rows.client_id, flagged_rows.ref_key)}
    P = {(c, norm(r)) for c, r in zip(M[bad_amt].client_id, M[bad_amt].line_id.map(lambda l: tr_idx.at[l, 'doc_ref']))}
    drop = tr[(tr.export_note == 'dropped_row') & tr.client_id.isin(df.client_id.unique())]
    P |= {(c, norm(r)) for c, r in zip(drop.client_id, drop.doc_ref)}
    inter = len(P & Q)
    R['imbalance'] = dict(groups_positive=len(P), groups_flagged=len(Q), precision=r4(inter / max(len(Q), 1)), recall=r4(inter / max(len(P), 1)),
                          sign_flip_rows=int(flip.sum()), sign_flip_repaired=int((flip & M.amt_ok).sum()),
                          digit_rows=int(M.tags.map(lambda t: 'amount_digit_error' in t).sum()),
                          flips_wrongly_repaired=int(((df.flip_repaired == True) & ~df.tags.map(lambda t: 'sign_flip' in t) & df.is_data_true).sum()) if 'flip_repaired' in df else 0)
    # calibration + triage
    Mm = M[~M.unmapped]
    conf = Mm.conf.values; ok = Mm.correct.values.astype(float)
    edges = np.linspace(0, 1, 11); bins = []
    ece = 0.0
    for a, b in zip(edges[:-1], edges[1:]):
        mask = (conf >= a) & ((conf < b) if b < 1 else (conf <= b))
        if mask.sum():
            bins.append(dict(lo=r4(a), hi=r4(b), n=int(mask.sum()), mean_conf=r4(conf[mask].mean()), acc=r4(ok[mask].mean())))
            ece += mask.sum() / len(conf) * abs(ok[mask].mean() - conf[mask].mean())
    thr = []
    for t in [0, .5, .6, .7, .8, .85, .9, .95, .99]:
        acc_mask = (M.conf >= t) & ~M.unmapped
        sub = M[acc_mask]
        thr.append(dict(threshold=t, coverage=r4(len(sub) / len(M)), accuracy=r4(sub.correct.mean()) if len(sub) else None,
                        wrong_auto_accepted=int((~sub.correct).sum()), review_queue=int(len(M) - len(sub))))
    R['calibration'] = dict(ece=r4(ece), bins=bins, mean_conf=r4(conf.mean()) if len(conf) else None)
    R['threshold_curve'] = thr
    # confusions
    wrong = M[(~M.correct) & ~M.unmapped]
    cf = wrong.groupby(['true_code', 'pred_code']).agg(n=('correct', 'size'), amount=('abs_net', 'sum')).reset_index().sort_values('n', ascending=False).head(15)
    R['confusions'] = [dict(true=r.true_code, true_name=NAME[r.true_code], pred=r.pred_code, pred_name=NAME[r.pred_code], n=int(r.n), amount=float(r.amount) / 100) for r in cf.itertuples()]
    # trial balance tie-out (gross-activity denominator; tolerance = max($1, 1% of account gross activity))
    tbrows = []
    for cid, g in df[(df.kind_pred == 'data') & df.net.notna()].groupby('client_id'):
        c = g.assign(code=g.pred_code.fillna('UNMAPPED')).groupby('code').net.sum() / 100
        tt = tb[tb.client_id == cid].set_index('std_account_code')
        t = tt.net_in_export; gross_a = (tt.debit_in_export + tt.credit_in_export)
        codes = set(c.index) | set(t.index)
        diff = pd.Series({k: c.get(k, 0.0) - t.get(k, 0.0) for k in codes})
        tol = pd.Series({k: max(1.0, 0.01 * gross_a.get(k, 0.0)) for k in codes})
        tbrows.append(dict(client_id=cid, accounts=len(codes), exact_share=r4((diff.abs() <= 1).mean()), within_1pct_share=r4((diff.abs() <= tol).mean()),
                           abs_error=float(diff.abs().sum()), misstatement_ratio=r4(0.5 * diff.abs().sum() / max(gross_a.sum(), 1)),
                           cleaned_tb_imbalance=float(c.sum()), truth_tb_imbalance=float(t.sum()),
                           unmapped_amount=float(g[g.pred_code.isna()].net.abs().sum() / 100)))
    R['trial_balance'] = tbrows
    R['trial_balance_overall'] = dict(exact_share_macro=r4(np.mean([x['exact_share'] for x in tbrows])), within_1pct_macro=r4(np.mean([x['within_1pct_share'] for x in tbrows])), misstatement_macro=r4(np.mean([x['misstatement_ratio'] for x in tbrows])))
    # human-in-the-loop value: review the top-K most damaging labels once (a label maps to its majority true account)
    gl = M[M.label_norm != ''].copy()
    gl['wrong'] = ~gl.correct
    rows_ = []
    for (cid, lab), g in gl.groupby(['client_id', 'label_norm']):
        if g.wrong.sum() == 0: continue
        maj = g.true_code.mode().iloc[0]
        fixed = int(((g.true_code == maj) & g.wrong).sum())
        rows_.append((int(g.wrong.sum()), fixed))
    rows_.sort(reverse=True)
    N, base = len(M), int(M.correct.sum()); curve = [dict(labels_reviewed=0, accuracy=r4(base / N))]
    cum = 0
    for K in [5, 10, 20, 40, 80, 160, 320]:
        cum = sum(f for _, f in rows_[:K]); curve.append(dict(labels_reviewed=min(K, len(rows_)), accuracy=r4((base + cum) / N)))
    cum_all = sum(f for _, f in rows_); curve.append(dict(labels_reviewed=len(rows_), accuracy=r4((base + cum_all) / N)))
    R['review_curve'] = curve
    # examples
    ex = []
    for cid, g in wrong.groupby('client_id'):
        for r in g.sample(min(4, len(g)), random_state=1).itertuples():
            ex.append(dict(client_id=cid, file=r.file, row_number=int(r.row_number), cells=list(r.cells), true=r.true_code, true_name=NAME[r.true_code],
                           pred=r.pred_code, pred_name=NAME[r.pred_code], conf=r4(r.conf), tags=list(r.tags), src=r.src))
    for r in M[M.unmapped].sample(min(12, int(M.unmapped.sum())), random_state=1).itertuples() if M.unmapped.any() else []:
        ex.append(dict(client_id=r.client_id, file=r.file, row_number=int(r.row_number), cells=list(r.cells), true=r.true_code, true_name=NAME[r.true_code],
                       pred=None, pred_name=None, conf=0, tags=list(r.tags), src='unmapped'))
    R['examples'] = ex
    # cleaned output file
    if not outputs:
        R.pop('examples', None); return R
    outdf = df[['client_id', 'file', 'sheet', 'row_number', 'kind_pred', 'pred_code', 'conf', 'src', 'date', 'net']].copy()
    outdf.to_csv(f'{OUT}/cleaned_output_{name}.csv.gz', index=False, compression='gzip')
    return R


results = dict(generated='2026-11-25', split=dict(dev=DEV, test=TEST),
               cleaners={n: dict(all=score(n, None, True), dev=score(n, DEV), test=score(n, TEST)) for n in CLEANERS},
               dataset=dict(clients=man[['client_id', 'client_name', 'industry', 'currency', 'export_layout', 'messiness']].to_dict('records'),
                            rows=int(man.data_rows.sum()), ledger_lines=int(man.truth_lines.sum())))
results['tuning'] = json.load(open(f'{CACHE}/tuning.json'))
json.dump(results, open(f'{OUT}/results.json', 'w'), default=lambda o: o.item() if hasattr(o, 'item') else str(o))
print('written', os.path.getsize(f'{OUT}/results.json') // 1024, 'KB')
for sp in ('dev', 'test', 'all'):
    print('---', sp)
    for n in CLEANERS:
        R = results['cleaners'][n][sp]; o = R['overall']
        print(f"{n:6s} n={o['n']} acc={o['acc']} $w={o['acc_dollar_weighted_macro']} unmapped={o['unmapped']} date={o['date_acc']} amt={o['amount_acc']} fully={o['fully_correct']} | dupR={R['duplicates']['recall']} | ECE={R['calibration']['ece']} | TBmisp={R['trial_balance_overall']['misstatement_macro']}")
