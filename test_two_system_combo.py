"""User model: system 1 (trend) + system 2 (exact inverse of system 1's raw signals) only when market ER says choppy.

System 1: buy = Close > HHV20(previous) AND stock ER20 >= .3, entry only when market ER20 >= .3 at the signal Close;
          sell = Close < SMA30 OR (Open - Low) >= 2 ATR14(previous) on the current bar. Fills next tradable Open.
System 2: buy = system 1's raw sell signal (Close < SMA30 or fading 2 ATR), entry only when market ER20 < .3;
          sell = system 1's raw buy signal (Close > HHV20 and stock ER20 >= .3). Fills next tradable Open. Long only.
Shared: Rp1bn, 10 slots, 10% prior-close equity per entry capped by cash, compounding, system-1 entries first each day,
positions carried across regime changes (main spec). Variants address the stated goal (idle cash rotates without
blocking system 1): system 2 capped at 5 slots; system 2 also sells at the next Open when market ER turns >= .3;
system 2's sell also requiring market ER >= .3 (literal 'system 1 buy incl. market gate' interpretation).
Costs: fees buy .15% sell .25%; spread1 = fees + 1 tick each side + 100-share lot.
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
from analyze_portfolio_regimes import regime_proxy, attribute

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'two_system_combo_results'
WINDOWS={'train':('2000-01-01','2015-12-31'),'validation':('2016-01-01','2020-12-31'),'test':('2021-01-01','2025-08-15'),'full':('2000-01-01','2025-08-15')}
SCEN={'fees':Costs(),'spread1':Costs(grid=True,ticks_per_side=1,round_lot=100)}
VARIANTS=['system1_only','system2_only','combined','combined_s2_max5slots','combined_s2_exit_when_trend','combined_s2_sell_needs_market_er']
G={}

def job(a):
    v,w,s=a;proxy=G['proxy'];prev=proxy.er.shift(1)
    trend=set(proxy.index[prev>=.3]);choppy=set(proxy.index[prev<.3])
    fr={t:g.reset_index(drop=True) for t,f in G['frames'].items() if len(g:=f[f['Date/Time']<=WINDOWS[w][1]])}
    ie,ix=inverted_builders(('market',0),choppy)
    er_close=proxy.er
    if v=='combined_s2_exit_when_trend':
        ix2=lambda f:ix(f)|(f['Date/Time'].map(er_close)>=.3).fillna(False).to_numpy(bool)
    elif v=='combined_s2_sell_needs_market_er':
        ix2=lambda f:ix(f)&(f['Date/Time'].map(er_close)>=.3).fillna(False).to_numpy(bool)
    else:ix2=ix
    s1=lambda f:entry_signal(f,.3)&f['Date/Time'].isin(trend).to_numpy()&f.tradable.to_numpy(bool)
    sec=None
    if v!='system1_only':
        sec=dict(style='inverse',slots=5 if v=='combined_s2_max5slots' else 10,reserved=False,primary_first=True,allowed_dates=choppy,entry_builder=ie,exit_builder=ix2)
    builder=(lambda f:np.zeros(len(f),bool)) if v=='system2_only' else s1
    with np.errstate(invalid='ignore'):
        c,t,counts=portfolio(fr,threshold=.3,hold=None,fade=2,exit_sma=30,entry_builder=builder,secondary=sec,cost_model=SCEN[s],start=WINDOWS[w][0])
    m=c.new_high.groupby(c.index.to_period('M')).any()
    _,daily=attribute(c,proxy,'stocks',v)
    def ann(regs):
        g=daily[daily.regime.isin(regs)];return np.expm1(g.log_return.sum()*365.25/g.elapsed_days.sum())
    # Slots held by system 2 on trend days (capital not available to system 1 when it is active).
    lab=proxy.regime.reindex(c.index).fillna('unknown');trend_days=c.index[lab.isin(['uptrend','downtrend'])]
    s2=t[t.module=='range'];held=pd.Series(0.,index=c.index)
    for r in s2.itertuples():held.loc[r.entry_date:r.exit_date]+=1
    row=dict(variant=v,window=w,scenario=s,cagr=(c.equity.iloc[-1]/1e9)**(365.25/(c.index[-1]-c.index[0]).days)-1,records=int(m.sum()),
        months=len(m),mdd=c.drawdown.min(),n=len(t),invested=(c.market_value/c.equity).mean(),trend_annual=ann(['uptrend','downtrend']),
        choppy_annual=ann(['sideways']),s2_slots_on_trend_days=held.loc[trend_days].mean() if len(trend_days) else np.nan,**counts)
    for mod,g in t.groupby('module'):
        r=g.net_return;win=r>0
        row.update({f'{mod}_n':len(g),f'{mod}_wr':win.mean(),f'{mod}_avg_win':r[win].mean(),f'{mod}_avg_loss':-r[~win].mean(),
            f'{mod}_payout':r[win].mean()/-r[~win].mean(),f'{mod}_bars':g.bars.mean(),f'{mod}_pnl_share':g.pnl.sum()})
    if w=='full':c.to_csv(OUT/f'{w}_{s}_{v}_equity.csv');t.to_csv(OUT/f'{w}_{s}_{v}_trades.csv',index=False)
    return row

def main():
    OUT.mkdir(exist_ok=True)
    st,_=engine.load_data('stocks');G['proxy']=regime_proxy(st)
    G['frames']={str(k):f.reset_index(drop=True) for k,f in st.groupby('Ticker',sort=True)}
    (OUT/'PLAN.json').write_text(json.dumps(dict(doc=__doc__,variants=VARIANTS,windows=WINDOWS,selection='None: user-specified model; all variants reported.'),indent=2),encoding='utf-8')
    with Pool(4) as p:rows=p.map(job,[(v,w,s) for v in VARIANTS for w in WINDOWS for s in SCEN])
    d=pd.DataFrame(rows);d.to_csv(OUT/'comparison.csv',index=False)
    for s,old in [('fees','fees'),('spread1','spread')]:
        np.testing.assert_allclose(pd.read_csv(OUT/f'full_{s}_combined_equity.csv').equity,pd.read_csv(ROOT/'primary_inverse_switch_results'/f'{old}_combined_equity.csv').equity,rtol=1e-10)
        np.testing.assert_allclose(pd.read_csv(OUT/f'full_{s}_system1_only_equity.csv').equity,pd.read_csv(ROOT/'primary_inverse_switch_results'/f'{old}_primary_trend_only_equity.csv').equity,rtol=1e-10)
        np.testing.assert_allclose(pd.read_csv(OUT/f'full_{s}_system2_only_equity.csv').equity,pd.read_csv(ROOT/'primary_inverse_switch_results'/f'{old}_inverse_choppy_only_equity.csv').equity,rtol=1e-10)
    print('regression OK')
    d['v']=d.apply(lambda x:f'{x.cagr*100:.1f}% / {x.records}/{x.months} / {x.mdd*100:.0f}%',axis=1)
    pd.set_option('display.width',260)
    for s in SCEN:print(s);print(d[d.scenario==s].pivot_table(index='variant',columns='window',values='v',aggfunc='first').loc[VARIANTS,list(WINDOWS)].to_string())
    cols=['variant','scenario','invested','trend_annual','choppy_annual','s2_slots_on_trend_days','trend_n','trend_wr','trend_payout','trend_bars','range_n','range_wr','range_avg_win','range_avg_loss','range_payout','range_bars','range_pnl_share','trend_pnl_share']
    print(d[d.window=='full'][[c for c in cols if c in d]].round(4).to_string())

if __name__=='__main__':main()
