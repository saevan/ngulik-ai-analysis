"""TimeHunter + fading loss exit, exploratory in-sample comparison.

Low[t] <= Open[t]*(1-dip) signals exit at NEXT open, not a guaranteed stop fill.
The level resets each bar; entry price is used for PnL, not the fading trigger.
Reenter at the following open; restart the 50-bar clock. Time exits occur
at the 50th close. All variants liquidate remaining positions at data end.
Uses the same OHLC normalization as backtest_lomba; does not edit source CSV.
Reported statistics are pooled trades, not portfolio returns or drawdowns.
Research uses gross returns only; no fees, tax, spread or slippage adjustments.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from backtest_lomba import load_stocks


def simulate(df, dip=None, hold=50):
    if hold < 1 or (dip is not None and not 0 < dip < 1):
        raise ValueError('Invalid hold or dip')
    o, h, low, c = (df[k].to_numpy(dtype=float) for k in ['Open', 'High', 'Low', 'Close'])
    dates = df['Date/Time'].to_numpy()
    n = len(df)
    records = []
    entry = 0
    while entry < n:
        deadline = min(entry + hold - 1, n - 1)
        end = deadline
        price = c[end]
        reason = 'time' if entry + hold <= n else 'data_end'
        if dip is not None:
            # Exclude deadline: a new signal there would exceed the deadline.
            hits = np.flatnonzero(low[entry:deadline] <= o[entry:deadline] * (1 - dip))
            if len(hits):
                end = entry + int(hits[0]) + 1
                price = o[end]
                reason = 'fading'
        # Never count the low AFTER an open exit as an experienced loss.
        seen_lows = low[entry:end] if reason == 'fading' else low[entry:end+1]
        trough = min(o[entry], price, seen_lows.min())
        records.append(dict(entry=entry, exit=end, entry_date=str(dates[entry]),
                            exit_date=str(dates[end]), reason=reason,
                            pnl=price/o[entry]-1, bars=end-entry+1,
                            adverse_excursion=trough/o[entry]-1))
        entry = end + 1
    return pd.DataFrame(records)


def checks():
    frame = pd.DataFrame({'Date/Time': pd.date_range('2000-01-01', periods=5),
                          'Open': [100, 100, 80, 90, 95],
                          'High': [101, 101, 85, 96, 100],
                          'Low': [99, 94, 70, 88, 94],
                          'Close': [100, 96, 75, 95, 99]})
    trades = simulate(frame, .05, 5)
    assert trades.iloc[0]['exit'] == 2
    assert np.isclose(trades.iloc[0]['pnl'], -.20)  # gap exceeds 5% trigger
    assert np.isclose(trades.iloc[0]['adverse_excursion'], -.20)
    assert trades.iloc[1]['entry'] == 3
    plain = simulate(frame, None, 5)
    assert len(plain) == 1 and plain.iloc[0]['exit'] == 4
    assert np.isclose(plain.iloc[0]['pnl'], -.01)
    assert simulate(frame, None, 3).iloc[-1]['reason'] == 'data_end'
    # Adding future bars cannot change a completed trade.
    assert simulate(frame.iloc[:3], .05, 5).iloc[0]['pnl'] == trades.iloc[0]['pnl']


def main():
    checks()
    data = load_stocks()
    prices = data[['Open', 'High', 'Low', 'Close']].to_numpy()
    if not np.isfinite(prices).all() or (prices <= 0).any():
        raise ValueError('Nonfinite or nonpositive prices')
    if data.duplicated(['Ticker', 'Date/Time']).any():
        raise ValueError('Duplicate ticker/date')
    groups = list(data.groupby('Ticker', sort=False))
    rows = []
    for dip in [None, .03, .05, .10, .15]:
        trades = pd.concat([simulate(g, dip).assign(ticker=t) for t, g in groups], ignore_index=True)
        p = trades.pnl
        wins = p[p > 0]
        losses = p[p < 0]
        row = dict(fading_reference='current_bar_open',
                   dip='time_only' if dip is None else f'{dip:.0%}',
                   trades=len(p), wr_pct=100*(p > 0).mean(),
                   avg_win_pct=100*wins.mean(), avg_loss_pct=100*losses.mean(),
                   payout=wins.mean()/abs(losses.mean()),
                   mean_pct=100*p.mean(), median_pct=100*p.median(),
                   p05_pct=100*p.quantile(.05), worst_pct=100*p.min(),
                   mean_bars=trades.bars.mean(),
                   mean_adverse_pct=100*trades.adverse_excursion.mean(),
                   fading_pct=100*(trades.reason == 'fading').mean(),
                   end_trades=int((trades.reason == 'data_end').sum()))
        row['result_basis'] = 'gross'
        row['cost_per_side'] = 0.0
        rows.append(row)
        print(json.dumps(row), flush=True)
    out = Path(__file__).with_name('timehunter_bar_open_price_gross_results.csv')
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f'Saved {out}; synthetic checks passed.', flush=True)


if __name__ == '__main__':
    main()
