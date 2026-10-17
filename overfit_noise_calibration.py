"""Calibration of the price-noise test (overfit_tests_sk5.py T6): the same OHLC noise (x(1+N(0,0.25%)), 10 draws, same seeds) applied to
the strict HHV20 base system and to the Swinger ideal benchmark, plus SK-5 with 0.25% proportional slippage for comparison."""
from multiprocessing import Pool
import numpy as np, pandas as pd
import grid_search_timehunter as engine
from backtest_stop_execution import run
from backtest_prototype_swinger import run_portfolio
from backtest_open_next import stats
from backtest_idx_costs import Costs
import search_swinger_like_system as S
import overfit_tests_sk5 as O
def job(a):
    kind,d=a;fr=O.noisy_frames(d) if d is not None else O.G['all']
    if kind=='SWINGER_ideal':eq,tr,_=run_portfolio(fr,'afl_ideal')
    else:
        with np.errstate(invalid='ignore',divide='ignore'):eq,tr=run(fr,cost_model=Costs(),start='2000-01-01',**S.kwargs(S.BASE))
    s=stats(eq,tr);return dict(system=kind,draw=-1 if d is None else d,cagr=s['cagr'],records=s['records'],mdd=s['mdd'])
def main():
    st,_=engine.load_data('stocks');O.G['all']={str(k):f.reset_index(drop=True) for k,f in st.groupby('Ticker',sort=True)}
    tasks=[(k,d) for k in ['BASE_HHV20','SWINGER_ideal'] for d in [None]+list(range(10))]
    with Pool(4) as p:rows=p.map(job,tasks,chunksize=1)
    d=pd.DataFrame(rows);d.to_csv(O.OUT/'noise_calibration.csv',index=False)
    for k,g in d.groupby('system'):
        b=g[g.draw==-1].iloc[0];n=g[g.draw>=0]
        print(f'{k}: clean {b.cagr*100:.1f}%/{b.records:.0f}/{b.mdd*100:.0f} | noise median {n.cagr.median()*100:.1f}%/{n.records.median():.0f}/{n.mdd.median()*100:.0f} | change {(n.cagr.median()-b.cagr)*100:+.1f} pp ({(n.cagr.median()/b.cagr-1)*100:+.0f}%)')
if __name__=='__main__':main()
