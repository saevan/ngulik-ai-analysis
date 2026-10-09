"""Remove scheduled time exit only; compare with original H200."""
from pathlib import Path
import numpy as np
import pandas as pd
import grid_search_timehunter as engine
from backtest_breakout_er_portfolio import portfolio
from backtest_idx_costs import Costs
from analyze_portfolio_regimes import regime_proxy, attribute

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'no_hold_limit_results'


def main():
    OUT.mkdir(exist_ok=True)
    data,_=engine.load_data('stocks')
    frames={str(k):f.reset_index(drop=True) for k,f in data.groupby('Ticker',sort=True)}
    proxy=regime_proxy(data);rows=[];regimes=[]
    for scenario,cost in [('fees',Costs()),('spread',Costs(grid=True,ticks_per_side=1,round_lot=100))]:
        for reverse in [False,True]:
            for hold in [200,None]:
                label=f'{scenario}_h{hold}_reverse{reverse}'
                curve,trades,counts=portfolio(frames,hold=hold,cost_model=cost,reverse=reverse)
                if hold==200 and not reverse:
                    name='fees_only' if scenario=='fees' else 'fees_1tick_each_side'
                    old=pd.read_csv(ROOT/'breakout_er_idx_cost_results'/f'{name}_equity.csv')
                    np.testing.assert_allclose(curve.equity,old.equity,rtol=1e-10)
                if hold is None:assert not trades.reason.str.startswith('time').any()
                years=(curve.index[-1]-curve.index[0]).days/365.25
                r=trades.net_return
                row=dict(variant=label,scenario=scenario,reverse=reverse,hold='none' if hold is None else hold,
                    cagr=(curve.equity.iloc[-1]/1e9)**(1/years)-1,mdd=curve.drawdown.min(),
                    records=int(curve.new_high.groupby(curve.index.to_period('M')).any().sum()),
                    trades=len(trades),wr=(r>0).mean(),payout=r[r>0].mean()/-r[r<0].mean(),
                    mean_bars=trades.bars.mean(),max_bars=trades.bars.max(),cash_fraction=(curve.cash/curve.equity).mean(),
                    fade_exits=int((trades.reason=='fading').sum()),terminal_exits=int(trades.reason.str.startswith('period_end').sum()),
                    time_exits=int(trades.reason.str.startswith('time').sum()),**counts)
                stats,_=attribute(curve,proxy,'stocks',label);regimes.append(stats)
                side=stats[stats.regime=='sideways'].iloc[0]
                row['sideways_annual_equivalent']=side.conditional_annualized
                row['sideways_records']=side.months_record
                rows.append(row)
                curve.to_csv(OUT/f'{label}_equity.csv');trades.to_csv(OUT/f'{label}_trades.csv',index=False)
                pd.DataFrame(rows).to_csv(OUT/'comparison.csv',index=False)
                print(label,f'CAGR {row["cagr"]:.2%}, records {row["records"]}/308, trades {len(trades)}, mean bars {row["mean_bars"]:.1f}',flush=True)
    pd.concat(regimes).to_csv(OUT/'regimes.csv',index=False)
    lines=['# Remove H200 time exit','',
        'Existing Breakout+ER module, not the pullback AFL currently open. Only change: hold=None disables time exits; fading remains current Open-Low>=5*prior ATR14 then exit next tradable Open. No trailing or secondary module. All remaining positions closed/marked at end of their data series for terminal valuation; those closures are not recurring strategy exit signals.', '',
        'Stocks2000-01-04 to2025-08-15, initialRp1billion, ten slots, prior-close equity allocation, compounding, one position per ticker. Buy0.15%,sell0.25%. Fees scenario fractional units/no spread. Spread stress uses modern grid/100share lots and1tick per side throughout history counterfactually, not observed historical bid/ask. Reverse ticker priority sensitivity included. Data/universe/liquidity limitations unchanged.', '',
        'No hold cap can lengthen positions and increase terminal dependence; it does not mean selling earlier. Baseline equity regression matches saved results. All simulations run cash/slot/PnL assertions. No time exits allowed in no-cap ledger. Regime attribution reconciles to portfolio CAGR; sideways annual equivalent concatenates disjoint days, not a standalone strategy CAGR. In-sample research, no claim of seven criteria or independent validation. Active AFL unchanged.', '',
        '| Variant | CAGR | Record months | MDD | Trades | Mean holding bars | Fade exits | Terminal exits | Sideways annual equivalent |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in pd.DataFrame(rows).itertuples():
        lines.append(f'| {r.variant} | {r.cagr:.2%} | {r.records}/308 | {r.mdd:.2%} | {r.trades} | {r.mean_bars:.1f} | {r.fade_exits} | {r.terminal_exits} | {r.sideways_annual_equivalent:.2%} |')
    (OUT/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')


if __name__=='__main__':main()
