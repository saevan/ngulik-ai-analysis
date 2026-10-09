"""Primary and its exact raw signal inverse under complementary market gates."""
from pathlib import Path
import numpy as np
import pandas as pd
import grid_search_timehunter as engine
from backtest_breakout_er import entry_signal
from backtest_breakout_er_portfolio import portfolio
from backtest_choppy_inverted_signals import inverted_builders
from backtest_idx_costs import Costs
from analyze_portfolio_regimes import regime_proxy,attribute

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'primary_inverse_switch_results'

def main():
    OUT.mkdir(exist_ok=True)
    data,_=engine.load_data('stocks');proxy=regime_proxy(data)
    frames={str(k):f.reset_index(drop=True) for k,f in data.groupby('Ticker',sort=True)}
    previous=proxy.er.shift(1);trend=set(proxy.index[previous>=.3]);choppy=set(proxy.index[previous<.3])
    assert not trend.intersection(choppy)
    assert len(trend|choppy)==int(previous.notna().sum())
    inv_entry,inv_exit=inverted_builders(('market',0),choppy)
    primary=lambda f:entry_signal(f,.3)&f['Date/Time'].isin(trend).to_numpy()&f.tradable.to_numpy(bool)
    for f in frames.values():
        assert not (primary(f)&inv_entry(f)).any()
        cut=len(f)//2
        for builder in [primary,inv_entry,inv_exit]:np.testing.assert_array_equal(builder(f.iloc[:cut]),builder(f)[:cut])
    rows=[];mods=[]
    for scenario,cost in [('fees',Costs()),('spread',Costs(grid=True,ticks_per_side=1,round_lot=100))]:
        for mode in ['original_primary','primary_trend_only','inverse_choppy_only','combined']:
            sec=None
            if mode in ['inverse_choppy_only','combined']:
                sec=dict(style='inverse',slots=10,reserved=False,primary_first=True,allowed_dates=choppy,entry_builder=inv_entry,exit_builder=inv_exit)
            builder=None if mode=='original_primary' else (lambda f:np.zeros(len(f),bool)) if mode=='inverse_choppy_only' else primary
            c,t,counts=portfolio(frames,threshold=.3,hold=None,fade=2,exit_sma=30,entry_builder=builder,secondary=sec,cost_model=cost)
            if mode=='original_primary':
                old=pd.read_csv(ROOT/'fading_sma30_results'/f'breakout_ER_{scenario}_fade2_equity.csv');np.testing.assert_allclose(c.equity,old.equity,rtol=1e-10)
            if mode=='inverse_choppy_only':
                old=pd.read_csv(ROOT/'choppy_inverted_signal_results'/f'full_{scenario}_market_0_equity.csv');np.testing.assert_allclose(c.equity,old.equity,rtol=1e-10)
            if mode!='original_primary':
                assert t.loc[t.module=='trend','entry_date'].isin(trend).all()
                assert t.loc[t.module=='range','entry_date'].isin(choppy).all()
            stats,_=attribute(c,proxy,'stocks',mode);side=stats[stats.regime=='sideways'].iloc[0]
            month=c.new_high.groupby(c.index.to_period('M')).any()
            row=dict(scenario=scenario,mode=mode,cagr=(c.equity.iloc[-1]/1e9)**(365.25/(c.index[-1]-c.index[0]).days)-1,
                mdd=c.drawdown.min(),n=len(t),wr=(t.net_return>0).mean(),records=int(month.sum()),months=len(month),
                sideways_annual=side.conditional_annualized,sideways_records=side.months_record,sideways_months=side.months_present,**counts)
            rows.append(row)
            for module,g in t.groupby('module'):
                r=g.net_return
                mods.append(dict(scenario=scenario,mode=mode,module=module,n=len(g),wr=(r>0).mean(),avg_win=r[r>0].mean(),avg_loss=-r[r<0].mean(),mean_bars=g.bars.mean()))
            label=f'{scenario}_{mode}';c.to_csv(OUT/f'{label}_equity.csv');t.to_csv(OUT/f'{label}_trades.csv',index=False)
            pd.DataFrame(rows).to_csv(OUT/'comparison.csv',index=False);pd.DataFrame(mods).to_csv(OUT/'modules.csv',index=False)
            print(label,row,flush=True)

if __name__=='__main__':main()
