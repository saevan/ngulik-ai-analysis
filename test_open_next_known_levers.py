"""Known stable levers on Open(i+1)-compliant systems: mom120 ranking and gap-up skip (decided at the Open, filled at
the Open). Systems: (a) Breakout+ER20 next Open, fade2 + SMA30 exits (backtest_stop_execution next_open, regression to
fading_sma30 results) and (b) fresh HHV55 stop3/trail2.5 (backtest_open_next). No selection: every combination reported
on every window, judged by consistency."""
from pathlib import Path
from itertools import product
from multiprocessing import Pool
import numpy as np
import pandas as pd
import grid_search_timehunter as engine
from backtest_stop_execution import run as run_be
from backtest_open_next import run as run_hh, stats
from backtest_idx_costs import Costs
from exploit_market_properties import mom120, WINDOWS

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'new_system_exploit_results'
SCEN={'fees':Costs(),'spread1':Costs(grid=True,ticks_per_side=1,round_lot=100)}
FR={}

def job(a):
    sysn,rank,gap,w,s=a;fr={t:g for t,f in FR.items() if len(g:=f[f['Date/Time']<=WINDOWS[w][1]])}
    with np.errstate(invalid='ignore',divide='ignore'):
        if sysn=='breakout_er':
            c,t=run_be(fr,entry_mode='next_open',cost_model=SCEN[s],start=WINDOWS[w][0],priority=mom120 if rank else None,gap_skip=.02 if gap else None)
            t=t.rename(columns={})
        else:
            # mom120 at the signal bar: same formula as exploit_market_properties.mom120 but evaluated at index i (signal Close).
            pr=(lambda f:np.log(f.Close.shift(20)/f.Close.shift(140)).to_numpy(float)) if rank else None
            c,t=run_hh(fr,cost_model=SCEN[s],start=WINDOWS[w][0],priority=pr,gap_skip=.02 if gap else None)
    return dict(system=sysn,mom120=rank,gap_skip=gap,window=w,scenario=s,**stats(c,t))

def main():
    st,_=engine.load_data('stocks')
    for k,f in st.groupby('Ticker',sort=True):FR[str(k)]=f.reset_index(drop=True)
    tasks=[(sy,r,g,w,s) for sy in ['breakout_er','hhv55'] for r,g in product([False,True],[False,True]) for w in WINDOWS for s in SCEN]
    with Pool(4) as p:rows=p.map(job,tasks)
    d=pd.DataFrame(rows);d.to_csv(OUT/'open_next_known_levers.csv',index=False)
    d['cfg']=d.system+'/mom'+d.mom120.astype(int).astype(str)+'/gap'+d.gap_skip.astype(int).astype(str)
    d['v']=d.apply(lambda x:f'{x.cagr*100:.1f}/{x.records}/{x.mdd*100:.0f}',axis=1)
    pd.set_option('display.width',250)
    for s in SCEN:print(s);print(d[d.scenario==s].pivot_table(index='cfg',columns='window',values='v',aggfunc='first')[list(WINDOWS)].to_string())
    b=d[(~d.mom120)&(~d.gap_skip)].set_index(['system','window','scenario'])
    for lab,m in [('mom120',(d.mom120)&(~d.gap_skip)),('gap_skip',(~d.mom120)&(d.gap_skip)),('both',(d.mom120)&(d.gap_skip))]:
        x=d[m].set_index(['system','window','scenario']);dd=(x.cagr-b.cagr).unstack('window').round(3);rr=(x.records-b.records).unstack('window')
        print(lab,'CAGR delta');print(dd[list(WINDOWS)].to_string());print(lab,'records delta');print(rr[list(WINDOWS)].to_string())

if __name__=='__main__':main()
