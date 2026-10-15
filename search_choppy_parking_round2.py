"""Round 2 (fixed before running): capacity mechanisms for the best round-1 family, rs_breakout ER>=0.5 HHV20.
Round 1 showed the module itself is profitable (fees and spread) but crowds out system 1 (1528 -> 1200 trades) and that
taking slots from its weakest positions destroys its winners. Variants: cap 5 / 10 x preemption none / losers-only.
Selection: train 2000-2015 spread1, CAGR > system1-only AND records >= system1-only. Family choice used round-1 results
of all windows, so validation/test are not clean for the family choice."""
from pathlib import Path
from multiprocessing import Pool
import json
import numpy as np
import pandas as pd
import search_choppy_parking_module as r1
import choppy_modules as cm
from analyze_portfolio_regimes import regime_proxy

OUT=r1.OUT
CONFIGS=[('none',10,False),('rs_er0.5_hhv20',10,False),('rs_er0.5_hhv20',5,False),('rs_er0.5_hhv20',10,'losers'),('rs_er0.5_hhv20',5,'losers')]

def job(a):
    (mod,cap,pre),w,s=a
    r1.MODS['rs_er0.5_hhv20']=lambda:cm.rs_breakout(.5,20,cap=cap);r1.G['suffix']=f'_cap{cap}' if mod!='none' else ''
    row=r1.job(((mod,pre),w,s));row.update(cap=cap,preempt=str(pre));return row

def main():
    r1.G['frames']=r1.setup();import grid_search_timehunter as engine
    st,_=engine.load_data('stocks');r1.G['proxy']=regime_proxy(st)
    with Pool(4) as p:rows=p.map(job,[(c,w,s) for c in CONFIGS for w in r1.WINDOWS for s in r1.SCEN])
    d=pd.DataFrame(rows);d.to_csv(OUT/'comparison_round2.csv',index=False)
    tr=d[(d.window=='train')&(d.scenario=='spread1')];b=tr[tr.module=='none'].iloc[0]
    ok=tr[(tr.cagr>b.cagr)&(tr.records>=b.records)].sort_values('cagr',ascending=False)
    chosen=None if ok.empty else dict(module=ok.iloc[0].module,cap=int(ok.iloc[0].cap),preempt=ok.iloc[0].preempt)
    (OUT/'FROZEN_round2.json').write_text(json.dumps(dict(chosen=chosen),indent=2),encoding='utf-8');print('FROZEN',chosen)
    d['cfg']=d.module+'/cap'+d.cap.astype(str)+'/pre_'+d.preempt
    d['v']=d.apply(lambda x:f'{x.cagr*100:.1f}% / {x.records} / {x.mdd*100:.0f}%',axis=1)
    pd.set_option('display.width',260)
    for s in r1.SCEN:print(s);print(d[d.scenario==s].pivot_table(index='cfg',columns='window',values='v',aggfunc='first')[list(r1.WINDOWS)].to_string())
    print(d[d.window=='full'][['cfg','scenario','invested_choppy','choppy_annual','trend_annual','preempted','s1_n','m2_n','m2_wr','m2_payout','m2_mean','m2_bars']].round(4).to_string())

if __name__=='__main__':main()
