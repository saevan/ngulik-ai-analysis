"""Compare H200 to no-cap SMA30 exit for two explicitly separate entries."""
from pathlib import Path
import numpy as np
import pandas as pd
import grid_search_timehunter as engine
from backtest_timehunter_atr import atr_previous
from backtest_breakout_er_portfolio import portfolio
from backtest_idx_costs import Costs
from analyze_portfolio_regimes import regime_proxy, attribute

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'sma30_exit_results'


def pullback_entry(f):
    a=atr_previous(f)
    setup=(a>0)&(f.Close>f.Close.rolling(30).mean())&(f.Close>f.Close.shift(1))&((f.High.rolling(10).max()-f.Close)>=.25*a)
    return setup.shift(1,fill_value=False).to_numpy(bool)


def main():
    OUT.mkdir(exist_ok=True)
    data,_=engine.load_data('stocks')
    frames={str(k):f.reset_index(drop=True) for k,f in data.groupby('Ticker',sort=True)}
    for f in frames.values():
        cut=len(f)//2
        np.testing.assert_array_equal(pullback_entry(f.iloc[:cut]),pullback_entry(f)[:cut])
    proxy=regime_proxy(data);rows=[];regimes=[]
    for entry,builder in [('breakout_ER',None),('AFL_pullback',pullback_entry)]:
        for scenario,cost in [('fees',Costs()),('spread',Costs(grid=True,ticks_per_side=1,round_lot=100))]:
            for reverse in [False,True]:
                for exit_type in ['H200','SMA30']:
                    label=f'{entry}_{scenario}_{exit_type}_reverse{reverse}'
                    curve,trades,counts=portfolio(frames,hold=200 if exit_type=='H200' else None,
                        exit_sma=30 if exit_type=='SMA30' else None,entry_builder=builder,cost_model=cost,reverse=reverse)
                    if entry=='breakout_ER' and exit_type=='H200' and not reverse:
                        name='fees_only' if scenario=='fees' else 'fees_1tick_each_side'
                        old=pd.read_csv(ROOT/'breakout_er_idx_cost_results'/f'{name}_equity.csv')
                        np.testing.assert_allclose(curve.equity,old.equity,rtol=1e-10)
                    if exit_type=='SMA30':assert not trades.reason.str.startswith('time').any()
                    r=trades.net_return;years=(curve.index[-1]-curve.index[0]).days/365.25
                    row=dict(variant=label,entry=entry,scenario=scenario,exit=exit_type,reverse=reverse,
                        cagr=(curve.equity.iloc[-1]/1e9)**(1/years)-1,mdd=curve.drawdown.min(),
                        records=int(curve.new_high.groupby(curve.index.to_period('M')).any().sum()),
                        trades=len(trades),wr=(r>0).mean(),payout=r[r>0].mean()/-r[r<0].mean(),
                        money_pf=trades.loc[trades.pnl>0,'pnl'].sum()/-trades.loc[trades.pnl<0,'pnl'].sum(),
                        mean_bars=trades.bars.mean(),cash_fraction=(curve.cash/curve.equity).mean(),
                        sma_exits=int((trades.reason=='sma_exit').sum()),fade_exits=int((trades.reason=='fading').sum()),**counts)
                    stats,_=attribute(curve,proxy,'stocks',label);regimes.append(stats)
                    side=stats[stats.regime=='sideways'].iloc[0]
                    row['sideways_annual_equivalent']=side.conditional_annualized
                    row['sideways_records']=side.months_record
                    rows.append(row)
                    curve.to_csv(OUT/f'{label}_equity.csv');trades.to_csv(OUT/f'{label}_trades.csv',index=False)
                    pd.DataFrame(rows).to_csv(OUT/'comparison.csv',index=False)
                    print(label,f'CAGR {row["cagr"]:.2%}, records {row["records"]}/308, trades {len(trades)}',flush=True)
    pd.concat(regimes).to_csv(OUT/'regimes.csv',index=False)
    lines=['# SMA30 exit backtest','',
        'Two separate entries: (1) prior-HHV20 breakout and ER20>=0.30, (2) active AFL default setup: Close>SMA30, Close>previousClose, HHV High10 including signal bar minus Close>=0.25 prior ATR14. Both entry signals use completed bars, next tradable Open execution. This is a Python portfolio replication of AFL default signals, not native AmiBroker execution or its fixed-notional test harness.', '',
        'Exit comparison: original H200 Close plus fade5 previous ATR14 versus NO holding cap and completed Close<SMA30 followed by next tradable Open. Equality does not trigger. Uses level condition, not Cross, so already-below positions also exit. Fading measured from each current bar Open, next tradable Open fill, unchanged and reason priority before SMA if simultaneous. No secondary module/profit trail. Terminal closures/marks remain.', '',
        'Stocks2000-01-04 through2025-08-15, Rp1billion, ten slots, entry10% prior-close equity capped cash, compounding. Buy0.15%,sell0.25%. Fee-only fractional units/no spread. Spread stress applies modern price grid/100share lot and1tick each side counterfactually over history; not observed historical bid/ask. Same universe/adjustment/market-impact limitations. Reverse ticker priority sensitivity. All in-sample, no universal or seven-criterion claim. Active AFL unchanged.', '',
        'Sideways uses prior-bar market proxy ER, conditional annual equivalent concatenates disjoint days and is not independently executable CAGR. Baseline regression, entry-prefix causality, no-time-exit assertion, cash/slot/PnL and attribution reconciliation checked. Unit tests cover strict below/equality, gap execution next Open and suspension queue.', '',
        '| Variant | CAGR | Records | MDD | Trades | WR | Mean bars | Sideways annual equivalent |',
        '|---|---:|---:|---:|---:|---:|---:|---:|']
    for r in pd.DataFrame(rows).itertuples():
        lines.append(f'| {r.variant} | {r.cagr:.2%} | {r.records}/308 | {r.mdd:.2%} | {r.trades} | {r.wr:.2%} | {r.mean_bars:.1f} | {r.sideways_annual_equivalent:.2%} |')
    (OUT/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')


if __name__=='__main__':main()
