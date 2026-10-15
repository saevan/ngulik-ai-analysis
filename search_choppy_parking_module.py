"""Choppy-period module so capital is not idle while system 1 (ER-gated breakout) is filtered out.

System 1: Close > HHV20 and stock ER20 >= .3, entries only when market ER20 >= .3; exits SMA30 / fading 2 ATR.
Choppy module candidates (entries only when market ER20 < .3, next-Open fills, defined in choppy_modules.py):
 rs_breakout (stock trending on its own in a choppy market), momentum_parking (top-decile 120d momentum above SMA50),
 lowvol_uptrend. Each with preemption on/off (preemption: system 1 candidates take slots from the weakest choppy-module
 positions, sold at the next Open). Earlier failed families (RSI2/support/Bollinger mean reversion, range escape,
 inverse) are not repeated.
Selection: train 2000-2015, spread1: CAGR > system1-only AND records >= system1-only; max CAGR. Frozen; all reported.
"""
from pathlib import Path
from multiprocessing import Pool
import json
import numpy as np
import pandas as pd
from analyze_portfolio_regimes import regime_proxy, attribute
from backtest_idx_costs import Costs
from backtest_two_module import run
import choppy_modules as cm
from test_two_module_regression import setup

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'choppy_module_results'
WINDOWS={'train':('2000-01-01','2015-12-31'),'validation':('2016-01-01','2020-12-31'),'test':('2021-01-01','2025-08-15'),'full':('2000-01-01','2025-08-15')}
SCEN={'fees':Costs(),'spread1':Costs(grid=True,ticks_per_side=1,round_lot=100)}
MODS={'none':None,'rs_er0.5_hhv20':lambda:cm.rs_breakout(.5,20),'rs_er0.3_hhv20':lambda:cm.rs_breakout(.3,20),'rs_er0.3_hhv55':lambda:cm.rs_breakout(.3,55),
    'mom_top10_t20':lambda:cm.momentum_parking(.9,20),'mom_top10_trend':lambda:cm.momentum_parking(.9,0),'lowvol_r0.3':lambda:cm.lowvol_uptrend(.3)}
CONFIGS=[('none',False)]+[(m,p) for m in list(MODS)[1:] for p in (True,False)]
G={}

def job(a):
    (mod,pre),w,s=a
    fr={t:g.reset_index(drop=True) for t,f in G['frames'].items() if len(g:=f[f['Date/Time']<=WINDOWS[w][1]])}
    mods=[cm.system1()]+([MODS[mod]()] if mod!='none' else [])
    with np.errstate(invalid='ignore',divide='ignore'):c,t,rej=run(fr,mods,cost_model=SCEN[s],start=WINDOWS[w][0],preempt=pre)
    m=c.new_high.groupby(c.index.to_period('M')).any()
    _,daily=attribute(c,G['proxy'],'stocks',mod)
    def ann(regs):
        g=daily[daily.regime.isin(regs)];return np.expm1(g.log_return.sum()*365.25/g.elapsed_days.sum())
    lab=G['proxy'].regime.reindex(c.index).fillna('unknown');inv=c.market_value/c.equity
    row=dict(module=mod,preempt=pre,window=w,scenario=s,cagr=(c.equity.iloc[-1]/1e9)**(365.25/(c.index[-1]-c.index[0]).days)-1,
        records=int(m.sum()),months=len(m),mdd=c.drawdown.min(),invested=inv.mean(),invested_choppy=inv[lab=='sideways'].mean(),
        invested_trend=inv[lab.isin(['uptrend','downtrend'])].mean(),trend_annual=ann(['uptrend','downtrend']),choppy_annual=ann(['sideways']),
        preempted=int((t.reason=='preempted').sum()) if len(t) else 0,**{f'rej_{k}':v for k,v in rej.items()})
    for name,g in t.groupby('module'):
        k='s1' if name=='system1' else 'm2';r=g.net_return;win=r>0
        row.update({f'{k}_n':len(g),f'{k}_wr':win.mean(),f'{k}_avg_win':r[win].mean(),f'{k}_avg_loss':-r[~win].mean(),
            f'{k}_payout':r[win].mean()/-r[~win].mean(),f'{k}_mean':r.mean(),f'{k}_bars':g.bars.mean(),f'{k}_pnl':g.pnl.sum()})
    if w=='full':
        lab_=f"{mod}_p{int(pre) if isinstance(pre,bool) else pre}{G.get('suffix','')}";c.to_csv(OUT/f'full_{s}_{lab_}_equity.csv');t.to_csv(OUT/f'full_{s}_{lab_}_trades.csv',index=False)
    return row

def main():
    OUT.mkdir(exist_ok=True)
    G['frames']=setup();import grid_search_timehunter as engine
    st,_=engine.load_data('stocks');G['proxy']=regime_proxy(st)
    # Causality of every module signal: prefix of history gives the same arrays.
    for name,fn in list(MODS.items())[1:]+[('system1',cm.system1)]:
        mod=fn()
        for f in list(G['frames'].values())[::13]:
            cut=len(f)//2;a=mod['prepare'](f);b=mod['prepare'](f.iloc[:cut])
            for k,v in b.items():np.testing.assert_array_equal(np.asarray(a[k])[:cut],np.asarray(v))
    (OUT/'PLAN.json').write_text(json.dumps(dict(doc=__doc__,configs=[list(c) for c in CONFIGS],windows=WINDOWS),indent=2),encoding='utf-8')
    with Pool(4) as p:
        train=p.map(job,[(c,'train','spread1') for c in CONFIGS])
        tr=pd.DataFrame(train);b=tr.iloc[0]
        ok=tr[(tr.cagr>b.cagr)&(tr.records>=b.records)].sort_values(['cagr','records'],ascending=False)
        chosen=None if ok.empty else dict(module=ok.iloc[0].module,preempt=bool(ok.iloc[0].preempt))
        (OUT/'FROZEN.json').write_text(json.dumps(dict(chosen=chosen,base_train=dict(cagr=b.cagr,records=int(b.records))),indent=2),encoding='utf-8')
        print('FROZEN',chosen,flush=True)
        rest=p.map(job,[(c,w,s) for c in CONFIGS for w in WINDOWS for s in SCEN if (w,s)!=('train','spread1')])
    d=pd.DataFrame(train+rest);d.to_csv(OUT/'comparison.csv',index=False)
    for s in SCEN:
        np.testing.assert_allclose(pd.read_csv(OUT/f'full_{s}_none_p0_equity.csv').equity,pd.read_csv(ROOT/'er_gated_breakout_results'/f'full_{s}_stock_and_market_er_equity.csv').equity,rtol=1e-10)
    print('regression OK')
    d['cfg']=d.module+'/pre'+d.preempt.astype(int).astype(str)
    d['v']=d.apply(lambda x:f'{x.cagr*100:.1f}% / {x.records} / {x.mdd*100:.0f}%',axis=1)
    pd.set_option('display.width',260)
    order=[f'{m}/pre{int(p)}' for m,p in CONFIGS]
    for s in SCEN:print(s);print(d[d.scenario==s].pivot_table(index='cfg',columns='window',values='v',aggfunc='first').loc[order,list(WINDOWS)].to_string())
    cols=['cfg','scenario','invested_choppy','invested_trend','choppy_annual','trend_annual','preempted','s1_n','m2_n','m2_wr','m2_avg_win','m2_avg_loss','m2_payout','m2_mean','m2_bars']
    print(d[d.window=='full'][[c for c in cols if c in d]].round(4).to_string())

if __name__=='__main__':main()
