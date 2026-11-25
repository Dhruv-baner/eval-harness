# -*- coding: utf-8 -*-
"""Stand-in cleaning agents. They only see messy files (+ labelled training rows from OTHER clients for the ML one)."""
import re, bisect, statistics
from collections import defaultdict, Counter
import numpy as np
from rapidfuzz import process, fuzz
from refdata import SYN, DE
from ledger_parser import parse_file, net_amount, parse_date, numeric_candidates, infer_dayfirst

ABBR = [('exp.', 'expenses'), ('maint.', 'maintenance'), ('prof.', 'professional'), ('equip.', 'equipment'), ('subs ', 'subscriptions '),
        ('tel.', 'telephone'), ('advert.', 'advertising'), ('ins.', 'insurance'), ('acc.', 'accounts'), ('rec.', 'receivable')]
UNCAT = {'uncategorized expense', 'ask my accountant', 'suspense', 'unallocated expense', 'uncategorised', 'unklare buchung', 'misc', '???', 'check', 'tbc', ''}
KW = [(r'rent|lease|miete', '6100'), (r'payroll|wages|gehalt|lohn', '6000'), (r'insurance|versicher', '6500'),
      (r'electric|utilit|water|energie|strom|stadtwerke', '6110'), (r'phone|telecom|broadband|telekom|vodafone|verizon|at&t|comcast|spectrum', '6120'),
      (r'processing fee|stripe fee|merchant', '6810'), (r'depreciation|abschreib', '6700'), (r'interest|zins', '7000'),
      (r'freight|shipping|fedex|ups\b|dhl|parcel|royal mail|dpd|toll', '5200'), (r'fuel|shell|aral|chevron|exxon|sunoco|wawa|pilot', '6610'),
      (r'software|subscription|zoom|slack|adobe|workspace|microsoft|github|notion|aws|cloud', '6210'),
      (r'advertis|google ads|meta ads|marketing|mailchimp|linkedin', '6400'), (r'accountan|cpa\b|bookkeep|steuerberat', '6310'),
      (r'legal|law\b|solicitor|kanzlei|llp', '6300'), (r'bank fee|bank charge', '6800'),
      (r'airline|hotel|uber|lyft|travel|delta|marriott|lufthansa|bahn|hilton|expedia', '6410'),
      (r'coffee|restaurant|meal|starbucks|chipotle|pret|panera|doordash|grubhub|deliveroo', '6420'),
      (r'staples|office depot|supplies|stationery', '6200'), (r'repair|maintenance|plumb|hvac|electric\b', '6600')]


def norm_label(x, fix=False):
    x = x or ''
    if fix and ('Ã' in x or 'Â' in x):
        try: x = x.encode('latin-1').decode('utf-8')
        except Exception: pass
    x = x.replace('\xa0', ' ').strip().lower()
    if ' : ' in x: x = x.split(' : ')[-1]
    x = re.sub(r'^acct\s*-\s*', '', x)
    x = re.sub(r'^\d+\s*(-\s*)?', '', x)
    x = re.sub(r'(\s*-\s*(general|misc)|\s*\(old\)|\*)$', '', x)
    for a, b in ABBR: x = x.replace(a, b)
    x = x.replace(' and ', ' & ')
    x = re.sub(r'[^\w&/ ]', ' ', x)
    return re.sub(r'\s+', ' ', x).strip()


def build_dict():
    d, coll = {}, []
    for code, syn in SYN.items():
        for lab in syn:
            k = norm_label(lab)
            if k in d and d[k] != code: coll.append((k, d[k], code))
            d.setdefault(k, code)
    for code, lab in DE.items():
        d.setdefault(norm_label(lab), code)
    return d, coll


LABEL_DICT, COLLISIONS = build_dict()
COA_CODES = set(SYN)


# ----------------------------------------------------------------------------- mappers
class RulesMapper:
    name = 'rules'
    def map(self, r):
        k = norm_label(r.get('label', ''))
        if k in LABEL_DICT: return LABEL_DICT[k], 1.0, 'dict'
        cc = (r.get('ccode') or '').strip()
        if cc in COA_CODES: return cc, 0.7, 'code'
        return None, 0.0, 'unmapped'


