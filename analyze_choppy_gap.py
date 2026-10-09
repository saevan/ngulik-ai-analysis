"""Diagnose choppy-market inactivity and ER removal, without changing live AFL."""
from pathlib import Path
import numpy as np
import pandas as pd
import grid_search_timehunter as engine
from backtest_breakout_er import entry_signal
from backtest_breakout_er_portfolio import portfolio
from backtest_idx_costs import Costs
from analyze_portfolio_regimes import attribute, regime_proxy

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'choppy_gap_results'


def main():
    OUT.mkdir(exist_ok=True)
    stocks, _ = engine.load_data('stocks')
    frames = {str(k): f.reset_index(drop=True) for k, f in stocks.groupby('Ticker', sort=True)}
    proxy = regime_proxy(stocks)
    cut = proxy.index[len(proxy)//2]
    pd.testing.assert_series_equal(regime_proxy(stocks[stocks['Date/Time'] <= cut]).regime, proxy.loc[:cut, 'regime'])
    variants = {}
    for name in ['afl_ideal_net', 'stop_order_net', 'next_open_net']:
        base = ROOT / 'prototype_swinger_benchmark_results'
        variants[name] = (pd.read_csv(base/f'{name}_equity.csv', parse_dates=['date']).set_index('date'),
                          pd.read_csv(base/f'{name}_trades.csv', parse_dates=['entry_date']))
    for label, model in [('fees_only', Costs()), ('fees_1tick_each_side', Costs(grid=True, ticks_per_side=1, round_lot=100))]:
        base = ROOT / 'breakout_er_idx_cost_results'
        variants['ER_'+label] = (pd.read_csv(base/f'{label}_equity.csv', parse_dates=['date']).set_index('date'),
                                pd.read_csv(base/f'{label}_trades.csv', parse_dates=['entry_date']))
        curve, trades, counts = portfolio(frames, threshold=None, cost_model=model)
        name = 'no_ER_'+label
        curve.to_csv(OUT/f'{name}_equity.csv')
        trades.to_csv(OUT/f'{name}_trades.csv', index=False)
        variants[name] = curve, trades
        print(name, counts, flush=True)
    all_regimes, overall = [], []
    for name, (curve, trades) in variants.items():
        stats, daily = attribute(curve, proxy, 'stocks', name)
        entry_regimes = trades.entry_date.map(proxy.regime)
        for i, row in stats.iterrows():
            g = daily[daily.regime == row.regime]
            stats.loc[i, 'entries'] = int((entry_regimes == row.regime).sum())
            stats.loc[i, 'flat_day_fraction'] = (g.positions == 0).mean()
            stats.loc[i, 'average_positions'] = g.positions.mean()
            stats.loc[i, 'full_slot_day_fraction'] = (g.positions == 10).mean()
        all_regimes.append(stats)
        years = (curve.index[-1]-curve.index[0]).days/365.25
        overall.append(dict(variant=name, cagr=(curve.equity.iloc[-1]/1e9)**(1/years)-1,
            mdd=curve.drawdown.min(), records=int(curve.new_high.groupby(curve.index.to_period('M')).any().sum()),
            months=curve.index.to_period('M').nunique(), trades=len(trades), wr=(trades.pnl>0).mean(),
            mean_bars=trades.bars.mean(), invested=(curve.market_value/curve.equity).mean()))
        daily.to_csv(OUT/f'{name}_attribution.csv')
    signals = []
    for ticker, f in frames.items():
        raw, gated = entry_signal(f), entry_signal(f, .3)
        z = pd.DataFrame({'date': f['Date/Time'], 'raw': raw, 'gated': gated})
        z = z[z.date >= '2000-01-01']
        z['regime'] = z.date.map(proxy.regime)
        signals.append(z)
    pd.concat(signals).groupby('regime')[['raw','gated']].sum().to_csv(OUT/'signal_counts.csv')
    result = pd.concat(all_regimes, ignore_index=True)
    result.to_csv(OUT/'regimes.csv', index=False)
    comparison = pd.DataFrame(overall)
    comparison.to_csv(OUT/'comparison.csv', index=False)
    print(comparison.to_string(index=False))
    print(result[['variant','regime','conditional_annualized','annualized_contribution','mean_invested_fraction','entries','flat_day_fraction','average_positions']].to_string(index=False))
    (OUT/'METHODOLOGY.md').write_text('''# Choppy-market diagnosis

Stocks 2000-01-04 to 2025-08-15. Initial Rp1 billion, ten slots, prior-close equity sizing with compounding. Buy fee 0.15%, sell fee 0.25%. Fee-only comparisons share cost assumptions with Swinger ideal. Additional tick scenario retains previous counterfactual modern IDX grid, 100-share lots and one tick each side; it is not reconstructed historical bid/ask.

Market regime: equal-weight available-stock return proxy, previous completed bar ER20 >= 0.30 with positive/negative 20-bar direction = up/down, otherwise sideways. Not IHSG. Entry filter uses individual stock ER, so sideways proxy does not imply every stock fails ER. Signal counts count all stock-bar opportunities, including already-held stocks and capacity-rejected signals; not executable trade counts. Actual entries are separately classified by entry-date market regime.

Daily equity attribution retains existing positions and never resets equity peaks. Conditional annualized returns concatenate noncontiguous regime days; they are NOT independently executable regime CAGRs. Whole-history annualized contributions reconcile multiplicatively to actual CAGR. Exposure and flat-day rates use daily closing snapshots, not intraday observations. Returns in sideways can arise from positions entered in other regimes.

No-filter control changes only ER entry gate; same breakout, hold200, fade5 prior ATR, ranking, sizing and costs. This tests removing the gate, NOT an unimplemented mean-reversion module. Results are in-sample and priority/universe dependent. Swinger literal ideal uses current Close signal with earlier level fills and contains 964 fills outside daily ranges; its gap is not a causal estimate of the benefit of sideways trading. Stop-order variant changes signal logic; next-open preserves original completed-close signals more closely.

Checks: prefix-causal regime labels, log-return/CAGR reconciliation and preservation of equity records. No live AFL changed.
''', encoding='utf-8')


if __name__ == '__main__':
    main()
