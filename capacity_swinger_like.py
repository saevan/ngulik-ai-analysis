"""Capacity check: the same systems and Swinger with a buy-order cap of x * 20-day average traded value (Close*Volume, bars before
entry), x in {none, 25%, 10%, 5%}. Full 2000-2025, Rp1bn start, compounding. Without a cap every system (Swinger ideal included)
compounds to order sizes many times the stocks' daily traded value, which no account could execute."""
from multiprocessing import Pool
import numpy as np, pandas as pd
import grid_search_timehunter as engine
from backtest_stop_execution import run
from backtest_open_next import stats
from backtest_prototype_swinger import run_portfolio
from backtest_idx_costs import Costs
import search_swinger_like_system as S
from evaluate_swinger_like_finalists import FIN, PropCosts
COST={'fee':Costs(),'s25':PropCosts(slip=.0025)}
CAPS=[None,.25,.10,.05]
FR=S.FR
def job(a):
    kind,name,c,cap=a
    if kind=='sys':
        with np.errstate(invalid='ignore',divide='ignore'):eq,tr=run(FR,cost_model=COST[c],start='2000-01-01',liq_cap=cap,**S.kwargs(FIN[name]))
    else:
        eq,tr,_=run_portfolio(FR,name,slip=0. if c=='fee' else .0025,liq_cap=cap);name='SWINGER_'+name
    st=stats(eq,tr)
    return dict(system=name,cost=c,cap='none' if cap is None else f'{int(cap*100)}%',**st,final_equity=float(eq.equity.iloc[-1]))
def main():
    st,_=engine.load_data('stocks')
    for k,f in st.groupby('Ticker',sort=True):FR[str(k)]=f.reset_index(drop=True)
    tasks=[('sys',n,c,cap) for n in FIN for c in COST for cap in CAPS]+[('sw',m,c,cap) for m in ['afl_ideal','stop_order','next_open'] for c in COST for cap in CAPS]
    with Pool(4) as p:rows=p.map(job,tasks,chunksize=2)
    d=pd.DataFrame(rows);d.to_csv(S.OUT/'capacity.csv',index=False)
    d['v']=d.apply(lambda r:f"{r.cagr*100:.1f}/{int(r.records)}/{r.mdd*100:.0f}",axis=1)
    print(d.pivot_table(index='system',columns=['cost','cap'],values='v',aggfunc='first').to_string());print('done')
if __name__=='__main__':main()