class FuzzyMapper:
    name = 'fuzzy'
    def __init__(self, cutoff=82):
        self.keys = list(LABEL_DICT)
        self.cache = {}
        self.cutoff = cutoff
    def match(self, k, cutoff=90):
        key = ('m', k, cutoff)
        if key not in self.cache:
            m = process.extractOne(k, self.keys, scorer=fuzz.WRatio, score_cutoff=cutoff)
            self.cache[key] = (LABEL_DICT[m[0]], min(.95, m[1] / 100)) if m else None
        return self.cache[key]
    def kw(self, r):
        text = f"{r.get('desc','')} {r.get('name','')}".lower()
        for rx, code in KW:
            if re.search(rx, text): return code, 0.5, 'keyword'
        return None, 0.0, 'unmapped'
    def map(self, r):
        k = norm_label(r.get('label', ''), fix=True)
        if k in UNCAT: return self.kw(r)
        if k in LABEL_DICT: return LABEL_DICT[k], 1.0, 'dict'
        if k not in self.cache:
            m = process.extractOne(k, self.keys, scorer=fuzz.WRatio, score_cutoff=self.cutoff)
            self.cache[k] = (LABEL_DICT[m[0]], min(.95, m[1] / 100), 'fuzzy') if m else None
        if self.cache[k]: return self.cache[k]
        return self.kw(r)


def row_text(r, sib):
    lab = norm_label(r.get('label', ''), fix=True) or 'blank_label'
    desc = re.sub(r'\d+', '#', f"{r.get('desc','')} {r.get('name','')} {r.get('type','')}".lower())
    side = 'side_d' if (r.get('net') or 0) >= 0 else 'side_c'
    return lab, f"{desc} {side}", sib


class MLMapper:
    name = 'ml'
    def __init__(self, n_train=45000, seed=0):
        self.n_train, self.seed = n_train, seed
    def feats(self, rows, fit=False):
        from sklearn.feature_extraction.text import TfidfVectorizer
        from scipy.sparse import hstack
        labs, descs, sibs = zip(*[row_text(r, r['_sib']) for r in rows])
        if fit:
            self.v1 = TfidfVectorizer(analyzer='char_wb', ngram_range=(2, 4), min_df=3, sublinear_tf=True, max_features=50000)
            self.v2 = TfidfVectorizer(ngram_range=(1, 2), min_df=3, sublinear_tf=True, max_features=50000)
            self.v3 = TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 4), min_df=5, sublinear_tf=True, max_features=20000)
            return hstack([self.v1.fit_transform(labs), self.v2.fit_transform(descs), self.v3.fit_transform(sibs)]).tocsr()
        return hstack([self.v1.transform(labs), self.v2.transform(descs), self.v3.transform(sibs)]).tocsr()
    def fit(self, rows, y):
        from sklearn.linear_model import SGDClassifier
        rng = np.random.default_rng(self.seed)
        idx = rng.permutation(len(rows))[:self.n_train]
        rows = [rows[i] for i in idx]; y = [y[i] for i in idx]
        X = self.feats(rows, fit=True)
        self.clf = SGDClassifier(loss='log_loss', alpha=2e-6, max_iter=10, tol=None, random_state=self.seed)
        self.clf.fit(X, y)
    def predict(self, rows):
        P = self.clf.predict_proba(self.feats(rows))
        j = P.argmax(1)
        return [(self.clf.classes_[a], float(P[i, a]), 'ml') for i, a in enumerate(j)]


# ----------------------------------------------------------------------------- repairs
def norm_key(x):
    return (x or '').strip().upper()


def resolve_dates(rows):
    """default parse + neighbour-median disambiguation of ambiguous numeric dates (file order)."""
    base = []
    for r in rows:
        d = parse_date(r['date_raw'], r['dayfirst'], r['year_hint'])
        base.append(d)
    # year hint for rows lacking a year: file's modal year
    unamb = []
    for i, r in enumerate(rows):
        raw = r['date_raw']
        c = numeric_candidates(str(raw)) if raw is not None and not hasattr(raw, 'year') else None
        if base[i] and not (c and c[0] and c[1] and c[0] != c[1]): unamb.append((i, base[i].toordinal()))
    idxs = [i for i, _ in unamb]
    out = list(base)
    for i, r in enumerate(rows):
        raw = r['date_raw']
        c = numeric_candidates(str(raw)) if raw is not None and not hasattr(raw, 'year') else None
        if not (c and c[0] and c[1] and c[0] != c[1]): continue
        p = bisect.bisect_left(idxs, i)
        nb = [unamb[k][1] for k in range(max(0, p - 3), min(len(unamb), p + 3))]
        if not nb: continue
        med = statistics.median(nb)
        d_def = abs(base[i].toordinal() - med)
        alt = c[1] if r['dayfirst'] else c[0]
        if abs(alt.toordinal() - med) + 20 < d_def: out[i] = alt
    return out


