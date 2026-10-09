"""Independent checks for TimeHunter's price/time search.

The slow reference deliberately scans bars rather than using precomputed
entry/exit lookup arrays. Reference comparisons cover tradable bars; separate
tests set the tradability mask to exercise queued orders during suspensions.
"""
import unittest

import numpy as np
import pandas as pd

import backtest_timehunter_price as price
import grid_search_timehunter as search


def fixture(opens, highs, lows, closes):
    n = len(opens)
    return pd.DataFrame({
        'Ticker': ['TEST'] * n,
        'Date/Time': pd.date_range('2000-01-01', periods=n),
        'Open': opens, 'High': highs, 'Low': lows, 'Close': closes,
        'Volume': np.full(n, 100000.),
    })


def slow_reference(frame, signal, hold, dip, start=None, stop=None):
    """Scan every eligible entry and signal bar with explicit chronology."""
    dates = frame['Date/Time'].to_numpy()
    left = 0 if start is None else int(np.searchsorted(dates, np.datetime64(start)))
    right = len(frame) if stop is None else int(np.searchsorted(dates, np.datetime64(stop)))
    trades = []
    cursor = left
    while cursor < right:
        if not signal[cursor]:
            cursor += 1
            continue
        entered = cursor
        entry_price = float(frame.Open.iloc[entered])
        deadline = min(entered + hold - 1, right - 1)
        reason = 'time' if entered + hold <= right else 'period_end'
        exited = deadline
        price = float(frame.Close.iloc[deadline])
        if dip is not None:
            for day in range(entered, deadline):
                bar_open = float(frame.Open.iloc[day])
                if float(frame.Low.iloc[day]) <= bar_open * (1 - dip):
                    exited = day + 1
                    price = float(frame.Open.iloc[exited])
                    reason = 'fading'
                    break
        trades.append((entered, exited, price / entry_price - 1, reason))
        cursor = exited + 1
    return trades


