# -*- coding: utf-8 -*-
"""Turns clean ledger lines into realistic messy exports and logs every injected error."""
import csv, re
from datetime import date, datetime, timedelta
import numpy as np
from refdata import *

LEVELS = {
 'low':  dict(label=.03, uncat=.004, date=.002, serial=.0003, amt=.01, dup=.0008, ndup=.0004, flip=.0006, digit=.0004, miss_acct=.002, miss_date=.001, negdeb=.002, desc_blank=.005, ws=.02, drop=.0),
 'med':  dict(label=.10, uncat=.015, date=.010, serial=.001, amt=.04, dup=.004, ndup=.002, flip=.002, digit=.0015, miss_acct=.008, miss_date=.004, negdeb=.006, desc_blank=.02, ws=.06, drop=.001),
 'high': dict(label=.20, uncat=.03, date=.030, serial=.003, amt=.08, dup=.008, ndup=.004, flip=.004, digit=.003, miss_acct=.015, miss_date=.008, negdeb=.010, desc_blank=.04, ws=.10, drop=.003),
}
DSTYLE = {'mdY': '%m/%d/%Y', 'dmY': '%d/%m/%Y', 'iso': '%Y-%m-%d', 'dmy_mon': '%d-%b-%y', 'dotted': '%d.%m.%Y'}
ALT_FMT = ['%Y-%m-%d', '%d %b %Y', '%b %d, %Y', '%m/%d/%y', '%d/%m/%y', '%d-%b-%Y', '%d/%m/%Y', '%m/%d/%Y', '%d.%m.%Y']
AMBIG_FMT = {'%m/%d/%y', '%d/%m/%y', '%d/%m/%Y', '%m/%d/%Y'}
SYM = {'USD': '$', 'GBP': '£', 'EUR': '€'}

HDR = {
 'qb': ['', 'Type', 'Date', 'Num', 'Name', 'Memo/Description', 'Debit', 'Credit'],
 'xero': ['Date', 'Account Code', 'Account', 'Source', 'Description', 'Reference', 'Debit', 'Credit'],
 'sage': ['Tran No', 'Date', 'Type', 'Nominal A/C', 'Account Name', 'Reference', 'Details', 'Amount', 'Job'],
 'netsuite': ['Internal ID', 'Date', 'Posting Period', 'Type', 'Document Number', 'Name', 'Memo', 'Account', 'Debit', 'Credit'],
 'euro': ['Buchungsdatum', 'Beleg', 'Konto', 'Kontobezeichnung', 'Buchungstext', 'Soll', 'Haben', 'Währung'],
}
TYPES = {
 'qb': {'INV': 'Invoice', 'RCPT': 'Payment', 'BILL': 'Bill', 'BPAY': 'Bill Payment', 'CARD': 'Credit Card Expense', 'BANK': 'Check', 'PAYR': 'Paycheck', 'JE': 'General Journal', 'SALE': 'Sales Receipt', 'DEP': 'Deposit', 'TFR': 'Transfer', 'OPEN': 'General Journal'},
 'xero': {'INV': 'Receivable Invoice', 'RCPT': 'Receivable Payment', 'BILL': 'Payable Invoice', 'BPAY': 'Payable Payment', 'CARD': 'Spend Money', 'BANK': 'Spend Money', 'PAYR': 'Manual Journal', 'JE': 'Manual Journal', 'SALE': 'Receive Money', 'DEP': 'Receive Money', 'TFR': 'Transfer', 'OPEN': 'Conversion Balance'},
 'sage': {'INV': 'SI', 'RCPT': 'SA', 'BILL': 'PI', 'BPAY': 'PP', 'CARD': 'BP', 'BANK': 'BP', 'PAYR': 'JD', 'JE': 'JD', 'SALE': 'BR', 'DEP': 'BR', 'TFR': 'JC', 'OPEN': 'JC'},
 'netsuite': {'INV': 'Invoice', 'RCPT': 'Customer Payment', 'BILL': 'Vendor Bill', 'BPAY': 'Bill Payment', 'CARD': 'Expense', 'BANK': 'Check', 'PAYR': 'Journal', 'JE': 'Journal', 'SALE': 'Cash Sale', 'DEP': 'Deposit', 'TFR': 'Transfer', 'OPEN': 'Journal'},
 'euro': {'INV': 'AR', 'RCPT': 'ZE', 'BILL': 'ER', 'BPAY': 'AZ', 'CARD': 'KK', 'BANK': 'BA', 'PAYR': 'LG', 'JE': 'MB', 'SALE': 'KA', 'DEP': 'ZE', 'TFR': 'UM', 'OPEN': 'EB'},
}
PARENT = {'1': 'Assets', '2': 'Liabilities', '3': 'Equity', '4': 'Income', '5': 'Cost of Goods Sold', '6': 'Operating Expenses', '7': 'Other Expense'}


