"""New system (HHV55 + stop 3 ATR + trailing 2.5 ATR after +2 ATR) vs Swinger ideal when market ER20 says choppy."""
from pathlib import Path
import numpy as np
import pandas as pd
import new_system_search as ns
import new_system_stage2 as s2
import grid_search_timehunter as engine
from analyze_portfolio_regimes import regime_proxy

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'new_system_choppy_results'
CFG=dict(entry='brk55|none',stop=3.,time=0,act=2.,trail=2.5,maxhold=0)
PERIODS={'2000-2015':('2000-01-01','2015-12-31'),'2016-2020':('2016-01-01','2020-12-31'),'2021-2025':('2021-01-01','2025-12-31'),'2000-2025':('2000-01-01','2025-12-31')}

def stats(r,b):
    w=r>0;out=dict(n=len(r),mean=r.mean(),median=np.median(r),wr=w.mean(),avg_win=r[w].mean(),avg_loss=-r[~w].mean(),
        win_bars=b[w].mean(),loss_bars=b[~w].mean(),pf=r[w].sum()/-r[~w].sum());out['payout']=out['avg_win']/out['avg_loss']
    out['c1']=bool(out['mean']>0 and out['mean']>=2*out['median'] and out['mean']-out['median']>=.01);out['c2']=bool(out['win_bars']>out['loss_bars'])
    out['c3']=bool(out['payout']>2);out['c4']=bool(out['wr']>.5);out['c5']=bool(out['mean']>0 and out['pf']>1);out['passes']=sum(out[k] for k in ['c1','c2','c3','c4','c5'])
    return out

def main():
    OUT.mkdir(exist_ok=True)
    st,_=engine.load_data('stocks');reg=regime_proxy(st).regime
    xs=[ns.features(f.reset_index(drop=True)) for _,f in st.groupby('Ticker',sort=True)]
    tr=[]
    for x in xs:tr+=ns.simulate(x,s2.entry2(x,CFG['entry']),CFG,ns.COST['stocks'],np.datetime64('2000-01-01'),np.datetime64('2025-12-31'))
    a=pd.DataFrame(tr,columns=['ret','bars','entry_date']);a['entry_date']=pd.to_datetime(a.entry_date);a['system']='Sistem baru HHV55'
    sw=pd.read_csv(ROOT/'prototype_swinger_benchmark_results'/'afl_ideal_net_trades.csv',parse_dates=['entry_date'])
    b=pd.DataFrame(dict(ret=sw.net_return,bars=sw.bars,entry_date=sw.entry_date,system='Swinger ideal'))
    t=pd.concat([a,b],ignore_index=True)
    t['regime']=t.entry_date.map(reg).fillna('unknown');t['state']=np.where(t.regime=='sideways','choppy',np.where(t.regime=='unknown','unknown','trend'))
    t.to_csv(OUT/'trades.csv',index=False)
    rows=[]
    for (sysn,state),g in t[t.state!='unknown'].groupby(['system','state']):
        for per,(s,e) in PERIODS.items():
            h=g[(g.entry_date>=s)&(g.entry_date<=e)]
            if len(h)>=20:rows.append(dict(system=sysn,state=state,period=per,**stats(h.ret.to_numpy(),h.bars.to_numpy())))
    r=pd.DataFrame(rows);r.to_csv(OUT/'comparison.csv',index=False)
    pd.set_option('display.width',250)
    print(r[['system','state','period','n','mean','median','wr','avg_win','avg_loss','payout','win_bars','loss_bars','pf','passes']].round(4).to_string())

if __name__=='__main__':main()
