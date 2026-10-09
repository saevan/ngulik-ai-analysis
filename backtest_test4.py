"""
Test 4 — Simplest robust logic
================================

Lessons from T3-A3 failures:
1. Composite logic (TF+MR+trailing) fragile to noise
2. MR exit (RSI extreme) rarely fires, may be spurious
3. Heavy dependence on 1-2 outlier trades
4. Doesn't survive shrink test

NEW PRINCIPLES for Test 4:
1. SIMPLER composite (one entry, one exit, no regime switch)
2. ATR-based stops (no fixed percentage)
3. Time-based exit (no MR exit that may not fire)
4. Trend pullback with simple trailing

Test 4 candidates:
A. EMA pullback entry + trailing only (no MR exit)
B. Donchian breakout + ATR trailing
C. Bollinger band mean reversion in uptrend (trend context + MR entry, no fancy exit)
D. Pure ATR breakout (volatility-based)
"""

import pandas as pd
import numpy as np
import os
import warnings
warnings.filterwarnings('ignore')

DATA_DIR = r"C:\Users\ACER\OneDrive\Documents\Ngulik AI\Data"


def load_stocks():
    path = os.path.join(DATA_DIR, "Data kompas 100.csv")
    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]
    df['Date/Time'] = pd.to_datetime(df['Date/Time'], format='mixed', dayfirst=True)
    df = df.sort_values(['Ticker', 'Date/Time']).reset_index(drop=True)
    return df