# ---------------------------------------------------------------- labels
def build_labels(cfg, used, rng):
    L = {}
    for code in sorted(used):
        syn = SYN[code]
        over = cfg['label_over'].get(code)
        if cfg['lang'] == 'DE' and code in DE:
            primary = DE[code]
        elif over:
            primary = over[0]
        else:
            primary = syn[int(rng.integers(len(syn)))]
        alts = [x for x in syn if x != primary] + ([o for o in over[1:] if o != primary] if over else [])
        L[code] = dict(primary=primary, alts=alts, legacy=None, rename=None)
    for c, lab in cfg['merged'].items():
        if c in L:
            L[c]['primary'], L[c]['alts'] = lab, []
    for c in sorted(L):
        if c[0] == '6' and c not in cfg['merged'] and rng.random() < .14 and L[c]['alts']:
            L[c]['legacy'] = L[c]['alts'][int(rng.integers(len(L[c]['alts'])))]
            L[c]['rename'] = cfg['fy0'] + timedelta(days=int(rng.integers(75, 280)))
    return L


def ccode(cfg, code):
    s = cfg['codes']
    if s == 'none': return ''
    if s == 'same': return code
    if s == 'x10': return str(int(code) * 10)
    return SKR.get(code, str(int(code) * 10 + 3))


# ---------------------------------------------------------------- noise primitives
def typo(s, rng):
    if len(s) < 4: return s
    i = int(rng.integers(1, len(s) - 1)); k = int(rng.integers(0, 4))
    if k == 0: return s[:i] + s[i + 1:]
    if k == 1: return s[:i] + s[i] + s[i:]
    if k == 2: return s[:i] + s[i + 1] + s[i] + s[i + 2:]
    return s[:i] + chr(max(97, min(122, ord(s[i].lower()) + int(rng.choice([-1, 1]))))) + s[i + 1:]


def label_variant(label, code, lab, cc, rng):
    kinds = ['case', 'typo', 'abbrev', 'alt_name', 'whitespace', 'suffix', 'codeprefix']
    k = str(rng.choice(kinds, p=[.2, .2, .12, .28, .08, .05, .07]))
    if k == 'case':
        return str(rng.choice([label.upper(), label.lower(), label.title()])), k
    if k == 'typo': return typo(label, rng), k
    if k == 'abbrev':
        for a, b in ABBREV:
            if a in label: return label.replace(a, b, 1), k
        return typo(label, rng), 'typo'
    if k == 'alt_name':
        if lab['alts']: return lab['alts'][int(rng.integers(len(lab['alts'])))], k
        return label.upper(), 'case'
    if k == 'whitespace': return ' ' + label.replace(' ', '  ', 1) + ' ', k
    if k == 'suffix': return label + str(rng.choice([' - General', ' (old)', ' - Misc', '*'])), k
    return (f"{cc} - {label}" if cc else f"Acct - {label}"), k


def digit_err(c, rng):
    s = str(c)
    if len(s) < 3: return c + 100
    i = int(rng.integers(0, len(s) - 1))
    s2 = s[:i] + s[i + 1] + s[i] + s[i + 2:] if s[i] != s[i + 1] else s[:i] + str((int(s[i]) + 1) % 10) + s[i + 1:]
    if s2[0] == '0' or int(s2) == c: s2 = str(c + 1000)
    return int(s2)


