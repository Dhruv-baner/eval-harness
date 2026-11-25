# -*- coding: utf-8 -*-
"""Layout-agnostic parser for messy GL exports. Uses only the file contents (never the answer key)."""
import csv, re
from collections import Counter
from datetime import date, datetime, timedelta

RULES = [
    ('code', r'^account code$|nominal|^konto$|^code$'),
    ('label', r'^account$|account name|kontobezeichnung|^category$'),
    ('debit', r'^debit$|^soll$|^out$|^money out$'),
    ('credit', r'^credit$|^haben$|^in$|^money in$'),
    ('amount', r'^amount$'),
    ('date', r'date|datum'),
    ('ref', r'^num$|^reference$|^beleg$|document number'),
    ('txn', r'^tran no$|^internal id$'),
    ('name', r'^name$|^payee$|paid to'),
    ('desc', r'description|memo|details|buchungstext|^notes$'),
    ('type', r'^type$|^source$'),
]
TOT = re.compile(r'^\s*((grand\s+)?total\b|summe\b|subtotal|report generated)', re.I)
NUMDATE = re.compile(r'^(\d{1,2})[/.](\d{1,2})[/.](\d{2,4})$')
TEXT_FMTS = ['%d-%b-%y', '%d-%b-%Y', '%d %b %Y', '%b %d, %Y', '%B %d, %Y', '%d %B %Y']


def header_roles(cells):
    roles = {}
    for j, h in enumerate(cells):
        hl = str(h or '').strip().lower()
        if hl == '' and j == 0:
            roles.setdefault('section', 0); continue
        for role, rx in RULES:
            if role not in roles and re.search(rx, hl):
                roles[role] = j; break
    return roles


def find_header(rows):
    for i, (_, cells) in enumerate(rows[:15]):
        r = header_roles(cells)
        if len(set(r) - {'section'}) >= 4:
            return i, r
    return None, None


def read_rows(path):
    """yield (sheet, [(row_number, cells)])"""
    if path.endswith('.xlsx'):
        from openpyxl import load_workbook
        wb = load_workbook(path, data_only=True)
        for ws in wb.worksheets:
            yield ws.title, [(i, list(r)) for i, r in enumerate(ws.iter_rows(values_only=True), 1)]
    else:
        with open(path, encoding='utf-8-sig', newline='') as f:
            yield '', [(i, r) for i, r in enumerate(csv.reader(f), 1)]


def s(v):
    if v is None: return ''
    if isinstance(v, datetime): return v.strftime('%Y-%m-%d')
    return str(v)


# ------------------------------------------------------------------ amounts
def parse_amount(v, eu):
    """returns (cents, negative_flag, suffix) or None"""
    if v is None: return None
    st = str(v).strip()
    if st == '': return None
    m = re.search(r'\b(cr|dr)\b\s*$', st, re.I)
    suffix = m.group(1).upper() if m else None
    neg = st.startswith('-') or st.startswith('(')
    digits = re.sub(r'[^\d,.]', '', st)
    if not re.search(r'\d', digits): return None
    digits = digits.replace('.', '').replace(',', '.') if eu else digits.replace(',', '')
    try:
        return int(round(float(digits) * 100)), neg, suffix
    except ValueError:
        return None


def detect_eu(samples):
    eu = sum(1 for x in samples if re.search(r',\d{1,2}\s*(cr|dr)?$', str(x).strip(), re.I) and not re.search(r'\.\d{2}\s*(cr|dr)?$', str(x).strip(), re.I))
    us = sum(1 for x in samples if re.search(r'\.\d{2}\s*(cr|dr)?$', str(x).strip(), re.I))
    return eu > us


# ------------------------------------------------------------------ dates
def infer_dayfirst(strs):
    a_big = b_big = dots = 0
    for x in strs:
        m = NUMDATE.match(x.strip())
        if not m: continue
        a, b = int(m.group(1)), int(m.group(2))
        if '.' in x: dots += 1
        if a > 12: a_big += 1
        if b > 12: b_big += 1
    if a_big or b_big: return a_big >= b_big
    return dots > 0


def numeric_candidates(x):
    m = NUMDATE.match(x.strip())
    if not m: return None
    a, b, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    y = y + 2000 if y < 100 else y
    out = []
    for dd, mm in ((a, b), (b, a)):
        try: out.append(date(y, mm, dd))
        except ValueError: out.append(None)
    return out  # [dayfirst, monthfirst]


