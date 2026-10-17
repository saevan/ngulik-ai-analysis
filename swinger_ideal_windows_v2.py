"""Swinger ideal per window for scenarios A (fee) and B (fee + 0.25%/side), full universe and without the 20 tickers first listed in 2018 or later.
NOTE (audit 17 Oct 2026): windows are SLICES of one continuous run from 2000 (positions carried in), not fresh Rp1bn restarts; the rebasing
line is a no-op. Fresh-start values (auditor rerun, B): 2016-20 91.8%/45, 2021-25 65.7%/42, pre-2018 universe 2021-25 50.9%/39."""
import numpy as np, pandas as pd
import grid_search_timehunter as engine
from backtest_prototype_swinger import run_portfolio
from backtest_open_next import stats
W={'train':('2000-01-01','2015-12-31'),'validation':('2016-01-01','2020-12-31'),'test':('2021-01-01','2025-08-15'),'full':('2000-01-01','2025-08-15')}
st,_=engine.load_data('stocks');fr={str(k):f.reset_index(drop=True) for k,f in st.groupby('Ticker',sort=True)}
pre={t:f for t,f in fr.items() if f['Date/Time'].min()<pd.Timestamp('2018-01-01')}
rows=[]
for uni,src in [('all',fr),('pre2018',pre)]:
    for w,(a,b) in W.items():
        sub={t:g for t,f in src.items() if len(g:=f[(f['Date/Time']<=b)])}
        for scen,slip in [('A',0.),('B',.0025)]:
            eq,tr,_=run_portfolio(sub,'afl_ideal',slip=slip)
            eq=eq.loc[a:b];eq=eq.assign(equity=eq.equity/eq.equity.iloc[0]*1e9) if False else eq
            # run_portfolio always starts in 2000; re-run from window start by slicing and rebasing the equity path
            e=eq.equity/ (float(eq.equity.iloc[0]) if a=='2000-01-01' else float(eq.equity.iloc[0]))
            prev=eq.equity.iloc[0]
            yrs=(eq.index[-1]-eq.index[0]).days/365.25;cg=(eq.equity.iloc[-1]/eq.equity.iloc[0])**(1/yrs)-1
            pk=eq.equity.cummax();nh=eq.equity>pk.shift(1).fillna(eq.equity.iloc[0])
            rec=int(nh.groupby(eq.index.to_period('M')).any().sum())
            rows.append(dict(universe=uni,window=w,scen=scen,cagr=float(cg),records=rec,mdd=float((eq.equity/pk-1).min())))
d=pd.DataFrame(rows);d.to_csv('realistic_chase_v2_results/swinger_ideal_windows.csv',index=False)
d['v']=d.apply(lambda r:f"{r.cagr*100:.1f}/{int(r.records)}/{r.mdd*100:.0f}",axis=1)
print(d.pivot_table(index=['universe','scen'],columns='window',values='v',aggfunc='first').to_string())