def fmtnum(c, ns, cur, style=None):
    v = c / 100
    if style == 'nodec' and c % 100 == 0: s = f"{int(v)}"
    elif ns == 'eu': s = f"{v:,.2f}".replace(',', '_').replace('.', ',').replace('_', '.')
    elif ns == 'comma': s = f"{v:,.2f}"
    else: s = f"{v:.2f}"
    if style == 'dollar': s = SYM[cur] + s
    if style == 'space': s = s + ' '
    return s


def fmt_date(r, cfg):
    d = r['date']; ds = r['datestyle']
    if ds == 'blank': return ''
    if ds == 'serial': return str((d - date(1899, 12, 30)).days)
    if ds: return d.strftime(ds)
    return d.strftime(DSTYLE[cfg['dstyle']])


# ---------------------------------------------------------------- records + corruption
def make_recs(cfg, truth, L):
    recs = []
    for t in truth:
        if not t['in_export']: continue
        lab = L[t['code']]
        legacy = bool(lab['legacy']) and t['date'] < lab['rename']
        recs.append(dict(t=t, label=lab['legacy'] if legacy else lab['primary'], ccode=ccode(cfg, t['code']), date=t['date'],
                         dr=t['dr'], cr=t['cr'], desc=t['desc'], ref=t['ref'], cp=t['cp'], src=t['src'],
                         errs=['legacy_label'] if legacy else [], negdeb=False, suffix=False, amtstyle=None,
                         datestyle=None, uncat=False))
    return recs


def corrupt(r, cfg, L, rng, M, flat, moji_ranges):
    t = r['t']; code = t['code']; roll = rng.random
    if code[0] == '6' and t['src'] != 'OPEN' and roll() < M['uncat']:
        r['uncat'] = True
        pool = [cfg['uncat_label']] + (UNCAT_LABELS if cfg['lang'] == 'EN' and flat else [])
        r['label'] = str(rng.choice(pool)) if flat else cfg['uncat_label']
        if cfg['codes'] != 'none': r['ccode'] = '9999'
        r['errs'].append('uncategorized_label')
    elif flat and roll() < M['label']:
        r['label'], kind = label_variant(r['label'], code, L[code], r['ccode'], rng)
        r['errs'].append('label_variant:' + kind)
    if flat and not r['uncat'] and roll() < M['miss_acct']:
        r['label'] = ''
        if roll() < .6: r['ccode'] = ''
        r['errs'].append('missing_account')
    # dates
    if roll() < M['date']:
        default = DSTYLE[cfg['dstyle']]
        f = str(rng.choice([x for x in ALT_FMT if x != default]))
        r['datestyle'] = f
        amb = f in AMBIG_FMT and r['date'].day <= 12 and r['date'].day != r['date'].month
        r['errs'].append('date_alt_format' + (':ambiguous' if amb else ''))
    elif roll() < M['serial']:
        r['datestyle'] = 'serial'; r['errs'].append('date_excel_serial')
    if flat and roll() < M['miss_date'] and t['src'] != 'OPEN':
        r['datestyle'] = 'blank'; r['errs'].append('missing_date')
    # amounts
    if roll() < M['flip'] and t['src'] != 'OPEN':
        r['dr'], r['cr'] = r['cr'], r['dr']; r['errs'].append('sign_flip')
    elif roll() < M['digit'] and t['src'] != 'OPEN':
        if r['dr']: r['dr'] = digit_err(r['dr'], rng)
        else: r['cr'] = digit_err(r['cr'], rng)
        r['errs'].append('amount_digit_error')
    if roll() < M['amt']:
        r['amtstyle'] = str(rng.choice(['dollar', 'nodec', 'space', 'minus'] if cfg['fmt'] == 'sage' else ['dollar', 'nodec', 'space']))
        r['errs'].append('amount_format')
    if cfg['fmt'] != 'sage':
        if r['cr'] > 0 and roll() < M['negdeb']:
            r['negdeb'] = True; r['errs'].append('credit_as_negative_debit')
        elif roll() < M['negdeb'] / 2:
            r['suffix'] = True; r['errs'].append('drcr_suffix')
    # text
    if roll() < M['desc_blank'] and t['src'] != 'OPEN':
        r['desc'] = ''; r['errs'].append('blank_description')
    elif roll() < M['ws']:
        r['desc'] = ' ' + r['desc'].replace(' ', '  ', 1) + ' '; r['errs'].append('whitespace')
    if cfg.get('moji') and any(a <= r['date'] <= b for a, b in moji_ranges):
        txt = (r['label'] + r['desc'] + r['cp'])
        if any(ord(ch) > 127 for ch in txt):
            fix = lambda x: x.encode('utf-8').decode('latin-1')
            r['label'], r['desc'], r['cp'] = fix(r['label']), fix(r['desc']), fix(r['cp'])
            r['errs'].append('mojibake')


