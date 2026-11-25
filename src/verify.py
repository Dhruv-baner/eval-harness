import pandas as pd, csv, re
from openpyxl import load_workbook
from paths import DATA as D
t=pd.read_csv(f'{D}/truth/clean_ledger_all_clients.csv',dtype={'std_account_code':str},keep_default_na=False).set_index('line_id')
rm=pd.read_csv(f'{D}/truth/row_truth_map.csv',keep_default_na=False,dtype=str)
man=pd.read_csv(f'{D}/manifest.csv',keep_default_na=False)
AMTERR={'sign_flip','amount_digit_error','amount_format','credit_as_negative_debit','drcr_suffix','swapped_direction'}
def num(s,eu):
    s=str(s).strip()
    if s=='': return 0.0
    neg=s.startswith('(') or s.startswith('-')
    s=re.sub(r'[^\d,.]','',s); s=s.replace('.','').replace(',','.') if eu else s.replace(',','')
    return -float(s) if neg else float(s)
COLS={'qb':(6,7),'xero':(6,7),'euro':(5,6),'netsuite':(8,9)}
bad_tot=0; n_tot=0
for _,m in man.iterrows():
    fmt=m.export_layout; sub=rm[(rm.client_id==m.client_id)&(rm.row_kind=='data')]
    n=bad=0
    if fmt=='cashbook':
        wb=load_workbook(f"{D}/messy/{m.messy_file}",data_only=True)
        for _,r in sub.iterrows():
            if set(e.split(':')[0] for e in r.error_types.split(';') if e)&AMTERR: continue
            row=[c.value for c in wb[r.sheet][int(r.row_number)]]; tl=t.loc[r.line_id]
            v=row[4] if row[4] is not None else row[5]; n+=1
            bad+= not(isinstance(v,(int,float)) and abs(float(v)-(tl.debit or tl.credit))<0.006)
    else:
        rows=list(csv.reader(open(f"{D}/messy/{m.messy_file}",encoding='utf-8-sig')))
        for _,r in sub.iterrows():
            if set(e.split(':')[0] for e in r.error_types.split(';') if e)&AMTERR: continue
            row=rows[int(r.row_number)-1]; tl=t.loc[r.line_id]
            v=num(row[7],False) if fmt=='sage' else num(row[COLS[fmt][0]],fmt=='euro')-num(row[COLS[fmt][1]],fmt=='euro')
            n+=1; bad+= abs(v-(tl.debit-tl.credit))>0.006
    print(f'{m.client_id:24s} verified {n-bad}/{n}'); bad_tot+=bad; n_tot+=n
print('TOTAL verified',n_tot-bad_tot,'/',n_tot)
