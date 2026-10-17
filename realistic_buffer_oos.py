"""Out-of-sample check of the stop-buffer lever found on train (search_realistic_chase.py): every F1 config with buffer 0 / 0.5% / 1%
on validation 2016-20 and test 2021-25, scenario B (fee + 0.25%/side, touch fill). Paired comparison per config."""
from multiprocessing import Pool
import numpy as np, pandas as pd
import grid_search_timehunter as engine
import search_realistic_chase as R
def main():
    st,_=engine.load_data('stocks');R.G['fr']={str(k):f.reset_index(drop=True) for k,f in st.groupby('Ticker',sort=True)}
    cf=[c for c in R.CFG if c['fam']=='F1']+[c for c in R.CFG if c['fam']=='F2']
    with Pool(4) as p:rows=p.map(R.job,[(c,w,'B') for c in cf for w in ['validation','test']],chunksize=8)
    d=pd.DataFrame(rows);d.to_csv(R.OUT/'oos_B_all.csv',index=False)
    f1=d[d.fam=='F1'];keys=['channel','er_min','exit','failed','size_div','window']
    f1=f1.assign(er_min=f1.er_min.fillna(-1),failed=f1.failed.fillna(-1))
    for b in [.005,.01]:
        a=f1[f1.buffer==0].set_index(keys);c=f1[f1.buffer==b].set_index(keys);j=a[['cagr','records','mdd']].join(c[['cagr','records','mdd']],rsuffix='_b')
        for w,g in j.groupby(level='window'):
            print(f'buffer 0 -> {b} {w}: CAGR better {(g.cagr_b>g.cagr).mean():.2f} (median d {((g.cagr_b-g.cagr).median())*100:+.1f} pp), records better {(g.records_b>g.records).mean():.2f} (median d {(g.records_b-g.records).median():+.0f}), MDD median d {((g.mdd_b-g.mdd).median())*100:+.1f} pp')
    for w in ['validation','test']:
        g=d[d.window==w];print(w,'median CAGR by fam/buffer:',g.groupby(['fam','buffer'],dropna=False).cagr.median().round(3).to_dict())
if __name__=='__main__':main()