def repair_file(rows, is_cashbook, near_dup=True):
    """rows: data rows of one file (file order). sets r['date'], r['net'], dup flags, balance flags."""
    dates = resolve_dates(rows)
    for r, d in zip(rows, dates): r['date'] = d
    # dedupe (normalised)
    seen = {}
    for r in rows:
        k = (norm_key(r.get('ref')), r['date'], r['net'], norm_label(r.get('label', ''), fix=True), (r.get('desc') or '').strip().lower())
        if k in seen: r['dup'] = True
        else: seen[k] = r
    live = [r for r in rows if not r.get('dup')]
    # fill missing dates from same-document siblings
    by_ref = defaultdict(list)
    for r in live: by_ref[norm_key(r.get('ref'))].append(r)
    for g in by_ref.values():
        ds = [r['date'] for r in g if r['date']]
        if ds:
            m = Counter(ds).most_common(1)[0][0]
            for r in g:
                if not r['date']: r['date'] = m; r['date_filled'] = True
    if is_cashbook: return
    # balance check per document
    for ref, g in by_ref.items():
        if not ref: continue
        net = sum(r['net'] for r in g if r['net'] is not None)
        if net == 0: continue
        cands = [r for r in g if r['net'] is not None and abs(r['net']) * 2 == abs(net) and (r['net'] > 0) == (net > 0)]
        if len(cands) == 1:
            cands[0]['net'] = -cands[0]['net']; cands[0]['flip_repaired'] = True
        else:
            for r in g: r['flag_unbalanced'] = True


# ----------------------------------------------------------------------------- orchestration
def run_rules(path_by_file):
    out = []
    for fname, path in path_by_file.items():
        rows = parse_file(path, fname, smart=False)
        m = RulesMapper(); seen = set()
        eu_cash = fname.endswith('.xlsx')
        for r in rows:
            o = dict(file=r['file'], sheet=r['sheet'], row_number=r['row_number'], kind_pred='junk', pred_code=None, conf=0.0, src='', date=None, net=None)
            if r['kind'] == 'data':
                o['net'] = net_amount(r)
                o['date'] = parse_date(r['date_raw'], r['dayfirst'], None, strict=True)
                key = tuple(r['cells'])
                o['kind_pred'] = 'dup' if key in seen else 'data'
                seen.add(key)
                o['pred_code'], o['conf'], o['src'] = m.map(r)
                o['_raw'] = r
            else:
                o['_raw'] = r
            out.append(o)
    return out


def prepare(path_by_file):
    allrows = {}
    for fname, path in path_by_file.items():
        rows = parse_file(path, fname, smart=True)
        data = [r for r in rows if r['kind'] == 'data']
        for r in data: r['net'] = net_amount(r)
        by_ref = defaultdict(list)
        for r in data: by_ref[(norm_key(r.get('ref')))].append(r)
        for r in data:
            labs = ' | '.join(norm_label(x.get('label', ''), fix=True) for x in by_ref[norm_key(r.get('ref'))] if x is not r)[:300]
            r['_sib'] = labs
        repair_file(data, fname.endswith('.xlsx'))
        allrows[fname] = rows
    return allrows


def finish(allrows, mapper_fn):
    out = []
    for fname, rows in allrows.items():
        data = [r for r in rows if r['kind'] == 'data']
        preds = mapper_fn(fname, data)
        pi = {id(r): p for r, p in zip(data, preds)}
        for r in rows:
            o = dict(file=r['file'], sheet=r['sheet'], row_number=r['row_number'], kind_pred='junk', pred_code=None, conf=0.0, src='', date=None, net=None, _raw=r)
            if r['kind'] == 'data':
                o['kind_pred'] = 'dup' if r.get('dup') else 'data'
                o['date'], o['net'] = r.get('date'), r['net']
                o['pred_code'], o['conf'], o['src'] = pi[id(r)]
                o['flag_unbalanced'] = r.get('flag_unbalanced', False); o['flip_repaired'] = r.get('flip_repaired', False)
                o['date_filled'] = r.get('date_filled', False)
            out.append(o)
    return out


def hybrid_map(fz, r, ml_pred, cutoff=90):
    """dictionary -> high-confidence fuzzy -> ML fallback (ML also handles uncategorised / blank labels)."""
    k = norm_label(r.get('label', ''), fix=True)
    if k in UNCAT: return ml_pred[0], ml_pred[1], 'ml'
    if k in LABEL_DICT: return LABEL_DICT[k], 1.0, 'dict'
    m = fz.match(k, cutoff)
    if m: return m[0], m[1], 'fuzzy'
    return ml_pred[0], ml_pred[1], 'ml'
