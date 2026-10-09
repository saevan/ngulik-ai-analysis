"""Reproduce the shorter-SMA variant currently used by the AFL."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import grid_search_timehunter as engine
from backtest_timehunter_proportional import signal


def main():
    out = Path(__file__).resolve().parent / 'timehunter_sma30_results'
    out.mkdir(exist_ok=True)
    df, _ = engine.load_data('stocks')
    groups = engine.prepare(df, dips=[.3])
    frames = {str(k): f.reset_index(drop=True) for k, f in df.groupby('Ticker', sort=True)}
    results = []
    for sma in [100, 30]:
        records = []
        for g in groups:
            sig = signal(frames[g.ticker], sma, 20, .02)
            n = len(sig)
            g.next_entry['variant'] = np.minimum.accumulate(np.where(sig, np.arange(n), n)[::-1])[::-1]
            _, rec = engine.simulate_group(g, 200, .3, 'variant', detail=True)
            records.extend(rec)
        trades = pd.DataFrame(records)
        r = trades.gross_return.to_numpy()
        metrics = engine.metrics(r, 0)
        metrics['pf'] = float(r[r > 0].sum() / -r[r < 0].sum())
        metrics['sma'] = sma
        metrics['fade_exits'] = int((trades.reason == 'fading').sum())
        # Compare complete ledger with the prior independent parameter sweep.
        reference = pd.read_csv(Path(__file__).resolve().parent /
            'price_indicator_hypothesis_results' / f'sma_{sma}_trades.csv')
        pd.testing.assert_frame_equal(trades, reference, check_dtype=False, rtol=1e-12, atol=1e-12)
        trades.to_csv(out / f'sma_{sma}_trades.csv', index=False)
        results.append(metrics)
    (out / 'summary.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
    pd.DataFrame(results).to_csv(out / 'comparison.csv', index=False)
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