# ---------------------------------------------------------------- cell emitters
def split_cells(r, cfg):
    ns, cur, zero = cfg['num'], cfg['cur'], cfg['zero']
    z = '' if zero == 'blank' else fmtnum(0, ns, cur)
    st = r['amtstyle']
    dr_s = fmtnum(r['dr'], ns, cur, st) if r['dr'] else z
    cr_s = fmtnum(r['cr'], ns, cur, st) if r['cr'] else z
    if r['negdeb'] and r['cr']: dr_s, cr_s = '-' + fmtnum(r['cr'], ns, cur, st), z
    if r['suffix']:
        if r['dr']: dr_s += ' DR'
        if r['cr']: cr_s += ' CR'
    return dr_s, cr_s


def signed_cell(r, cfg):
    v = r['dr'] - r['cr']; st = r['amtstyle']
    base = fmtnum(abs(v), cfg['num'], cfg['cur'], 'dollar' if st == 'dollar' else 'nodec' if st == 'nodec' else None)
    if r['suffix']: return base + (' Dr' if v >= 0 else ' Cr')
    if v < 0: return ('-' + base) if st == 'minus' else '(' + base + ')'
    return base


def acct_label(r, cfg):
    return r['label']


def emit(r, cfg, fmt):
    t = r['t']; ds = fmt_date(r, cfg); n = int(t['txn_id'].split('-')[1]); ty = TYPES[fmt][r['src']]
    if fmt == 'xero':
        dr, cr = split_cells(r, cfg)
        return [ds, r['ccode'], r['label'], ty, r['desc'], r['ref'], dr, cr]
    if fmt == 'sage':
        job = f"J-{1000 + (n * 7) % 60}" if t['code'] in ('5000', '5100', '5300') else ''
        return [n, ds, ty, r['ccode'], r['label'], r['ref'], r['desc'], signed_cell(r, cfg), job]
    if fmt == 'netsuite':
        dr, cr = split_cells(r, cfg)
        acct = r['label'] if (r['uncat'] or not r['label'] or r['label'].startswith(r['ccode'] + ' - ')) else \
            f"{int(t['code']) // 1000 * 1000} {PARENT[t['code'][0]]} : {r['ccode']} {r['label']}"
        return [n, ds, f"{MON[r['date'].month-1]} {r['date'].year}", ty, r['ref'], r['cp'], r['desc'], acct, dr, cr]
    if fmt == 'euro':
        dr, cr = split_cells(r, cfg)
        return [ds, r['ref'], r['ccode'], r['label'], r['desc'], dr, cr, cfg['cur']]
    dr, cr = split_cells(r, cfg)       # qb detail row
    return ['', ty, ds, r['ref'], r['cp'], r['desc'], dr, cr]


MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']


