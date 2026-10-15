"""User model: trend module = HHV breakout allowed only when ER says the market is not choppy.

Entry: Close > HHV20 of the previous 20 Highs (signal at Close i), filled at the next tradable Open.
ER filters (threshold 0.3): stock ER20 of the stock itself and/or market ER20 of the equal-weight 100-stock proxy
(analyze_portfolio_regimes.regime_proxy; not IHSG), both known at the signal Close.
Exits (research primary): Close < SMA30 or Open - Low >= 2 * ATR14(previous) of the CURRENT bar; next tradable Open.
No holding cap. Positions opened in trend are NOT force-closed when the market turns choppy (main spec); a sensitivity
adds 'exit at next Open when market ER < 0.3'.
Portfolio: Rp1bn, 10 shared slots, 10% prior-close equity per entry capped by cash, compounding, long only,
alphabetical priority. Costs: fees buy .15% sell .25%; spread1 = fees + 1 tick each side + 100-share lots.
"""
from pathlib import Path
from multiprocessing import Pool
import json
import numpy as np
import pandas as pd
import grid_search_timehunter as engine
from backtest_breakout_er import entry_signal
from backtest_breakout_er_portfolio import portfolio
from backtest_idx_costs import Costs
from analyze_portfolio_regimes import regime_proxy, attribute

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'er_gated_breakout_results'
WINDOWS={'train':('2000-01-01','2015-12-31'),'validation':('2016-01-01','2020-12-31'),'test':('2021-01-01','2025-08-15'),'full':('2000-01-01','2025-08-15')}
SCEN={'fees':Costs(),'spread1':Costs(grid=True,ticks_per_side=1,round_lot=100)}
VARIANTS=[dict(name='no_er',stock_er=None,market_er=None,exit_choppy=False),
    dict(name='stock_er',stock_er=.3,market_er=None,exit_choppy=False),
    dict(name='market_er',stock_er=None,market_er=.3,exit_choppy=False),
    dict(name='stock_and_market_er',stock_er=.3,market_er=.3,exit_choppy=False),
    dict(name='stock_and_market_er+exit_choppy',stock_er=.3,market_er=.3,exit_choppy=True),
    dict(name='market_er+exit_choppy',stock_er=None,market_er=.3,exit_choppy=True),
    dict(name='stock_and_market_er_0.2',stock_er=.3,market_er=.2,exit_choppy=False),
    dict(name='stock_and_market_er_0.4',stock_er=.3,market_er=.4,exit_choppy=False)]
G={}

def builders(v):
    er=G['proxy'].er
    entry=None
    if v['market_er'] is not None:
        allowed=set(er.index[er.shift(1)>=v['market_er']])  # entry day label = market ER at the signal Close
        entry=lambda f:entry_signal(f,v['stock_er'])&f['Date/Time'].isin(allowed).to_numpy()&f.tradable.to_numpy(bool)
    elif v['stock_er'] is None:
        entry=lambda f:entry_signal(f,None)
    exit_b=None
    if v['exit_choppy']:
        exit_b=lambda f:(f['Date/Time'].map(er)<v['market_er']).fillna(False).to_numpy(bool)  # known at that Close
    return entry,exit_b

def job(a):
    v,w,s=a;entry,exit_b=builders(v)
    fr={t:g.reset_index(drop=True) for t,f in G['frames'].items() if len(g:=f[f['Date/Time']<=WINDOWS[w][1]])}
    with np.errstate(invalid='ignore'):
        c,t,counts=portfolio(fr,threshold=.3 if v['stock_er'] is not None else None,hold=None,fade=2,exit_sma=30,entry_builder=entry,
            exit_builder=exit_b,cost_model=SCEN[s],start=WINDOWS[w][0])
    m=c.new_high.groupby(c.index.to_period('M')).any();r=t.net_return;win=r>0
    _,daily=attribute(c,G['proxy'],'stocks',v['name'])
    def ann(regs):
        g=daily[daily.regime.isin(regs)];return np.expm1(g.log_return.sum()*365.25/g.elapsed_days.sum())
    row=dict(variant=v['name'],window=w,scenario=s,cagr=(c.equity.iloc[-1]/1e9)**(365.25/(c.index[-1]-c.index[0]).days)-1,
        records=int(m.sum()),months=len(m),mdd=c.drawdown.min(),n=len(t),wr=win.mean(),avg_win=r[win].mean(),avg_loss=-r[~win].mean(),
        payout=r[win].mean()/-r[~win].mean(),mean_bars=t.bars.mean(),invested=(c.market_value/c.equity).mean(),
        trend_annual=ann(['uptrend','downtrend']),choppy_annual=ann(['sideways']),final_equity=c.equity.iloc[-1],**counts)
    if w=='full':c.to_csv(OUT/f'{w}_{s}_{v["name"]}_equity.csv');t.to_csv(OUT/f'{w}_{s}_{v["name"]}_trades.csv',index=False)
    return row

def main():
    OUT.mkdir(exist_ok=True)
    st,_=engine.load_data('stocks');G['proxy']=regime_proxy(st)
    G['frames']={str(k):f.reset_index(drop=True) for k,f in st.groupby('Ticker',sort=True)}
    (OUT/'PLAN.json').write_text(json.dumps(dict(doc=__doc__,variants=VARIANTS,windows=WINDOWS,selection='None: user-specified model; all variants reported.'),indent=2),encoding='utf-8')
    with Pool(4) as p:rows=p.map(job,[(v,w,s) for v in VARIANTS for w in WINDOWS for s in SCEN])
    d=pd.DataFrame(rows);d.to_csv(OUT/'comparison.csv',index=False)
    # Regression to earlier published curves.
    np.testing.assert_allclose(pd.read_csv(OUT/'full_fees_stock_er_equity.csv').equity,pd.read_csv(ROOT/'fading_sma30_results'/'breakout_ER_fees_fade2_equity.csv').equity,rtol=1e-10)
    np.testing.assert_allclose(pd.read_csv(OUT/'full_spread1_stock_er_equity.csv').equity,pd.read_csv(ROOT/'fading_sma30_results'/'breakout_ER_spread_fade2_equity.csv').equity,rtol=1e-10)
    np.testing.assert_allclose(pd.read_csv(OUT/'full_fees_stock_and_market_er_equity.csv').equity,pd.read_csv(ROOT/'primary_inverse_switch_results'/'fees_primary_trend_only_equity.csv').equity,rtol=1e-10)
    np.testing.assert_allclose(pd.read_csv(OUT/'full_spread1_stock_and_market_er_equity.csv').equity,pd.read_csv(ROOT/'primary_inverse_switch_results'/'spread_primary_trend_only_equity.csv').equity,rtol=1e-10)
    print('regression OK')
    d['v']=d.apply(lambda x:f'{x.cagr*100:.1f}% / {x.records}/{x.months} / {x.mdd*100:.0f}%',axis=1)
    pd.set_option('display.width',250)
    for s in SCEN:print(s);print(d[d.scenario==s].pivot_table(index='variant',columns='window',values='v',aggfunc='first')[list(WINDOWS)].to_string())
    print(d[d.window=='full'][['variant','scenario','n','wr','avg_win','avg_loss','payout','mean_bars','invested','trend_annual','choppy_annual']].round(4).to_string())

if __name__=='__main__':main()