class TimeHunterIndependentTests(unittest.TestCase):
    def assert_both_engines(self, frame, hold, dip, expected):
        """Compare two implementations with explicit hand-calculated trades."""
        group = search.prepare(frame, dips=[dip])[0]
        pnl, records = search.simulate_group(group, hold, dip, 'always', detail=True)
        simple = price.simulate(frame, dip, hold)
        for engine, actual in [
            ('grid', [(r['entry_index'], r['exit_index'], r['gross_return'], r['reason'])
                      for r in records]),
            ('simple', [(r.entry, r.exit, r.pnl,
                         'period_end' if r.reason == 'data_end' else r.reason)
                        for r in simple.itertuples()]),
        ]:
            with self.subTest(engine=engine):
                self.assertEqual([(r[0], r[1], r[3]) for r in actual],
                                 [(r[0], r[1], r[3]) for r in expected])
                np.testing.assert_allclose([r[2] for r in actual],
                                           [r[2] for r in expected], rtol=1e-12, atol=1e-12)
        np.testing.assert_allclose(pnl, [r[2] for r in expected], rtol=1e-12, atol=1e-12)

    def test_fading_uses_current_open_even_while_trade_is_profitable(self):
        # Entry = 100. Next bar drops 120 -> 113 (>5%), even though it
        # remains above entry. Sell at the following open, 114.
        frame = fixture([100, 120, 114, 115], [101, 121, 116, 117],
                        [99, 113, 113, 114], [100, 119, 115, 116])
        self.assert_both_engines(frame, 4, .05,
                                 [(0, 2, .14, 'fading'),
                                  (3, 3, 116 / 115 - 1, 'period_end')])

    def test_gap_loss_alone_does_not_trigger_fading(self):
        # The gap 100 -> 80 puts the position down 20%, but 80 -> 79
        # is only a 1.25% decline within that bar, so hold to final close.
        frame = fixture([100, 80, 82, 84], [101, 82, 84, 86],
                        [99, 79, 81, 83], [100, 81, 83, 85])
        self.assert_both_engines(frame, 4, .05, [(0, 3, -.15, 'time')])

    def test_fading_level_resets_up_and_down_at_every_new_open(self):
        # Bar opens 100, 120, 80, 110 imply levels 95, 114, 76, 104.5.
        # Only the fourth bar's low (104) hits its own level; neither
        # a fixed entry level nor carrying forward an earlier open works.
        frame = fixture([100, 120, 80, 110, 108], [101, 121, 81, 111, 110],
                        [99, 115, 78, 104, 107], [100, 118, 80, 106, 109])
        self.assert_both_engines(frame, 5, .05, [(0, 4, .08, 'fading')])

    def test_simple_engine_matches_sequential_reference(self):
        rng = np.random.default_rng(14317)
        n = 245
        closes = 100 * np.exp(np.cumsum(rng.normal(.0005, .025, n)))
        opens = np.r_[100., closes[:-1]] * np.exp(rng.normal(0., .02, n))
        highs = np.maximum(opens, closes) * np.exp(np.abs(rng.normal(0., .025, n)))
        lows = np.minimum(opens, closes) * np.exp(-np.abs(rng.normal(0., .025, n)))
        frame = fixture(opens, highs, lows, closes)
        for hold in [1, 2, 10, 50, 200]:
            for dip in [None, .03, .10]:
                with self.subTest(hold=hold, dip=dip):
                    expected = slow_reference(frame, np.ones(n, dtype=bool), hold, dip)
                    actual = price.simulate(frame, dip, hold)
                    np.testing.assert_allclose(actual.pnl, [r[2] for r in expected],
                                               rtol=1e-12, atol=1e-12)
                    self.assertEqual(
                        [(r.entry, r.exit, 'period_end' if r.reason == 'data_end' else r.reason)
                         for r in actual.itertuples()],
                        [(r[0], r[1], r[3]) for r in expected],
                    )

    def test_lookup_matches_sequential_reference(self):
        rng = np.random.default_rng(63019)
        n = 245
        close = 100 * np.exp(np.cumsum(rng.normal(.0005, .025, n)))
        opening = np.r_[100., close[:-1]] * np.exp(rng.normal(0., .02, n))
        high = np.maximum(opening, close) * np.exp(np.abs(rng.normal(0., .025, n)))
        low = np.minimum(opening, close) * np.exp(-np.abs(rng.normal(0., .025, n)))
        frame = fixture(opening, high, low, close)
        group = search.prepare(frame, dips=[.03, .10])[0]
        boundaries = [(None, None), ('2000-02-01', '2000-05-01')]
        for hold in [1, 2, 10, 50, 200]:
            for dip in [None, .03, .10]:
                for name in ['always', 'trend_20', 'breakout_20', 'dip_20_5']:
                    for start, stop in boundaries:
                        with self.subTest(hold=hold, dip=dip, name=name, start=start):
                            expected = slow_reference(frame, group.signals[name], hold, dip, start, stop)
                            actual, records = search.simulate_group(
                                group, hold, dip, name, start=start, stop=stop, detail=True)
                            np.testing.assert_allclose(actual, [row[2] for row in expected], rtol=1e-12, atol=1e-12)
                            self.assertEqual(
                                [(r['entry_index'], r['exit_index'], r['reason']) for r in records],
                                [(r[0], r[1], r[3]) for r in expected],
                            )

    def test_gap_exit_is_not_capped_at_stop_and_ignores_later_low(self):
        frame = fixture([100, 100, 70, 80], [102, 101, 75, 84],
                        [99, 94, 40, 79], [100, 96, 60, 83])
        group = search.prepare(frame, dips=[.05])[0]
        pnl, records = search.simulate_group(group, 4, .05, 'always', detail=True)
        self.assertAlmostEqual(pnl[0], -.30)
        self.assertEqual(records[0]['exit_index'], 2)
        self.assertAlmostEqual(records[0]['adverse_excursion'], -.30)
        self.assertEqual(records[1]['entry_index'], 3)

    def test_exact_deadline_and_signal_at_deadline(self):
        frame = fixture([100] * 6, [102] * 6,
                        [99, 99, 80, 99, 99, 99], [101] * 6)
        group = search.prepare(frame, dips=[.05])[0]
        pnl, records = search.simulate_group(group, 3, .05, 'always', detail=True)
        self.assertEqual([(r['entry_index'], r['exit_index']) for r in records], [(0, 2), (3, 5)])
        self.assertTrue(all(r['reason'] == 'time' for r in records))
        np.testing.assert_allclose(pnl, [.01, .01])

    def test_predeadline_signal_exits_at_deadline_open(self):
        frame = fixture([100, 100, 90], [101, 101, 92], [99, 94, 80], [100, 95, 85])
        group = search.prepare(frame, dips=[.05])[0]
        pnl, records = search.simulate_group(group, 3, .05, 'always', detail=True)
        self.assertAlmostEqual(pnl[0], -.10)
        self.assertEqual(records[0]['reason'], 'fading')
        self.assertEqual(records[0]['exit_index'], 2)

    def test_period_boundary_blocks_future_open(self):
        frame = fixture([100, 100, 1], [101, 101, 1], [99, 94, 1], [100, 96, 1])
        group = search.prepare(frame, dips=[.05])[0]
        pnl, records = search.simulate_group(
            group, 50, .05, 'always', stop='2000-01-03', detail=True)
        self.assertAlmostEqual(pnl[0], -.04)
        self.assertEqual(records[0]['exit_index'], 1)
        self.assertEqual(records[0]['reason'], 'period_end')

    def test_entry_indicators_are_prefix_invariant_and_shifted(self):
        n = 250
        close = 100 + np.arange(n) * .1 + 4 * np.sin(np.arange(n) / 4)
        frame = fixture(close, close + 1, close - 1, close)
        original = search.entry_signals(frame)
        for cutoff in [30, 101, 210]:
            prefix = search.entry_signals(frame.iloc[:cutoff].copy())
            changed = frame.copy()
            changed.loc[cutoff:, ['Open', 'High', 'Low', 'Close']] *= 3
            future_changed = search.entry_signals(changed)
            for name in original:
                np.testing.assert_array_equal(prefix[name], original[name][:cutoff])
                # Signal for Open[cutoff] must not inspect any OHLC[cutoff].
                np.testing.assert_array_equal(future_changed[name][:cutoff + 1], original[name][:cutoff + 1])
        # Direct independent check on a trend signal's first possible bar.
        monotonic = fixture(np.arange(100, 125), np.arange(101, 126),
                            np.arange(99, 124), np.arange(100, 125))
        signal = search.entry_signals(monotonic)['trend_20']
        self.assertFalse(signal[:20].any())
        self.assertTrue(signal[20:].all())

    def test_breakout_requires_prior_complete_rolling_window(self):
        frame = fixture([100] * 23, [101] * 20 + [106, 106, 106],
                        [99] * 23, [100] * 20 + [105, 105, 105])
        signal = search.entry_signals(frame)['breakout_20']
        self.assertFalse(signal[:21].any())
        self.assertTrue(signal[21])
        self.assertFalse(signal[22])

    def test_metrics_exclude_breakeven_from_loss_size(self):
        summary = search.metrics(np.array([0., .1, -.05, .2, .4]), 0.)
        self.assertEqual(summary['n'], 5)
        self.assertAlmostEqual(summary['wr'], .6)
        self.assertAlmostEqual(summary['avg_win'], .7 / 3)
        self.assertAlmostEqual(summary['avg_loss'], .05)
        self.assertAlmostEqual(summary['payout'], 14 / 3)
        self.assertAlmostEqual(summary['mean'], .13)
        self.assertAlmostEqual(summary['median'], .1)
        self.assertEqual(summary['numeric_passes'], 5)

    def test_costs_apply_to_entry_and_exit_not_only_winners(self):
        gross = np.array([0., .10, -.05])
        cost = .002
        expected = (1 + gross) * .998 / 1.002 - 1
        summary = search.metrics(gross, cost)
        self.assertAlmostEqual(summary['mean'], expected.mean())
        self.assertAlmostEqual(summary['avg_loss'], -expected[expected < 0].mean())
        self.assertAlmostEqual(summary['wr'], 1 / 3)

    def test_research_defaults_score_raw_returns_without_costs(self):
        # Exercise the actual default evaluate path, including a flat trade.
        # Merely changing display labels must not leave old fees in scoring.
        self.assertEqual(search.STOCK_COST, 0.)
        self.assertEqual(search.FOREX_COST, 0.)
        frame = fixture([100] * 5, [101, 111, 101, 121, 141],
                        [99, 99, 94, 99, 99], [100, 110, 95, 120, 140])
        groups = search.prepare(frame, dips=[])
        summary, records = search.evaluate(
            groups, dict(hold=1, dip=None, entry_name='always'), detail=True)
        raw = np.array([r['exit_price'] / r['entry_price'] - 1 for r in records])
        np.testing.assert_array_equal(raw, [r['gross_return'] for r in records])
        expected = search.metrics(raw, 0.)
        self.assertEqual(summary['gross'], expected)
        for name, value in expected.items():
            self.assertEqual(summary[name], value, name)
        self.assertEqual(summary['wr'], 3 / 5)
        self.assertEqual(summary['numeric_passes'], 5)

    def test_zero_cost_preserves_tiny_returns_and_breakeven_classification(self):
        # Applying (1 + return) - 1 at zero cost can erase tiny nonzero
        # returns, changing strict win/loss and mean-positive criteria.
        gross = np.array([0., 1e-18, -1e-18, 2e-18])
        original = gross.copy()
        summary = search.metrics(gross, 0.)
        self.assertEqual(summary['wr'], .5)
        self.assertEqual(summary['avg_loss'], 1e-18)
        self.assertEqual(summary['mean'], gross.mean())
        self.assertEqual(summary['worst'], -1e-18)
        np.testing.assert_array_equal(gross, original)

    def test_empty_period_has_no_trades(self):
        frame = fixture([100], [101], [99], [100])
        group = search.prepare(frame, dips=[])[0]
        pnl, records = search.simulate_group(group, 1, None, 'always', start='2001-01-01', detail=True)
        self.assertEqual(len(pnl), 0)
        self.assertEqual(records, [])
        self.assertEqual(search.metrics(pnl, 0)['numeric_passes'], 0)

    def test_zero_volume_entry_waits_for_first_available_open(self):
        frame = fixture([100, 110, 120, 130], [102, 112, 122, 132],
                        [99, 109, 119, 129], [101, 111, 121, 131])
        frame['tradable'] = [False, False, True, True]
        group = search.prepare(frame, dips=[])[0]
        pnl, records = search.simulate_group(group, 1, None, 'always', detail=True)
        self.assertEqual([r['entry_index'] for r in records], [2, 3])
        self.assertAlmostEqual(records[0]['entry_price'], 120)
        np.testing.assert_allclose(pnl, [121 / 120 - 1, 131 / 130 - 1])

    def test_fading_waits_through_suspension_without_capping_gap(self):
        frame = fixture([100, 99, 99, 70, 80], [101, 99, 99, 75, 82],
                        [94, 99, 99, 40, 79], [95, 99, 99, 60, 81])
        frame['tradable'] = [True, False, False, True, True]
        group = search.prepare(frame, dips=[.05])[0]
        pnl, records = search.simulate_group(group, 5, .05, 'always', detail=True)
        self.assertEqual(records[0]['reason'], 'fading')
        self.assertEqual(records[0]['exit_index'], 3)
        self.assertTrue(records[0]['exit_at_open'])
        self.assertAlmostEqual(pnl[0], -.3)
        self.assertAlmostEqual(records[0]['adverse_excursion'], -.3)
        self.assertEqual(records[1]['entry_index'], 4)

    def test_scheduled_exit_queues_past_zero_volume_deadline(self):
        frame = fixture([100, 99, 99, 70, 80], [101, 99, 99, 75, 82],
                        [99, 99, 99, 40, 79], [100, 99, 99, 60, 81])
        frame['tradable'] = [True, False, False, True, True]
        group = search.prepare(frame, dips=[])[0]
        pnl, records = search.simulate_group(group, 2, None, 'always', detail=True)
        self.assertEqual(records[0]['reason'], 'time_delayed')
        self.assertEqual(records[0]['exit_index'], 3)
        self.assertAlmostEqual(pnl[0], -.3)
        self.assertAlmostEqual(records[0]['adverse_excursion'], -.3)

    def test_unfilled_order_at_boundary_is_mark_not_future_fill(self):
        frame = fixture([100, 95, 95, 20], [101, 95, 95, 21],
                        [94, 95, 95, 19], [95, 95, 95, 20])
        frame['tradable'] = [True, False, False, True]
        group = search.prepare(frame, dips=[.05])[0]
        for dip in [None, .05]:
            with self.subTest(dip=dip):
                pnl, records = search.simulate_group(
                    group, 2, dip, 'always', stop='2000-01-04', detail=True)
                self.assertEqual(len(records), 1)
                self.assertEqual(records[0]['reason'], 'period_end_mark')
                self.assertEqual(records[0]['exit_index'], 2)
                self.assertFalse(records[0]['exit_at_open'])
                self.assertAlmostEqual(pnl[0], -.05)


if __name__ == '__main__':
    unittest.main()