def near_dup(r, rng):
    r2 = dict(r); r2['errs'] = list(r['errs'])
    k = int(rng.integers(3))
    if k == 0: r2['ref'] = r['ref'] + ' '
    elif k == 1: r2['desc'] = r['desc'].upper()
    else: r2['datestyle'] = '%Y-%m-%d' if r['datestyle'] != '%Y-%m-%d' else '%d %b %Y'
    return r2


def with_dups(recs, rng, M):
    """returns list of (rec, is_dup_kind or None) with duplicates inserted immediately or a few rows later."""
    pending, out = {}, []
    for i, r in enumerate(recs):
        out.append((r, None))
        for d in pending.pop(i, []): out.append(d)
        if r['t']['src'] != 'OPEN':
            u = rng.random()
            if u < M['dup']: d = (dict(r), 'duplicate_exact')
            elif u < M['dup'] + M['ndup']: d = (near_dup(r, rng), 'duplicate_near')
            else: continue
            d[0]['errs'] = list(r['errs'])
            k = 0 if rng.random() < .5 else int(rng.integers(1, 30))
            if k == 0: out.append(d)
            else: pending.setdefault(i + k, []).append(d)
    for k in sorted(pending): out += pending[k]
    return out


# ---------------------------------------------------------------- layouts
def build_flat(cfg, recs, rng, M):
    fmt = cfg['fmt']
    key = (lambda r: (r['t']['code'], r['date'], r['t']['txn_id'], r['t']['line_id'])) if cfg.get('sort') == 'account' else \
          (lambda r: (r['date'], r['t']['txn_id'], r['t']['line_id']))
    recs = sorted(recs, key=key)
    seq = with_dups(recs, rng, M)
    rows = []
    for ttl in cfg.get('titles', []):
        rows.append(([ttl], dict(kind='title' if ttl else 'blank')))
    rows.append((HDR[fmt], dict(kind='header')))
    data_n, cur_m, msum = 0, None, 0
    tot_dr = tot_cr = 0
    for r, dk in seq:
        m = (r['date'].year, r['date'].month)
        if fmt == 'sage' and cur_m and m != cur_m:
            rows.append((['', '', '', '', '', '', f"Total for {MON[cur_m[1]-1]} {cur_m[0]}", fmtnum(abs(msum), cfg['num'], cfg['cur']) if msum >= 0 else '(' + fmtnum(abs(msum), cfg['num'], cfg['cur']) + ')', ''], dict(kind='subtotal')))
            msum = 0
        cur_m = m if (fmt == 'sage' and r['datestyle'] != 'blank') or fmt != 'sage' else cur_m
        if fmt == 'sage' and data_n and data_n % 450 == 0:
            rows.append((HDR[fmt], dict(kind='repeat_header')))
        errs = list(r['errs']) + ([dk] if dk else [])
        rows.append((emit(r, cfg, fmt), dict(kind='data', line_id=r['t']['line_id'], errs=errs, dup=bool(dk))))
        data_n += 1; msum += r['dr'] - r['cr']; tot_dr += r['dr']; tot_cr += r['cr']
    if fmt == 'sage':
        rows.append((['', '', '', '', '', '', f"Total for {MON[cur_m[1]-1]} {cur_m[0]}", fmtnum(abs(msum), cfg['num'], cfg['cur']), ''], dict(kind='subtotal')))
    rows.append((['' for _ in HDR[fmt]], dict(kind='blank')))
    tot = ['' for _ in HDR[fmt]]
    if fmt in ('xero', 'netsuite', 'euro'):
        tot[{'xero': 2, 'netsuite': 7, 'euro': 3}[fmt]] = 'Total' if fmt != 'euro' else 'Summe'
        tot[-3 if fmt == 'euro' else -2 if fmt != 'xero' else -2] = fmtnum(tot_dr, cfg['num'], cfg['cur'])
        tot[-2 if fmt == 'euro' else -1] = fmtnum(tot_cr, cfg['num'], cfg['cur'])
        if fmt == 'xero': tot[-2], tot[-1] = fmtnum(tot_dr, cfg['num'], cfg['cur']), fmtnum(tot_cr, cfg['num'], cfg['cur'])
    else:
        tot[6] = 'GRAND TOTAL'; tot[7] = fmtnum(abs(tot_dr - tot_cr), cfg['num'], cfg['cur'])
    rows.append((tot, dict(kind='grand_total')))
    rows.append((['Report generated 2026-01-14 09:12 by admin'], dict(kind='footer')))
    return rows


