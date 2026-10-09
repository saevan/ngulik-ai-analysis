"""Controlled holding-cap sweep of the existing Breakout+ER portfolio."""
from pathlib import Path
import numpy as np
import pandas as pd
import grid_search_timehunter as engine
from backtest_breakout_er_portfolio import portfolio
from backtest_idx_costs import Costs

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'holding_period_results'


def main():
    OUT.mkdir(exist_ok=True)
    frame, _ = engine.load_data('stocks')
    frames = {str(k): f.reset_index(drop=True) for k, f in frame.groupby('Ticker', sort=True)}
    rows = []
    for scenario, costs, reverse in [('fees', Costs(), False),
            ('spread', Costs(grid=True, ticks_per_side=1, round_lot=100), False),
            ('fees_reverse', Costs(), True)]:
        for hold in [10, 20, 30, 50, 75, 100, 150, 200]:
            curve, trades, counts = portfolio(frames, hold=hold, cost_model=costs, reverse=reverse)
            if hold == 200 and scenario in ['fees', 'spread']:
                label = 'fees_only' if scenario == 'fees' else 'fees_1tick_each_side'
                old = pd.read_csv(ROOT/'breakout_er_idx_cost_results'/f'{label}_equity.csv')
                np.testing.assert_allclose(curve.equity, old.equity, rtol=1e-10)
            years = (curve.index[-1]-curve.index[0]).days/365.25
            r = trades.net_return
            wins, losses = r[r>0], r[r<0]
            pnl = trades.pnl
            row = dict(scenario=scenario, hold=hold, cagr=(curve.equity.iloc[-1]/1e9)**(1/years)-1,
                mdd=curve.drawdown.min(), records=int(curve.new_high.groupby(curve.index.to_period('M')).any().sum()),
                months=curve.index.to_period('M').nunique(), trades=len(trades), wr=(r>0).mean(),
                money_pf=pnl[pnl>0].sum()/-pnl[pnl<0].sum(), payout=wins.mean()/-losses.mean(),
                mean_trade_return=r.mean(), median_trade_return=r.median(), average_win=wins.mean(),
                average_loss=losses.mean(), mean_bars=trades.bars.mean(),
                invested=(curve.market_value/curve.equity).mean(), final_equity=curve.equity.iloc[-1], **counts)
            rows.append(row)
            name=f'{scenario}_h{hold}'
            curve.to_csv(OUT/f'{name}_equity.csv')
            trades.to_csv(OUT/f'{name}_trades.csv', index=False)
            # Time slices describe stability within the searched sample, not holdout validation.
            for start, end in [('2000', '2009'), ('2010', '2019'), ('2020', '2025')]:
                segment=curve.loc[start:end]
                previous=curve.equity.shift(1).fillna(1e9).loc[segment.index[0]]
                row[f'return_{start}_{end}']=segment.equity.iloc[-1]/previous-1
            pd.DataFrame(rows).to_csv(OUT/'comparison.csv', index=False)
            print(f'{scenario} H{hold}: CAGR {row["cagr"]:.2%}, records {row["records"]}/308, trades {len(trades)}', flush=True)
    result=pd.DataFrame(rows)
    lines=['# Holding period sweep', '',
        'Existing Breakout+ER module, not the pullback AFL currently open. Only maximum holding bars vary; entry ER20>=0.30 and prior-HHV20 breakout, fade5 previous ATR14, next tradable Open entry/fade exit, scheduled hold-bar Close exit remain unchanged. Holding cap differs from observed mean duration.', '',
        'Stocks 2000-01-04 through 2025-08-15; Rp1 billion, ten slots, compounding from prior-close equity. Buy fee0.15%, sell fee0.25%. Fees scenario has fractional units and no spread. Spread scenario applies modern grid/100-share lots and one tick each side counterfactually to history, not observed historical bid/ask. Reverse scenario changes only ticker priority.', '',
        'New trades after early exits are included under the original entry rules. Portfolio CAGR therefore tests net replacement through reinvestment; this is not a matched-trade causal decomposition of foregone profit versus replacement profit. More trades need not mean better returns. Profit can also be saved by exiting losers earlier.', '',
        'All holds and time slices use the same historical sample. No independent out-of-sample validation or universal seven-criterion pass. Original AFL untouched. H200 fee and spread curves reproduce saved baselines to numerical tolerance; engine cash/slot and terminal PnL reconciliation assertions run for every variant.', '',
        '| Scenario | Hold cap | Actual mean bars | Trades | CAGR | Record months | MDD | WR | Payout |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in result.itertuples():
        lines.append(f'| {r.scenario} | {r.hold} | {r.mean_bars:.2f} | {r.trades} | {r.cagr:.2%} | {r.records}/308 ({r.records/308:.2%}) | {r.mdd:.2%} | {r.wr:.2%} | {r.payout:.2f} |')
    (OUT/'REPORT.md').write_text('\n'.join(lines), encoding='utf-8')


if __name__=='__main__':
    main()