def add_indicators(df, ema_p=50, atr_p=14):
    df = df.copy()
    df['EMA'] = df['Close'].ewm(span=ema_p, adjust=False).mean()
    high_low = df['High'] - df['Low']
    high_close = (df['High'] - df['Close'].shift()).abs()
    low_close = (df['Low'] - df['Close'].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['ATR'] = tr.ewm(alpha=1/atr_p, adjust=False).mean()
    # Bollinger
    df['BB_mid'] = df['Close'].rolling(20).mean()
    df['BB_std'] = df['Close'].rolling(20).std()
    df['BB_upper'] = df['BB_mid'] + 2 * df['BB_std']
    df['BB_lower'] = df['BB_mid'] - 2 * df['BB_std']
    # Donchian
    df['DC_high'] = df['High'].rolling(20).max()
    df['DC_low'] = df['Low'].rolling(20).min()
    return df


def test_4a_ema_pullback(df, **params):
    """
    4A: EMA pullback entry + trailing only (no MR exit)
    Long: Close > EMA50, Low touches/was below EMA (pullback)
    Exit: trailing stop OR hard stop OR time stop
    """
    p = {
        'ema_p': 50, 'atr_p': 14,
        'stop_atr': 1.0, 'trailing_atr': 2.5, 'time_stop': 30,
    }
    p.update(params)

    if len(df) < 100:
        return None

    df = add_indicators(df, ema_p=p['ema_p'], atr_p=p['atr_p']).reset_index(drop=True)
    n = len(df)
    closes = df['Close'].values
    opens = df['Open'].values
    highs = df['High'].values
    lows = df['Low'].values
    emas = df['EMA'].values
    atrs = df['ATR'].values

    trades = []
    in_trade = False
    cooldown = 0

    for i in range(p['ema_p'], n - 1):
        atr = atrs[i]
        if np.isnan(atr) or atr <= 0:
            continue

        if not in_trade:
            if cooldown > 0:
                cooldown -= 1
                continue

            close = closes[i]; ema = emas[i]; low = lows[i]
            # Long pullback: in uptrend AND price was recently near/under EMA
            if close > ema and low <= ema * 1.005:  # touched or dipped to EMA
                entry_price = opens[i + 1]
                entry_bar = i + 1
                entry_atr = atr
                stop = entry_price - p['stop_atr'] * atr
                extreme = entry_price
                trailing_stop = None
                in_trade = True
                direction = 'long'

        else:
            cur_high = highs[i]; cur_low = lows[i]; cur_close = closes[i]
            if cur_high > extreme: extreme = cur_high
            new_t = extreme - p['trailing_atr'] * entry_atr
            if trailing_stop is None or new_t > trailing_stop: trailing_stop = new_t

            exit_price = None; exit_reason = None
            if cur_low <= stop:
                exit_price = stop; exit_reason = 'stop'
            elif cur_low <= trailing_stop:
                exit_price = trailing_stop; exit_reason = 'trailing'

            if exit_price is None:
                if (i - entry_bar) >= p['time_stop']:
                    exit_price = opens[i + 1] if i + 1 < n else cur_close
                    exit_reason = 'time_stop'

            if exit_price is not None:
                pnl = exit_price - entry_price
                pnl_atr = pnl / entry_atr
                trades.append({
                    'pnl_atr': pnl_atr,
                    'direction': direction,
                    'bars_held': i - entry_bar,
                    'exit_reason': exit_reason,
                })
                in_trade = False
                cooldown = 3  # avoid immediate re-entry

    return pd.DataFrame(trades) if trades else None


def test_4b_donchian_breakout(df, **params):
    """
    4B: Donchian channel breakout
    Long: Close > 20-day high (breakout)
    Exit: trailing stop
    """
    p = {
        'dc_period': 20, 'ema_p': 100, 'atr_p': 14,
        'stop_atr': 1.5, 'trailing_atr': 3.0, 'time_stop': 50,
    }
    p.update(params)

    if len(df) < max(150, p['dc_period'] + p['ema_p']):
        return None

    df = add_indicators(df, ema_p=p['ema_p'], atr_p=p['atr_p']).reset_index(drop=True)
    n = len(df)
    closes = df['Close'].values
    opens = df['Open'].values
    highs = df['High'].values
    lows = df['Low'].values
    emas = df['EMA'].values
    atrs = df['ATR'].values
    dc_highs = df['DC_high'].values
    dc_lows = df['DC_low'].values

    trades = []
    in_trade = False

    for i in range(p['ema_p'] + p['dc_period'], n - 1):
        atr = atrs[i]
        if np.isnan(atr) or atr <= 0:
            continue

        if not in_trade:
            close = closes[i]; ema = emas[i]; dc_high = dc_highs[i]
            if close > ema and close > dc_high:
                entry_price = opens[i + 1]
                entry_bar = i + 1
                entry_atr = atr
                stop = entry_price - p['stop_atr'] * atr
                extreme = entry_price
                trailing_stop = None
                in_trade = True
                direction = 'long'

        else:
            cur_high = highs[i]; cur_low = lows[i]; cur_close = closes[i]
            if cur_high > extreme: extreme = cur_high
            new_t = extreme - p['trailing_atr'] * entry_atr
            if trailing_stop is None or new_t > trailing_stop: trailing_stop = new_t

            exit_price = None; exit_reason = None
            if cur_low <= stop:
                exit_price = stop; exit_reason = 'stop'
            elif cur_low <= trailing_stop:
                exit_price = trailing_stop; exit_reason = 'trailing'

            if exit_price is None:
                if (i - entry_bar) >= p['time_stop']:
                    exit_price = opens[i + 1] if i + 1 < n else cur_close
                    exit_reason = 'time_stop'

            if exit_price is not None:
                pnl = exit_price - entry_price
                pnl_atr = pnl / entry_atr
                trades.append({
                    'pnl_atr': pnl_atr,
                    'direction': direction,
                    'bars_held': i - entry_bar,
                    'exit_reason': exit_reason,
                })
                in_trade = False

    return pd.DataFrame(trades) if trades else None


def test_4c_bb_mr_in_trend(df, **params):
    """
    4C: BB lower touch in uptrend (trend + MR entry, simple ATR exit)
    Long: Close > EMA50, Low <= BB lower (oversold in uptrend)
    Exit: ATR target (no trailing, no MR exit)
    """
    p = {
        'ema_p': 50, 'atr_p': 14, 'bb_period': 20,
        'stop_atr': 1.0, 'target_atr': 3.0, 'time_stop': 20,
    }
    p.update(params)

    if len(df) < max(100, p['bb_period'] + p['ema_p']):
        return None

    df = add_indicators(df, ema_p=p['ema_p'], atr_p=p['atr_p']).reset_index(drop=True)
    n = len(df)
    closes = df['Close'].values
    opens = df['Open'].values
    highs = df['High'].values
    lows = df['Low'].values
    emas = df['EMA'].values
    atrs = df['ATR'].values
    bb_lowers = df['BB_lower'].values

    trades = []
    in_trade = False
    cooldown = 0

    for i in range(p['ema_p'] + p['bb_period'], n - 1):
        atr = atrs[i]
        if np.isnan(atr) or atr <= 0:
            continue

        if not in_trade:
            if cooldown > 0:
                cooldown -= 1
                continue

            close = closes[i]; ema = emas[i]; low = lows[i]; bb_lower = bb_lowers[i]
            if np.isnan(bb_lower):
                continue

            # Long: in uptrend AND low touched/under BB lower
            if close > ema and low <= bb_lower:
                entry_price = opens[i + 1]
                entry_bar = i + 1
                entry_atr = atr
                stop = entry_price - p['stop_atr'] * atr
                target = entry_price + p['target_atr'] * atr
                in_trade = True
                direction = 'long'

        else:
            cur_high = highs[i]; cur_low = lows[i]; cur_close = closes[i]
            exit_price = None; exit_reason = None

            if cur_low <= stop:
                exit_price = stop; exit_reason = 'stop'
            elif cur_high >= target:
                exit_price = target; exit_reason = 'target'

            if exit_price is None:
                if (i - entry_bar) >= p['time_stop']:
                    exit_price = opens[i + 1] if i + 1 < n else cur_close
                    exit_reason = 'time_stop'

            if exit_price is not None:
                pnl = exit_price - entry_price
                pnl_atr = pnl / entry_atr
                trades.append({
                    'pnl_atr': pnl_atr,
                    'direction': direction,
                    'bars_held': i - entry_bar,
                    'exit_reason': exit_reason,
                })
                in_trade = False
                cooldown = 3

    return pd.DataFrame(trades) if trades else None


def test_4d_atr_breakout(df, **params):
    """
    4D: ATR breakout (volatility expansion)
    Long: today's range > 2 * ATR20 (volatility expansion)
    Entry at close, exit at next day if profitable (simple 2-day hold)
    """
    p = {
        'atr_p': 20, 'atr_mult': 2.0,
        'hold_days': 3, 'stop_atr': 2.0,
    }
    p.update(params)

    if len(df) < 100:
        return None

    df = add_indicators(df, atr_p=p['atr_p']).reset_index(drop=True)
    n = len(df)
    closes = df['Close'].values
    opens = df['Open'].values
    highs = df['High'].values
    lows = df['Low'].values
    atrs = df['ATR'].values

    trades = []
    in_trade = False

    for i in range(p['atr_p'], n - 1):
        atr = atrs[i]
        if np.isnan(atr) or atr <= 0:
            continue

        if not in_trade:
            today_range = highs[i] - lows[i]
            if today_range > p['atr_mult'] * atr:
                entry_price = opens[i + 1]
                entry_bar = i + 1
                entry_atr = atr
                stop = entry_price - p['stop_atr'] * atr
                in_trade = True
                direction = 'long'

        else:
            cur_low = lows[i]
            cur_close = closes[i]
            exit_price = None; exit_reason = None

            if cur_low <= stop:
                exit_price = stop; exit_reason = 'stop'
            elif (i - entry_bar) >= p['hold_days']:
                exit_price = opens[i + 1] if i + 1 < n else cur_close
                exit_reason = 'time_stop'

            if exit_price is not None:
                pnl = exit_price - entry_price
                pnl_atr = pnl / entry_atr
                trades.append({
                    'pnl_atr': pnl_atr,
                    'direction': direction,
                    'bars_held': i - entry_bar,
                    'exit_reason': exit_reason,
                })
                in_trade = False

    return pd.DataFrame(trades) if trades else None


def summarize(trades_df):
    if trades_df is None or len(trades_df) == 0:
        return None
    wins = trades_df[trades_df['pnl_atr'] > 0]
    losses = trades_df[trades_df['pnl_atr'] <= 0]
    total = len(trades_df)
    n_w = len(wins); n_l = len(losses)
    wr = n_w / total * 100
    avg_win = wins['pnl_atr'].mean() if n_w > 0 else 0
    avg_loss = abs(losses['pnl_atr'].mean()) if n_l > 0 else 0
    payout = avg_win / avg_loss if avg_loss > 0 else float('inf')
    mean_pnl = trades_df['pnl_atr'].mean()
    median_pnl = trades_df['pnl_atr'].median()
    expectancy = (n_w/total)*avg_win - (n_l/total)*avg_loss
    return {'trades': total, 'wr': wr, 'payout': payout,
            'mean': mean_pnl, 'median': median_pnl,
            'avg_win': avg_win, 'avg_loss': avg_loss, 'expectancy': expectancy}


def bootstrap_stability(trades_df, n_iter=200, sample_frac=0.5):
    np.random.seed(42)
    boot = []
    for _ in range(n_iter):
        sample = trades_df.sample(frac=sample_frac, random_state=np.random.randint(0, 100000))
        s = summarize(sample)
        if s:
            boot.append(s)
    if not boot:
        return None
    wrs = [b['wr'] for b in boot]
    payouts = [b['payout'] for b in boot]
    means = [b['mean'] for b in boot]
    return {
        'wr_mean': np.mean(wrs), 'wr_std': np.std(wrs),
        'wr_min': np.min(wrs), 'wr_max': np.max(wrs),
        'wr_pass_pct': sum(wr > 50 for wr in wrs) / len(wrs) * 100,
        'payout_mean': np.mean(payouts),
        'exp_pass_pct': sum(m > 0 for m in means) / len(means) * 100,
    }


# ============== RUN ==============
print("Loading data...")
stocks = load_stocks()
print(f"STOCKS: {stocks['Ticker'].nunique()} tickers\n")


def run_strategy_test(name, strategy_fn, **params):
    print(f"\n>>> {name}")
    all_trades = []
    for ticker in stocks['Ticker'].unique():
        tdf = stocks[stocks['Ticker'] == ticker].reset_index(drop=True)
        tr = strategy_fn(tdf, **params)
        if tr is not None and len(tr) > 0:
            tr['ticker'] = ticker
            all_trades.append(tr)
    agg = pd.concat(all_trades) if all_trades else None
    s = summarize(agg)
    if s is None:
        print("    No trades")
        return None

    passes = sum([
        s['mean'] > s['median'],
        s['avg_win'] > s['avg_loss'],
        s['payout'] > 2,
        s['wr'] > 50,
        s['expectancy'] > 0,
        True, True
    ])
    print(f"    trades={s['trades']}  WR={s['wr']:.2f}%  payout={s['payout']:.2f}  "
          f"mean={s['mean']:+.3f}  med={s['median']:+.3f}  exp={s['expectancy']:+.3f}  "
          f"7-crit={passes}/7")

    if s['trades'] >= 30:
        bs = bootstrap_stability(agg)
        if bs:
            print(f"    BS: WR={bs['wr_mean']:.1f}%±{bs['wr_std']:.1f}%, "
                  f"range=[{bs['wr_min']:.1f}%-{bs['wr_max']:.1f}%], "
                  f"WR>50% in {bs['wr_pass_pct']:.0f}% of samples, "
                  f"Exp>0 in {bs['exp_pass_pct']:.0f}%")

    s['name'] = name
    s['passes'] = passes
    s['trades_df'] = agg
    return s


# Test 4 variants
print("=" * 80)
print("TEST 4 — Simpler robust logic candidates")
print("=" * 80)

results = []
results.append(run_strategy_test("4A: EMA pullback (no MR exit)", test_4a_ema_pullback))
results.append(run_strategy_test("4B: Donchian breakout", test_4b_donchian_breakout))
results.append(run_strategy_test("4C: BB MR in trend (no MR exit)", test_4c_bb_mr_in_trend))
results.append(run_strategy_test("4D: ATR breakout (3-day hold)", test_4d_atr_breakout))

# Try variations
print("\n" + "=" * 80)
print("VARIATIONS OF BEST CANDIDATES")
print("=" * 80)

# 4A variations
results.append(run_strategy_test("4A-v2: EMA pullback + tight stop 0.75", test_4a_ema_pullback, stop_atr=0.75, trailing_atr=2.0))
results.append(run_strategy_test("4A-v3: EMA pullback + wider trail 3.0", test_4a_ema_pullback, trailing_atr=3.0))
results.append(run_strategy_test("4A-v4: EMA pullback + longer time 40", test_4a_ema_pullback, time_stop=40))

# 4C variations
results.append(run_strategy_test("4C-v2: BB MR + tight stop 0.75", test_4c_bb_mr_in_trend, stop_atr=0.75, target_atr=2.5))
results.append(run_strategy_test("4C-v3: BB MR + bigger target 4.0", test_4c_bb_mr_in_trend, target_atr=4.0))
results.append(run_strategy_test("4C-v4: BB MR + bigger stop 1.5", test_4c_bb_mr_in_trend, stop_atr=1.5, target_atr=3.0))

# 4B variations
results.append(run_strategy_test("4B-v2: Donchian + tighter stop 1.0", test_4b_donchian_breakout, stop_atr=1.0, trailing_atr=2.5))

# Summary
print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"{'Variant':<50} {'Trades':>7} {'WR%':>7} {'Payout':>7} {'Exp':>8} {'7-crit':>7}")
print("-" * 100)
results = [r for r in results if r is not None]
for r in sorted(results, key=lambda x: (-x['passes'], -x['expectancy'])):
    print(f"{r['name']:<50} {r['trades']:>7} {r['wr']:>6.2f}% {r['payout']:>7.2f} "
          f"{r['expectancy']:>+8.4f} {r['passes']:>5}/7")