def build_qb(cfg, recs, rng, M):
    sections = {}
    for r in recs:
        sections.setdefault(r['label'], []).append(r)
    order = sorted(sections, key=lambda k: (min(x['t']['code'] for x in sections[k]) if not any(x['uncat'] for x in sections[k]) else '9999', k))
    rows = [([ttl], dict(kind='title' if ttl else 'blank')) for ttl in cfg['titles']]
    rows.append((HDR['qb'], dict(kind='header')))
    gdr = gcr = 0
    for lab in order:
        rs = sorted(sections[lab], key=lambda r: (r['date'], r['t']['txn_id']))
        rows.append(([lab, '', '', '', '', '', '', ''], dict(kind='section_header')))
        sdr = scr = 0
        for r, dk in with_dups(rs, rng, M):
            errs = list(r['errs']) + ([dk] if dk else [])
            rows.append((emit(r, cfg, 'qb'), dict(kind='data', line_id=r['t']['line_id'], errs=errs, dup=bool(dk))))
            sdr += r['dr']; scr += r['cr']
        rows.append(([f"Total {lab}", '', '', '', '', '', fmtnum(sdr, cfg['num'], cfg['cur']), fmtnum(scr, cfg['num'], cfg['cur'])], dict(kind='section_total')))
        gdr += sdr; gcr += scr
    rows.append((['TOTAL', '', '', '', '', '', fmtnum(gdr, cfg['num'], cfg['cur']), fmtnum(gcr, cfg['num'], cfg['cur'])], dict(kind='grand_total')))
    return rows


def write_csv(path, rows, cfg, rowmap):
    enc = 'utf-8-sig' if cfg.get('moji') else 'utf-8'
    fname = path.split('/')[-1]
    with open(path, 'w', newline='', encoding=enc) as f:
        w = csv.writer(f)
        for i, (cells, meta) in enumerate(rows, 1):
            w.writerow(cells)
            rowmap.append(dict(client_id=cfg['id'], file=fname, sheet='', row_number=i, row_kind=meta['kind'],
                               line_id=meta.get('line_id', ''), is_duplicate=int(meta.get('dup', False)),
                               error_types=';'.join(meta.get('errs', []))))