def parse_date(v, dayfirst, year_hint=None, strict=False):
    if v is None: return None
    if isinstance(v, datetime): return v.date()
    if isinstance(v, date): return v
    st = str(v).strip()
    if st == '': return None
    if not strict and re.fullmatch(r'\d{5}(\.0)?', st):
        n = int(float(st))
        if 30000 < n < 60000: return date(1899, 12, 30) + timedelta(days=n)
    m = re.match(r'^(\d{4})-(\d{2})-(\d{2})', st)
    if m:
        try: return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError: return None
    c = numeric_candidates(st)
    if c: return c[0] if dayfirst else c[1]
    for f in TEXT_FMTS:
        try: return datetime.strptime(st, f).date()
        except ValueError: pass
    if strict or not year_hint: return None
    st2 = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', st)
    for f in ('%d %B %Y', '%b %d %Y', '%d %b %Y'):
        for cand in (f"{st2} {year_hint}",):
            try: return datetime.strptime(cand, f).date()
            except ValueError: pass
    return None


# ------------------------------------------------------------------ file parser
def parse_file(path, fname, smart=False):
    out = []
    for sheet, rows in read_rows(path):
        hi, roles = find_header(rows)
        if hi is None:
            for rn, cells in rows:
                out.append(dict(file=fname, sheet=sheet, row_number=rn, kind='junk', cells=[s(c) for c in cells]))
            continue
        header = [s(c).strip().lower() for c in rows[hi][1]]
        grouped = 'section' in roles
        # file-level conventions from this sheet
        amt_cols = [roles[k] for k in ('debit', 'credit', 'amount') if k in roles]
        samples = [s(c[j]) for _, c in rows[hi + 1:] for j in amt_cols if j < len(c) and s(c[j]).strip()]
        eu = detect_eu(samples[:4000])
        dsamples = [s(c[roles['date']]) for _, c in rows[hi + 1:] if 'date' in roles and roles['date'] < len(c)][:6000]
        dayfirst = infer_dayfirst(dsamples)
        ym = re.search(r'(20\d\d)', sheet)
        section = ''
        for rn, cells in rows:
            cs = [s(c) for c in cells]
            base = dict(file=fname, sheet=sheet, row_number=rn, cells=cs, kind='junk', eu=eu, dayfirst=dayfirst,
                        year_hint=int(ym.group(1)) if ym else None)
            if rn <= rows[hi][0] or not any(x.strip() for x in cs):
                out.append(base); continue
            if [x.strip().lower() for x in cs] == header:
                out.append(base); continue
            nonblank = [x for x in cs if x.strip()]
            if grouped and cs[0].strip():
                if len(nonblank) == 1 and not TOT.match(cs[0]):
                    section = cs[0].strip(); out.append(base); continue
                out.append(base); continue
            tot_hit = any(TOT.match(x) for x in cs)
            if tot_hit and smart:
                has_id = any(role in roles and roles[role] < len(cs) and cs[roles[role]].strip() for role in ('ref', 'date'))
                tot_hit = not has_id
            if tot_hit or len(nonblank) <= 1:
                out.append(base); continue
            g = lambda role: cs[roles[role]] if role in roles and roles[role] < len(cs) else ''
            amts = {k: (cells[roles[k]] if k in roles and roles[k] < len(cells) else None) for k in ('debit', 'credit', 'amount')}
            if not any(a is not None and str(a).strip() != '' for a in amts.values()):
                out.append(base); continue
            base.update(kind='data', section=section, label=g('label') or (section if grouped else ''), ccode=g('code'),
                        desc=g('desc'), name=g('name'), ref=g('ref') or g('txn'), type=g('type'),
                        date_raw=cells[roles['date']] if 'date' in roles else None, amts=amts)
            out.append(base)
    return out


def net_amount(r):
    """signed cents, positive = debit; None if unparseable"""
    a = r['amts']; eu = r['eu']; net = 0; seen = False
    if a.get('amount') is not None and str(a['amount']).strip():
        p = parse_amount(a['amount'], eu)
        if p:
            v, neg, suf = p
            sign = -1 if (neg or suf == 'CR') else 1
            if suf == 'DR': sign = 1
            return sign * v
        return None
    for k, side in (('debit', 1), ('credit', -1)):
        if a.get(k) is not None and str(a[k]).strip():
            p = parse_amount(a[k], eu)
            if p:
                v, neg, suf = p
                net += side * (-v if neg else v); seen = True
    return net if seen else None
