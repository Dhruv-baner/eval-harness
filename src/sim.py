# -*- coding: utf-8 -*-
"""Double-entry ledger simulator. Produces balanced journal entries (the ground truth)."""
import math, random
from datetime import date, timedelta
from collections import defaultdict
import numpy as np
from refdata import *

MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']


def Dr(code, amt, desc='', cp=''):
    return (code, int(amt), 0, desc, cp)


def Cr(code, amt, desc='', cp=''):
    return (code, 0, int(amt), desc, cp)


def month_spans(fy0):
    spans, y, m = [], fy0.year, fy0.month
    for _ in range(12):
        s = date(y, m, 1)
        ny, nm = (y + 1, 1) if m == 12 else (y, m + 1)
        spans.append((s, date(ny, nm, 1) - timedelta(days=1)))
        y, m = ny, nm
    return spans


class Sim:
    def __init__(s, cfg):
        s.cfg = cfg
        s.rng = np.random.default_rng(cfg['seed'])
        s.py = random.Random(cfg['seed'])
        s.fy0 = cfg['fy0']
        s.spans = month_spans(s.fy0)
        s.fy1 = s.spans[-1][1]
        s.ents, s.seq = [], 0
        s.docn = defaultdict(int)
        s.tax = defaultdict(int)       # (y,m) -> net VAT/sales tax accrued
        s.ptax = defaultdict(int)      # payroll liabilities accrued
        s.card = defaultdict(int)      # card charges by month
        s.tips = defaultdict(int)      # tips by iso week
        s.remitted_tax, s.remitted_ptax = set(), set()
        s.first_tax = s.first_ptax = True
        s.sticky = {}
        s.customers = s.make_customers(cfg.get('cust', 'biz'), cfg.get('ncust', 90))

    # ---------- helpers ----------
    def make_customers(s, kind, n):
        if kind == 'payers':
            return VEND['payers']['US']
        reg = s.cfg['reg']
        out = set()
        while len(out) < n:
            if kind == 'law' and s.py.random() < .5:
                out.add(f"{s.py.choice(FIRST)} {s.py.choice(LAST)}")
            else:
                out.add(f"{s.py.choice(ADJ)} {s.py.choice(NOUN)} {s.py.choice(SUF[reg])}")
        return sorted(out)

    def num(s, pfx):
        base = {'INV': 1000, 'BILL': 5000, 'RCPT': 2000, 'CHK': 3000, 'JE': 100, 'PAY': 700, 'ACH': 9000}.get(pfx, 1)
        s.docn[pfx] += 1
        return f"{pfx}-{base + s.docn[pfx]}"

    def pick(s, seq):
        return seq[int(s.rng.integers(len(seq)))]

    def vend(s, key):
        pool = VEND[key].get(s.cfg['reg'], VEND[key]['US'])
        return s.pick(pool)

    def amt(s, mu, sigma, lo=1.0, hi=None, rnd=None):
        v = float(s.rng.lognormal(math.log(mu) - sigma ** 2 / 2, sigma)) if sigma > 0 else float(mu)
        v = max(lo, v)
        if hi:
            v = min(hi, v)
        if rnd:
            v = round(v / rnd) * rnd or rnd
        return int(round(v * 100))

    def season(s, d):
        return s.cfg.get('season', [1] * 12)[d.month - 1]

    def rand_day(s, span, weekend=False):
        a, b = span
        n = (b - a).days + 1
        for _ in range(12):
            d = a + timedelta(days=int(s.rng.integers(0, n)))
            if weekend or d.weekday() < 5:
                return d
        return a

    def bizday(s, d):
        while d.weekday() >= 5:
            d += timedelta(days=1)
        return d

    def post(s, d, src, ref, lines):
        if d > s.fy1 or d < s.fy0:
            return False
        lines = [l for l in lines if l[1] != 0 or l[2] != 0]
        assert sum(l[1] for l in lines) == sum(l[2] for l in lines), (ref, lines)
        s.seq += 1
        s.ents.append(dict(date=d, src=src, ref=ref, lines=lines, seq=s.seq))
        return True

    def tax_on(s, net, taxable=True):
        r = s.cfg.get('tax', 0.0)
        return int(round(net * r)) if (r and taxable) else 0

    def desc_bill(s, v, d):
        n = int(s.rng.integers(1000, 99999))
        return s.pick([f"{v} Inv {n}", f"{v} - Invoice #{n}", f"{v} INV{n}", f"{v} - {MON[d.month-1]} {d.year} statement", f"{v}"])

    def desc_card(s, v):
        n4 = int(s.rng.integers(1000, 9999))
        city = s.pick(CITIES[s.cfg['reg']])
        V = v.upper()
        return s.pick([f"SQ *{V} {n4}", f"POS PURCHASE {V} {city}", f"{V} #{n4}", f"CARD {V} {city}", f"PAYPAL *{V}", f"{v}"])

    def desc_direct(s, v):
        V = v.upper()
        return s.pick([f"ACH DEBIT {V}", f"{v} autopay", f"DD {V}", f"Bank draft - {v}", f"{v} - monthly"])

    # ---------- flow generators ----------
    def g_pos(s, p):
        d = s.fy0
        revs = p['rev'] if isinstance(p['rev'], list) else [(p['rev'], 1.0)]
        locs = p.get('locs', 1)
        while d <= s.fy1:
            if p.get('weekend', False) or d.weekday() < 5:
                for loc in range(locs):
                    n = 1 if p.get('batch') else int(s.rng.poisson(p['rate'] * s.season(d)))
                    for _ in range(n):
                        net = s.amt(p['mu'], p['sigma'], lo=p.get('lo', 5))
                        tax = s.tax_on(net, p.get('taxable', True))
                        tips = int(net * p.get('tips', 0) * s.rng.uniform(.7, 1.2)) if p.get('tips') else 0
                        fee = int(round((net + tax + tips) * p.get('fee', 0)))
                        if p.get('batch'):
                            desc = f"Daily sales summary - {p.get('locnames', ['Main'])[loc % len(p.get('locnames', ['Main']))]} - {d:%Y-%m-%d}"
                        else:
                            desc = s.pick(p['desc']) + (f" #{int(s.rng.integers(10000,99999))}" if p.get('ordno') else '')
                        cp = p.get('cp', 'POS')
                        lines = [Dr('1000', net + tax + tips - fee, desc, cp), Dr('6810', fee, f"Processing fee - {desc}", p.get('proc', 'Stripe'))]
                        rem = net
                        for i, (rc, sh) in enumerate(revs):
                            a = rem if i == len(revs) - 1 else int(net * sh)
                            rem -= a
                            lines.append(Cr(rc, a, desc, cp))
                        lines += [Cr('2300', tax, f"Tax - {desc}", cp), Cr('2210', tips, f"Card tips - {desc}", cp)]
                        if p.get('cogs'):
                            c = int(net * p['cogs'] * s.rng.uniform(.92, 1.08))
                            lines += [Dr('5000', c, f"COGS - {desc}", cp), Cr('1200', c, f"Inventory relief - {desc}", cp)]
                        s.tax[(d.year, d.month)] += tax
                        s.tips[d.isocalendar()[:2]] += tips
                        s.post(d, 'SALE', s.num('PAY') if not p.get('batch') else f"DS-{d:%Y%m%d}-{loc+1}", lines)
            d += timedelta(days=1)

    def g_tips_payout(s, p):
        for (yy, ww), amt_ in sorted(s.tips.items()):
            d = date.fromisocalendar(yy, ww, 5) + timedelta(days=7)
            if amt_:
                s.post(d, 'PAYR', s.num('PAY'), [Dr('2210', amt_, f"Tip payout week {ww}", 'Staff'), Cr('1000', amt_, f"Tip payout week {ww}", 'Staff')])

    def receive(s, d, gross, ref, cust, p):
        if s.rng.random() < p.get('baddebt', .01):
            return
        lag = int(max(3, s.rng.normal(p.get('lag', 30), p.get('lag_sd', 10))))
        pd_ = s.bizday(d + timedelta(days=lag))
        short = int(gross * s.rng.uniform(.05, .25)) if s.rng.random() < p.get('short', 0) else 0
        lines = [Dr('1000', gross - short, f"Payment received {ref} - {cust}", cust)]
        if short:
            lines.append(Dr(p.get('short_code', '4900'), short, f"Adjustment {ref}", cust))
        lines.append(Cr('1100', gross, f"Payment received {ref} - {cust}", cust))
        s.post(pd_, 'RCPT', s.num('RCPT'), lines)

    def g_invoice(s, p):
        for span in s.spans:
            n = int(s.rng.poisson(p['rate'] * s.season(span[0])))
            for _ in range(n):
                d = s.rand_day(span)
                net = s.amt(p['mu'], p['sigma'], lo=p.get('lo', 20))
                tax = s.tax_on(net, p.get('taxable', True))
                gross = net + tax
                cust = s.pick(s.customers)
                ref = s.num('INV')
                lines = [Dr('1100', gross, f"Invoice {ref} - {cust}", cust), Cr(p['rev'], net, f"Invoice {ref} - {cust}", cust),
                         Cr('2300', tax, f"Tax {ref}", cust)]
                if p.get('cogs'):
                    c = int(net * p['cogs'] * s.rng.uniform(.9, 1.1))
                    lines += [Dr('5000', c, f"COGS {ref}", cust), Cr('1200', c, f"Inventory relief {ref}", cust)]
                s.tax[(d.year, d.month)] += tax
                s.post(d, 'INV', ref, lines)
                s.receive(d, gross, ref, cust, p)

    def pay_bill(s, d, gross, ref, v, p):
        lag = int(max(3, s.rng.normal(p.get('lag', 30), 8)))
        pd_ = s.bizday(d + timedelta(days=lag))
        chk = s.num('CHK') if s.cfg['reg'] == 'US' else s.num('ACH')
        s.post(pd_, 'BPAY', chk, [Dr('2000', gross, f"Payment {chk} - {v} ({ref})", v), Cr('1000', gross, f"Payment {chk} - {v} ({ref})", v)])

    def g_bill(s, p):
        for span in s.spans:
            n = int(s.rng.poisson(p['rate'] * s.season(span[0])))
            for _ in range(n):
                d = s.rand_day(span)
                net = s.amt(p['mu'], p['sigma'], lo=p.get('lo', 20), rnd=p.get('rnd'))
                tax = s.tax_on(net, p.get('taxable', True)) if s.cfg.get('input_tax') else 0
                v = s.vend(p['vend'])
                ref = s.num('BILL')
                desc = s.desc_bill(v, d)
                tgt = p.get('asset', p['exp'])
                s.tax[(d.year, d.month)] -= tax
                s.post(d, 'BILL', ref, [Dr(tgt, net, desc, v), Dr('2300', tax, f"Input tax - {desc}", v), Cr('2000', net + tax, desc, v)])
                s.pay_bill(d, net + tax, ref, v, p)

    def g_card(s, p):
        for span in s.spans:
            n = int(s.rng.poisson(p['rate'] * s.season(span[0])))
            for _ in range(n):
                d = s.rand_day(span, weekend=True)
                net = s.amt(p['mu'], p['sigma'], lo=p.get('lo', 3))
                tax = s.tax_on(net, p.get('taxable', True)) if s.cfg.get('input_tax') else 0
                v = s.vend(p['vend'])
                desc = s.desc_card(v)
                s.tax[(d.year, d.month)] -= tax
                s.card[(d.year, d.month)] += net + tax
                s.post(d, 'CARD', s.num('ACH'), [Dr(p['exp'], net, desc, v), Dr('2300', tax, f"Input tax - {desc}", v), Cr('2100', net + tax, desc, v)])

    def g_direct(s, p):
        for span in s.spans:
            n = int(s.rng.poisson(p['rate'] * s.season(span[0])))
            for _ in range(n):
                d = s.rand_day(span)
                net = s.amt(p['mu'], p['sigma'], lo=p.get('lo', 3), rnd=p.get('rnd'))
                tax = s.tax_on(net, p.get('taxable', False)) if s.cfg.get('input_tax') else 0
                v = s.vend(p['vend'])
                desc = p.get('desc') or s.desc_direct(v)
                s.tax[(d.year, d.month)] -= tax
                s.post(d, 'BANK', s.num('ACH'), [Dr(p['exp'], net, desc, v), Dr('2300', tax, f"Input tax - {desc}", v), Cr('1000', net + tax, desc, v)])

    def g_recurring(s, p):
        every = p.get('every', 1)
        for i, span in enumerate(s.spans):
            if i % every != p.get('offset', 0):
                continue
            d = s.bizday(span[0] + timedelta(days=p['day'] - 1))
            net = s.amt(p['mu'], p.get('sigma', 0), rnd=p.get('rnd'))
            tax = s.tax_on(net, p.get('taxable', True)) if s.cfg.get('input_tax') else 0
            v = s.sticky.setdefault(p['code'] + p['vend'], s.vend(p['vend']))
            s.tax[(d.year, d.month)] -= tax
            desc = p.get('desc', '') and f"{p['desc']} - {MON[d.month-1]} {d.year}" or s.desc_direct(v)
            if p.get('via') == 'bill':
                ref = s.num('BILL')
                s.post(d, 'BILL', ref, [Dr(p['code'], net, desc, v), Dr('2300', tax, f"Input tax - {desc}", v), Cr('2000', net + tax, desc, v)])
                s.pay_bill(d, net + tax, ref, v, p)
            else:
                s.post(d, 'BANK', s.num('ACH'), [Dr(p['code'], net, desc, v), Dr('2300', tax, f"Input tax - {desc}", v), Cr('1000', net + tax, desc, v)])

    def g_prepaid(s, p):
        d = s.bizday(s.fy0 + timedelta(days=4))
        prem = s.amt(p['mu'], 0)
        v = s.vend(p['vend'])
        s.post(d, 'BANK', s.num('ACH'), [Dr('1300', prem, f"Annual insurance premium - {v}", v), Cr('1000', prem, f"Annual insurance premium - {v}", v)])
        m = prem // 12
        for span in s.spans:
            s.post(span[1], 'JE', s.num('JE'), [Dr('6500', m, f"Prepaid insurance amortization {MON[span[1].month-1]}", ''), Cr('1300', m, f"Prepaid insurance amortization {MON[span[1].month-1]}", '')])

    def g_payroll(s, p):
        dates = []
        if p['freq'] == 'biweekly':
            d = s.fy0
            while d.weekday() != 4:
                d += timedelta(days=1)
            while d <= s.fy1:
                dates.append(d)
                d += timedelta(days=14)
        elif p['freq'] == 'semimonthly':
            for span in s.spans:
                dates += [s.bizday(span[0] + timedelta(days=14)), s.bizday(span[1] - timedelta(days=2 if span[1].weekday() >= 5 else 0))]
        else:
            for span in s.spans:
                d = span[1]
                while d.weekday() >= 5:
                    d -= timedelta(days=1)
                dates.append(d)
        for d in dates:
            gross = s.amt(p['mu'], p['sigma'])
            er = int(gross * p['ertax']); ben = int(gross * p.get('ben', 0))
            wh = int(gross * p.get('wh', .22)); net = gross - wh
            lines, rem = [], gross
            for i, (code, share, lbl) in enumerate(p['split']):
                a = rem if i == len(p['split']) - 1 else int(gross * share)
                rem -= a
                lines.append(Dr(code, a, f"Payroll {d:%b %d} - {lbl}", p['agent']))
            lines += [Dr('6010', er, f"Employer taxes {d:%b %d}", p['agent'])]
            if ben:
                lines.append(Dr('6020', ben, f"Employee benefits {d:%b %d}", 'Benefits provider'))
            lines += [Cr('1000', net + ben, f"Net pay & benefits {d:%b %d}", p['agent']), Cr('2310', wh + er, f"Payroll liabilities {d:%b %d}", p['agent'])]
            s.ptax[(d.year, d.month)] += wh + er
            s.post(d, 'PAYR', s.num('PAY'), lines)

    def g_owner(s, p):
        for i, span in enumerate(s.spans):
            if i % p.get('every', 1) == 0:
                d = s.bizday(span[0] + timedelta(days=p.get('day', 27)))
                a = s.amt(p['mu'], .1, rnd=p.get('round', 500))
                s.post(d, 'BANK', s.num('ACH'), [Dr('3200', a, p.get('desc', 'Owner draw'), 'Owner'), Cr('1000', a, p.get('desc', 'Owner draw'), 'Owner')])

    def g_accrual(s, p):
        for i, span in enumerate(s.spans):
            if s.rng.random() < p['prob']:
                a = s.amt(p['mu'], p['sigma'], rnd=p.get('round', 100))
                s.post(span[1], 'JE', s.num('JE'), [Dr(p['code'], a, f"Accrual - {MON[span[1].month-1]} month-end", ''), Cr('2200', a, f"Accrual - {MON[span[1].month-1]} month-end", '')])
                nxt = span[1] + timedelta(days=1)
                s.post(s.bizday(nxt), 'JE', s.num('JE'), [Dr('2200', a, f"Reverse accrual - {MON[span[1].month-1]}", ''), Cr(p['code'], a, f"Reverse accrual - {MON[span[1].month-1]}", '')])

    def g_refund(s, p):
        for span in s.spans:
            for _ in range(int(s.rng.poisson(p['rate']))):
                d = s.rand_day(span)
                a = s.amt(p['mu'], p['sigma'], lo=2)
                cust = s.pick(s.customers) if s.customers else 'Customer'
                s.post(d, 'BANK', s.num('ACH'), [Dr('4900', a, f"Refund - {cust}", cust), Cr('1000', a, f"Refund - {cust}", cust)])

    def g_transfer(s, p):
        for span in s.spans:
            for _ in range(int(s.rng.poisson(p['rate']))):
                d = s.rand_day(span)
                a = s.amt(p['mu'], p['sigma'], rnd=p.get('round', 500))
                s.post(d, 'TFR', s.num('JE'), [Dr('1010', a, 'Transfer to savings', 'Bank'), Cr('1000', a, 'Transfer to savings', 'Bank')])
                if s.rng.random() < .5:
                    d2 = s.bizday(d + timedelta(days=int(s.rng.integers(5, 40))))
                    s.post(d2, 'TFR', s.num('JE'), [Dr('1000', a, 'Transfer from savings', 'Bank'), Cr('1010', a, 'Transfer from savings', 'Bank')])

    def g_subs(s, p):
        active = []
        for i, span in enumerate(s.spans):
            active = [c for c in active if s.rng.random() > p.get('churn', .02)]
            for _ in range(int(s.rng.poisson(p['join']))):
                active.append(dict(name=f"{s.py.choice(ADJ)} {s.py.choice(NOUN)} #{int(s.rng.integers(100,999))}",
                                   plan=s.pick(p['plans']), day=int(s.rng.integers(1, 28))))
            if i == 0:
                for _ in range(p['n0']):
                    active.append(dict(name=f"{s.py.choice(ADJ)} {s.py.choice(NOUN)} #{int(s.rng.integers(100,999))}",
                                       plan=s.pick(p['plans']), day=int(s.rng.integers(1, 28))))
            for c in active:
                d = span[0] + timedelta(days=c['day'] - 1)
                a = int(c['plan'] * 100)
                fee = int(a * .029) + 30
                desc = f"Stripe charge - {c['name']} - ${c['plan']} plan"
                s.post(d, 'SALE', s.num('PAY'), [Dr('1000', a - fee, desc, c['name']), Dr('6810', fee, f"Stripe fee - {c['name']}", 'Stripe'), Cr('4200', a, desc, c['name'])])

    def g_annual(s, p):
        for i, span in enumerate(s.spans):
            for _ in range(int(s.rng.poisson(p['rate']))):
                d = s.rand_day(span)
                a = s.amt(p['mu'], p['sigma'], lo=500)
                cust = s.pick(s.customers)
                ref = s.num('INV')
                s.post(d, 'INV', ref, [Dr('1100', a, f"Annual subscription {ref} - {cust}", cust), Cr('2400', a, f"Annual subscription {ref} - {cust}", cust)])
                s.receive(d, a, ref, cust, p)
                m = a // 12
                for k in range(12):
                    if i + k < 12:
                        e = s.spans[i + k][1]
                        mm = m if k < 11 else a - 11 * m
                        s.post(e, 'JE', s.num('JE'), [Dr('2400', mm, f"Revenue recognition {ref} ({k+1}/12)", cust), Cr('4200', mm, f"Revenue recognition {ref} ({k+1}/12)", cust)])

    def g_rents(s, p):
        units = [f"{n}{l}" for n in range(1, 5) for l in 'ABCD'][:p['units']]
        tenants = [f"{s.py.choice(FIRST)} {s.py.choice(LAST)}" for _ in units]
        rents = [int(s.amt(p['mu'], .15, rnd=25) / 100) * 100 for _ in units]
        for span in s.spans:
            for u, t, r in zip(units, tenants, rents):
                if s.rng.random() < .04:
                    continue
                d = span[0] + timedelta(days=int(s.rng.choice([0, 0, 0, 1, 1, 2, 3, 4, 6, 9])))
                s.post(d, 'DEP', s.num('RCPT'), [Dr('1000', r, f"Rent - Unit {u} - {t}", t), Cr('4150', r, f"Rent - Unit {u} - {t}", t)])
                if s.rng.random() < .05:
                    lf = 7500
                    s.post(d + timedelta(days=12), 'DEP', s.num('RCPT'), [Dr('1000', lf, f"Late fee - Unit {u}", t), Cr('4300', lf, f"Late fee - Unit {u}", t)])

    # ---------- derived (phase 2) ----------
    def x_card_pay(s, p):
        for span in s.spans[1:]:
            prev = (span[0] - timedelta(days=1))
            a = s.card.get((prev.year, prev.month), 0)
            if a:
                s.post(s.bizday(span[0] + timedelta(days=19)), 'BANK', s.num('ACH'),
                       [Dr('2100', a, 'Credit card payment', 'Card issuer'), Cr('1000', a, 'Credit card payment', 'Card issuer')])

    def _remit(s, store, done, first_flag_attr, opening, acct, d, desc, agent):
        keys = [k for k in store if k < (d.year, d.month) and k not in done]
        a = sum(store[k] for k in keys) + (opening if getattr(s, first_flag_attr) else 0)
        setattr(s, first_flag_attr, False)
        done.update(keys)
        if a > 0:
            s.post(d, 'BANK', s.num('ACH'), [Dr(acct, a, desc, agent), Cr('1000', a, desc, agent)])
        elif a < 0:
            s.post(d, 'BANK', s.num('ACH'), [Dr('1000', -a, desc + ' refund', agent), Cr(acct, -a, desc + ' refund', agent)])

    def x_ptax(s, p):
        for span in s.spans:
            d = s.bizday(span[0] + timedelta(days=14))
            s._remit(s.ptax, s.remitted_ptax, 'first_ptax', s.cfg.get('ptax0', 0) * 100, '2310', d, p['desc'], p['agent'])

    def x_tax(s, p):
        months = p.get('months')
        for span in s.spans:
            if months and span[0].month not in months:
                continue
            d = s.bizday(span[0] + timedelta(days=p.get('day', 19)))
            s._remit(s.tax, s.remitted_tax, 'first_tax', s.cfg.get('tax0', 0) * 100, '2300', d, p['desc'], p['agent'])

    def x_dep(s, p):
        m = s.cfg['fa0'] * 100 // 84
        for span in s.spans:
            s.post(span[1], 'JE', s.num('JE'), [Dr('6700', m, f"Depreciation {MON[span[1].month-1]} {span[1].year}", ''), Cr('1590', m, f"Depreciation {MON[span[1].month-1]} {span[1].year}", '')])

    def x_loan(s, p):
        bal = s.cfg['loan0'] * 100
        r = s.cfg['loan_rate'] / 12
        n = s.cfg['loan_n']
        pmt = int(bal * r / (1 - (1 + r) ** -n))
        for span in s.spans:
            d = s.bizday(span[0] + timedelta(days=p.get('day', 5) - 1))
            intr = int(bal * r); prin = min(bal, pmt - intr)
            bank = s.vend('bank')
            s.post(d, 'BANK', s.num('ACH'), [Dr('2600', prin, f"Loan payment - principal ({bank})", bank), Dr('7000', intr, f"Loan payment - interest ({bank})", bank),
                                             Cr('1000', prin + intr, f"Loan payment {bank}", bank)])
            bal -= prin

    def x_interest(s, p):
        for span in s.spans:
            a = s.amt(p['mu'], .3, lo=1)
            s.post(span[1], 'BANK', s.num('JE'), [Dr('1010', a, 'Interest earned', 'Bank'), Cr('4400', a, 'Interest earned', 'Bank')])

    def g_open_items(s):
        c = s.cfg
        for key, acct, nm, kind in (('ar0', '1100', 'receipt', 'AR'), ('ap0', '2000', 'payment', 'AP')):
            tot = c.get(key, 0) * 100
            if not tot:
                continue
            k = int(s.rng.integers(5, 10))
            cuts = sorted(s.rng.integers(1, tot, k - 1).tolist())
            parts = [b - a for a, b in zip([0] + cuts, cuts + [tot])]
            for part in parts:
                d = s.bizday(s.fy0 + timedelta(days=int(s.rng.integers(2, 60))))
                if kind == 'AR':
                    cust = s.pick(s.customers)
                    s.post(d, 'RCPT', s.num('RCPT'), [Dr('1000', part, f"Payment received - {cust} (prior year inv)", cust), Cr('1100', part, f"Payment received - {cust} (prior year inv)", cust)])
                else:
                    v = s.vend(c.get('ap_vend', 'office'))
                    s.post(d, 'BPAY', s.num('CHK'), [Dr('2000', part, f"Payment - {v} (prior year bill)", v), Cr('1000', part, f"Payment - {v} (prior year bill)", v)])

    # ---------- run ----------
    def run(s):
        phase2 = []
        for name, p in s.cfg['mix']:
            if name.startswith('x_'):
                phase2.append((name, p))
            else:
                getattr(s, 'g_' + name)(p)
        s.g_open_items()
        for name, p in phase2:
            getattr(s, name)(p)
        s.finalize()
        return s

    def finalize(s):
        c = s.cfg
        ents = sorted(s.ents, key=lambda e: (e['date'], e['seq']))
        bal, mins = defaultdict(int), defaultdict(int)
        for e in ents:
            for code, dr, cr, _, _ in e['lines']:
                bal[code] += dr - cr
                if code in ('1000', '1200'):
                    mins[code] = min(mins[code], bal[code])
        cash0 = -mins['1000'] + int(c.get('cash_buf', 20000) * 100)
        inv0 = -mins['1200'] + (int(c.get('inv_buf', 0) * 100) if c.get('has_inv') else 0)
        opening = [('1000', cash0, 0), ('1010', c.get('sav0', 0) * 100, 0), ('1100', c.get('ar0', 0) * 100, 0), ('1200', inv0, 0),
                   ('1500', c.get('fa0', 0) * 100, 0), ('1590', 0, c.get('accdep0', 0) * 100), ('1700', c.get('dep0', 0) * 100, 0),
                   ('2000', 0, c.get('ap0', 0) * 100), ('2300', 0, c.get('tax0', 0) * 100), ('2310', 0, c.get('ptax0', 0) * 100),
                   ('2600', 0, c.get('loan0', 0) * 100), ('3000', 0, c.get('cap0', 0) * 100)]
        opening = [o for o in opening if o[1] or o[2]]
        diff = sum(o[1] for o in opening) - sum(o[2] for o in opening)
        opening.append(('3100', max(-diff, 0), max(diff, 0)))
        lines = [(code, int(dr), int(cr), 'Opening balance', '') for code, dr, cr in opening]
        s.seq = 0
        s.ents.append(dict(date=s.fy0, src='OPEN', ref='OPENING', lines=lines, seq=-1))
        s.ents.sort(key=lambda e: (e['date'], e['seq']))

    def x_tips(s, p):
        s.g_tips_payout(p)