# ---------------------------------------------------------------- cash book (xlsx)
def build_cashbook(cfg, truth, rng, M, rowmap, path):
    from openpyxl import Workbook
    from openpyxl.styles import Font
    lines = [t for t in truth if t['in_export']]
    lines.sort(key=lambda t: (t['date'], t['line_id']))
    wb = Workbook(); wb.remove(wb.active)
    A = Font(name='Arial', size=10); AB = Font(name='Arial', size=10, bold=True)
    fy0 = cfg['fy0']; fname = path.split('/')[-1]
    by_q = {}
    for t in lines:
        q = (t['date'].month - 1) // 3 + 1
        by_q.setdefault(q, []).append(t)
    for q in sorted(by_q):
        sh = wb.create_sheet(f"Q{q} {fy0.year}" if q != 3 else f"Q{q}-{fy0.year}")
        hdr = ['Date', 'Payee', 'Category', 'Notes', 'Money In', 'Money Out'] if q % 2 else ['Date', 'Paid to / from', 'Category', 'Memo', 'In', 'Out']
        rown = [0]
        def put(cells, kind, line_id='', errs=None, dup=False, bold=False):
            rown[0] += 1
            for j, v in enumerate(cells, 1):
                c = sh.cell(row=rown[0], column=j, value=v); c.font = AB if bold else A
                if isinstance(v, datetime): c.number_format = 'mm/dd/yyyy'
            rowmap.append(dict(client_id=cfg['id'], file=fname, sheet=sh.title, row_number=rown[0], row_kind=kind,
                               line_id=line_id, is_duplicate=int(dup), error_types=';'.join(errs or [])))
        put([f"Sunrise Property Holdings - Cash Book {fy0.year} Q{q}"], 'title', bold=True)
        put([], 'blank')
        put(hdr, 'header', bold=True)
        cur_m, msum_in, msum_out, n = None, 0, 0, 0
        def subtotal():
            put(['', '', f"Total {MON[cur_m-1]}", '', round(msum_in / 100, 2), round(msum_out / 100, 2)], 'subtotal', bold=True)
        pend = {}
        out = []
        for i, t in enumerate(by_q[q]):
            out.append((t, None))
            for d in pend.pop(i, []): out.append(d)
            u = rng.random()
            if u < M['dup']:
                k = 0 if rng.random() < .5 else int(rng.integers(1, 12))
                (out.append((t, 'duplicate_exact')) if k == 0 else pend.setdefault(i + k, []).append((t, 'duplicate_exact')))
        for k in sorted(pend): out += pend[k]
        for t, dk in out:
            if cur_m is not None and t['date'].month != cur_m:
                subtotal(); msum_in = msum_out = 0; put([], 'blank')
            cur_m = t['date'].month
            errs = [dk] if dk else []
            amt_c = t['dr'] or t['cr']
            if rng.random() < M['digit']:
                amt_c = digit_err(amt_c, rng); errs.append('amount_digit_error')
            is_in = t['cr'] > 0
            if rng.random() < .003:
                is_in = not is_in; errs.append('swapped_direction')
            # date
            d = datetime(t['date'].year, t['date'].month, t['date'].day); dcell = d
            u = rng.random()
            if u < .06: dcell = f"{MON[d.month-1]} {d.day}"; errs.append('date_no_year')
            elif u < .09: dcell = f"{d.day}{'th' if 10 < d.day < 14 else {1:'st',2:'nd',3:'rd'}.get(d.day % 10,'th')} {d.strftime('%B')}"; errs.append('date_text_ordinal')
            elif u < .10: dcell = (t['date'] - date(1899, 12, 30)).days; errs.append('date_excel_serial')
            elif u < .12: dcell = d.strftime('%m/%d/%Y'); errs.append('date_text_string')
            # category
            labs = CB_LABELS.get(t['code'], [SYN[t['code']][0]])
            cat = labs[int(rng.choice(len(labs), p=np.array([.35, .25] + [.4 / max(1, len(labs) - 2)] * (len(labs) - 2)) if len(labs) > 2 else None))]
            if rng.random() < .04: cat = typo(cat, rng); errs.append('label_variant:typo')
            if rng.random() < M['miss_acct']: cat = None; errs.append('missing_account')
            elif rng.random() < M['uncat']: cat = str(rng.choice(['Misc', '???', 'check', 'TBC'])); errs.append('uncategorized_label')
            payee = t['cp'] if rng.random() > .05 else None
            notes = t['desc'] if rng.random() < .55 else None
            # amount cell
            v = round(amt_c / 100, 2); cell = v
            u = rng.random()
            if u < .02: cell = f"${v:,.2f}"; errs.append('amount_format')
            elif u < .025: cell = f"{v:.0f} (cash)" if v == int(v) else f"{v} cash"; errs.append('amount_format')
            elif u < .028: cell = f"approx {v:.0f}"; errs.append('amount_format')
            row = [dcell, payee, cat, notes, cell if is_in else None, None if is_in else cell]
            put(row, 'data', t['line_id'], errs, bool(dk))
            if is_in: msum_in += amt_c
            else: msum_out += amt_c
            n += 1
            if rng.random() < .015: put([], 'blank')
        if cur_m is not None: subtotal()
        sh.column_dimensions['A'].width = 14; sh.column_dimensions['B'].width = 28
        sh.column_dimensions['C'].width = 24; sh.column_dimensions['D'].width = 40
    wb.save(path)
