"""Independent-audit check (17 Oct 2026): effect of letting buy stops fill when the High only TOUCHES the level (High == level).
SK-5, CAND (ER .2 + trail), the strict HHV20 base; full 2000-2025 and the three windows; fee and s25; plus the 25% ADV cap."""
from multiprocessing import Pool
import numpy as np, pandas as pd
import grid_search_timehunter as engine
from backtest_stop_execution import run
from backtest_open_next import stats
from backtest_idx_costs import Costs
import search_swinger_like_system as S
from evaluate_swinger_like_finalists import PropCosts
W={'train':('2000-01-01','2015-12-31'),'validation':('2016-01-01','2020-12-31'),'test':('2021-01-01','2025-08-15'),'full':('2000-01-01','2025-08-15')}
SYS={'SK5':S.kwargs(dict(channel=5,er_min=.3,exit='cand',failed=0.,size_div=5)),'CAND':S.kwargs(dict(channel=5,er_min=.2,exit='cand_trail2',failed=0.,size_div=5)),
     'BASE_HHV20':S.kwargs(S.BASE),'HHV10_prereg':S.kwargs(dict(channel=10,er_min=.3,exit='cand',failed=0.,size_div=5))}
G={}
def job(a):
    name,touch,w,cost,cap=a;fr={t:g for t,f in G['fr'].items() if len(g:=f[f['Date/Time']<=W[w][1]])}
    kw=dict(SYS[name],touch_fill=touch);
    if cap:kw['liq_cap']=cap
    with np.errstate(invalid='ignore',divide='ignore'):eq,tr=run(fr,cost_model=Costs() if cost=='fee' else PropCosts(slip=.0025),start=W[w][0],**kw)
    s=stats(eq,tr);return dict(system=name,touch_fill=touch,window=w,cost=cost,cap=cap or 0,cagr=s['cagr'],records=s['records'],mdd=s['mdd'],n=s['n'],wr=s['wr'])
def main():
    st,_=engine.load_data('stocks');G['fr']={str(k):f.reset_index(drop=True) for k,f in st.groupby('Ticker',sort=True)}
    tasks=[(n,t,w,c,None) for n in SYS for t in [False,True] for w in W for c in ['fee','s25']]+[(n,t,'full','fee',.25) for n in SYS for t in [False,True]]
    with Pool(4) as p:rows=p.map(job,tasks,chunksize=2)
    d=pd.DataFrame(rows);d.to_csv('overfit_results/touch_fill_check.csv',index=False)
    d['v']=d.apply(lambda r:f"{r.cagr*100:.1f}/{int(r.records)}/{r.mdd*100:.0f}",axis=1)
    pd.set_option('display.width',260,'display.max_columns',30)
    print(d[d.cap==0].pivot_table(index=['system','touch_fill'],columns=['cost','window'],values='v',aggfunc='first').to_string())
    print(d[d.cap>0].pivot_table(index='system',columns='touch_fill',values='v',aggfunc='first').to_string());print('done')
if __name__=='__main__':main()
