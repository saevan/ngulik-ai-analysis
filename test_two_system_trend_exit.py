"""System 2 sells when market ER says trend: immediate vs confirmed versions (user question follow-up).

Same model as test_two_system_combo.py (system 1 ER-gated HHV20 breakout; system 2 = exact inverse, entries only when
market ER20 < .3; shared 10 slots; next-Open fills). System 2 additionally sells at the next Open when, at a Close:
 trend1  : market ER20 >= .3 (immediate; = combined_s2_exit_when_trend)
 trend3  : market ER20 >= .3 on 3 consecutive Closes
 trend5  : market ER20 >= .3 on 5 consecutive Closes
 er040   : market ER20 >= .4 (buffer above the entry threshold)
 trend3_max5: trend3 with system 2 capped at 5 slots
Its normal sell (system 1 raw buy signal) stays active. Measured motivation: ER switches regime ~29x/year; 53% of
trend runs last <=3 days. Variants fixed before running; no selection, all windows/costs reported.
"""
from pathlib import Path
from multiprocessing import Pool
import json
import numpy as np
import pandas as pd
import grid_search_timehunter as engine
from backtest_breakout_er import entry_signal
from backtest_breakout_er_portfolio import portfolio
from backtest_choppy_inverted_signals import inverted_builders
from backtest_idx_costs import Costs
from analyze_portfolio_regimes import regime_proxy

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'two_system_combo_results'
WINDOWS={'train':('2000-01-01','2015-12-31'),'validation':('2016-01-01','2020-12-31'),'test':('2021-01-01','2025-08-15'),'full':('2000-01-01','2025-08-15')}
SCEN={'fees':Costs(),'spread1':Costs(grid=True,ticks_per_side=1,round_lot=100)}
VARIANTS={'trend1':(1,.3,10),'trend3':(3,.3,10),'trend5':(5,.3,10),'er040':(1,.4,10),'trend3_max5':(3,.3,5)}
G={}

def job(a):
    v,w,s=a;n,thr,cap=VARIANTS[v];proxy=G['proxy'];prev=proxy.er.shift(1)
    trend=set(proxy.index[prev>=.3]);choppy=set(proxy.index[prev<.3])
    confirmed=((proxy.er>=thr).astype(float).rolling(n).sum()==n)  # known at that Close
    fr={t:g.reset_index(drop=True) for t,f in G['frames'].items() if len(g:=f[f['Date/Time']<=WINDOWS[w][1]])}
    ie,ix=inverted_builders(('market',0),choppy)
    ix2=lambda f:ix(f)|f['Date/Time'].map(confirmed).fillna(False).to_numpy(bool)
    s1=lambda f:entry_signal(f,.3)&f['Date/Time'].isin(trend).to_numpy()&f.tradable.to_numpy(bool)
    sec=dict(style='inverse',slots=cap,reserved=False,primary_first=True,allowed_dates=choppy,entry_builder=ie,exit_builder=ix2)
    with np.errstate(invalid='ignore'):
        c,t,_=portfolio(fr,threshold=.3,hold=None,fade=2,exit_sma=30,entry_builder=s1,secondary=sec,cost_model=SCEN[s],start=WINDOWS[w][0])
    m=c.new_high.groupby(c.index.to_period('M')).any()
    row=dict(variant=v,window=w,scenario=s,cagr=(c.equity.iloc[-1]/1e9)**(365.25/(c.index[-1]-c.index[0]).days)-1,records=int(m.sum()),
        months=len(m),mdd=c.drawdown.min(),invested=(c.market_value/c.equity).mean())
    for mod,g in t.groupby('module'):
        r=g.net_return;win=r>0
        row.update({f'{mod}_n':len(g),f'{mod}_wr':win.mean(),f'{mod}_avg_win':r[win].mean(),f'{mod}_avg_loss':-r[~win].mean(),
            f'{mod}_payout':r[win].mean()/-r[~win].mean(),f'{mod}_mean':r.mean(),f'{mod}_bars':g.bars.mean()})
    if w=='full':c.to_csv(OUT/f'{w}_{s}_exit_{v}_equity.csv');t.to_csv(OUT/f'{w}_{s}_exit_{v}_trades.csv',index=False)
    return row

def main():
    st,_=engine.load_data('stocks');G['proxy']=regime_proxy(st)
    G['frames']={str(k):f.reset_index(drop=True) for k,f in st.groupby('Ticker',sort=True)}
    (OUT/'PLAN_trend_exit.json').write_text(json.dumps(dict(doc=__doc__,variants=VARIANTS),indent=2),encoding='utf-8')
    with Pool(4) as p:rows=p.map(job,[(v,w,s) for v in VARIANTS for w in WINDOWS for s in SCEN])
    d=pd.DataFrame(rows);d.to_csv(OUT/'comparison_trend_exit.csv',index=False)
    for s in SCEN:  # trend1 must equal the earlier combined_s2_exit_when_trend run
        np.testing.assert_allclose(pd.read_csv(OUT/f'full_{s}_exit_trend1_equity.csv').equity,pd.read_csv(OUT/f'full_{s}_combined_s2_exit_when_trend_equity.csv').equity,rtol=1e-10)
    print('regression OK')
    d['v']=d.apply(lambda x:f'{x.cagr*100:.1f}% / {x.records} / {x.mdd*100:.0f}%',axis=1)
    pd.set_option('display.width',260)
    for s in SCEN:print(s);print(d[d.scenario==s].pivot_table(index='variant',columns='window',values='v',aggfunc='first').loc[list(VARIANTS),list(WINDOWS)].to_string())
    print(d[d.window=='full'][['variant','scenario','invested','trend_n','range_n','range_wr','range_avg_win','range_avg_loss','range_payout','range_mean','range_bars']].round(4).to_string())

if __name__=='__main__':main()
