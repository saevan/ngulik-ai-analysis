"""Empirical sweep of every price component in the current strategy family.

This is a research runner, not a claim about every technical indicator.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import grid_search_timehunter as engine

OUT = Path(__file__).resolve().parent / 'price_indicator_hypothesis_results'
LENGTHS = [5, 10, 20, 30, 50, 75, 100, 150, 200]
FAMILIES = ['sma_only', 'sma_combined', 'pullback_only', 'pullback_combined', 'breakout', 'rebound_combined']


def condition(f, family, value):
    c, h = f.Close, f.High
    trend = c > c.rolling(100).mean()
    pullback = 1 - c / h.rolling(20).max() >= .02
    rebound = c > c.shift(1)
    if family == 'sma_only':
        return c > c.rolling(int(value)).mean()
    if family == 'sma_combined':
        return (c > c.rolling(int(value)).mean()) & pullback & rebound
    if family == 'pullback_only':
        return 1 - c / h.rolling(int(value)).max() >= .02
    if family == 'pullback_combined':
        return trend & (1 - c / h.rolling(int(value)).max() >= .02) & rebound
    if family == 'breakout':
        return c > h.shift(1).rolling(int(value)).max()
    if family == 'rebound_combined':
        return trend & pullback & (c > c.shift(int(value)))
    if family == 'pullback_depth':
        return trend & (1 - c / h.rolling(20).max() >= value) & rebound
    raise ValueError(family)


def main():
    OUT.mkdir(exist_ok=True)
    df, _ = engine.load_data('stocks')
    fades = [.02, .03, .05, .075, .1, .15, .2, .3]
    groups = engine.prepare(df, dips=fades)
    frames = {str(k): v.reset_index(drop=True) for k, v in df.groupby('Ticker', sort=True)}
    settings = [(family, n) for family in FAMILIES for n in
                ([1, 2, 3, 5, 10, 20, 30, 50, 100] if family == 'rebound_combined' else LENGTHS)]
    settings += [('pullback_depth', d) for d in [.005, .01, .02, .03, .05, .075, .1, .15]]
    signal_counts = {}
    for family, value in settings:
        name = f'{family}_{value}'
        signal_counts[name] = 0
        for g in groups:
            f = frames[g.ticker]
            cond = condition(f, family, value)
            sig = cond.shift(1, fill_value=False).to_numpy(bool)
            # Prefix causality: appending data must not change past entry signals.
            cut = min(300, len(f))
            assert np.array_equal(sig[:cut], condition(f.iloc[:cut], family, value).shift(1, fill_value=False).to_numpy(bool))
            n = len(sig)
            g.next_entry[name] = np.minimum.accumulate(np.where(sig, np.arange(n), n)[::-1])[::-1]
            signal_counts[name] += int(sig.sum())
            if family == 'sma_combined' and value == 100:
                assert np.array_equal(sig, g.signals['trend_100_rebound_2'])
    configs = [(family, value, hold, dip) for family, value in settings
               for hold in [50, 100, 200] for dip in [None, .3]]
    configs += [('fading', d, hold, d) for d in fades[:-1] for hold in [50, 100, 200]]
    rows = []
    for ix, (family, value, hold, dip) in enumerate(configs):
        name = f'{family}_{value}' if family != 'fading' else 'sma_combined_100'
        chunks = []
        records = []
        save = family == 'sma_combined' and value in [30, 100] and hold == 200 and dip == .3
        for g in groups:
            r, rec = engine.simulate_group(g, hold, dip, name, detail=save)
            chunks.append(r)
            records.extend(rec)
        r = np.concatenate(chunks)
        s = engine.metrics(r, 0)
        loss = -r[r < 0].sum()
        s['pf'] = float(r[r > 0].sum() / loss) if loss else float('inf')
        rows.append(dict(family=family, value=value, hold=hold, fade='off' if dip is None else str(dip),
                         signal_bars=signal_counts[name], **s))
        if save:
            pd.DataFrame(records).to_csv(OUT / f'sma_{value}_trades.csv', index=False)
        if (ix+1) % 50 == 0:
            print(f'{ix+1}/{len(configs)} complete', flush=True)
    grid = pd.DataFrame(rows)
    grid.to_csv(OUT / 'grid.csv', index=False)
    base = grid[(grid.family == 'sma_combined') & (grid.value == 100) & (grid.hold == 200) & (grid.fade == '0.3')].iloc[0]
    assert base.n == 1974 and np.isclose(base['mean'], .2625687848471162)
    paired = []
    for family in FAMILIES:
        values = sorted(grid.loc[grid.family == family, 'value'].unique())
        for short, long in zip(values[:-1], values[1:]):
            a = grid[(grid.family == family) & (grid.value == short)]
            b = grid[(grid.family == family) & (grid.value == long)]
            merged = a.merge(b, on=['hold', 'fade'], suffixes=('_short', '_long'), validate='one_to_one')
            for r in merged.itertuples():
                paired.append(dict(family=family, short=short, long=long, hold=r.hold, fade=r.fade,
                    short_more_trades=r.n_short > r.n_long, n_short=r.n_short, n_long=r.n_long,
                    trade_ratio=r.n_short/r.n_long, mean_short=r.mean_short, mean_long=r.mean_long,
                    mean_delta=r.mean_short-r.mean_long, wr_delta=r.wr_short-r.wr_long,
                    pf_delta=r.pf_short-r.pf_long, signal_ratio=r.signal_bars_short/r.signal_bars_long))
    paired = pd.DataFrame(paired)
    paired.to_csv(OUT / 'matched_pairs.csv', index=False)
    stats = paired.groupby('family').agg(pairs=('short_more_trades', 'size'),
        fraction_short_more_trades=('short_more_trades', 'mean'), median_trade_ratio=('trade_ratio', 'median'),
        mean_delta_min=('mean_delta', 'min'), mean_delta_max=('mean_delta', 'max'),
        wr_delta_min=('wr_delta', 'min'), wr_delta_max=('wr_delta', 'max'),
        median_abs_wr_delta=('wr_delta', lambda x: x.abs().median()))
    stats.to_csv(OUT / 'family_summary.csv')
    def table(t):
        lines = ['| Indicator | Value | Hold | Fade | Signal bars | Trades | WR | PF | Mean | Median | Payout |',
                 '|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|']
        for r in t.itertuples():
            lines.append(f'| {r.family} | {r.value:g} | {r.hold} | {r.fade} | {r.signal_bars} | {r.n} | {r.wr:.2%} | {r.pf:.3f} | {r.mean:.2%} | {r.median:.2%} | {r.payout:.3f} |')
        return '\n'.join(lines)
    lines = ['# Does shortening price indicators preserve returns and increase trades?',
        f'{len(grid)} configurations, 100 stocks, continuous 1994-07-12 to 2025-08-15, zero costs. Every execution uses the existing engine; fading references each current bar Open and executes next tradable Open.',
        'Scope: every price component in the existing strategy family (SMA, rolling-high pullback window/depth, breakout, rebound lookback, fading threshold). Not every indicator ever invented. A rebound over N bars is an explicit variant of the original one-bar rebound. Hold is controlled at 50, 100 and 200, rather than shortened along with indicators.',
        'The user clarified that 30% refers to WIN RATE. Check both trade frequency and changes in WR; mean return remains an additional metric only. PF uses equal entry notional. A signal bar is not an actual trade: only one position per symbol and entry cannot occur while holding. Comparisons are descriptive, in-sample, not tests of statistical equivalence or causality. Windows have their natural warmups. Corporate actions and survivorship remain unaudited.',
        'Validation: prefix causality checked for all entry variants and tickers; original SMA100 entry signals and 1,974-trade baseline reproduced.',
        '## SMA30 versus SMA100, other parameters fixed',
        table(grid[(grid.family.isin(['sma_only', 'sma_combined'])) & grid.value.isin([30,100])]),
        '## All price components at hold=200 / fading=30%',
        table(grid[(grid.hold == 200) & (grid.fade == '0.3')]),
        '## Fading sensitivity at hold=200 (original entry)',
        table(grid[(grid.family == 'fading') & (grid.hold == 200)]),
        '## Matched adjacent-window comparisons',
        'Every comparison changes only one lookback, with hold and fade unchanged. Fraction below counts configurations, NOT independent statistical observations.',
        stats.to_string(),
        'Reproduce: python test_price_indicator_hypothesis.py']
    (OUT / 'REPORT.md').write_text('\n\n'.join(lines), encoding='utf-8')
    print(table(grid[(grid.family.isin(['sma_only', 'sma_combined'])) & grid.value.isin([30,100])]), flush=True)
    print(stats.to_string(), flush=True)
    print(json.dumps(dict(configurations=len(grid), matched_pairs=len(paired))), flush=True)


if __name__ == '__main__':
    main()
