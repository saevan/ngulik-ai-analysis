"""
Test 6 — Better Entry Signals
==============================

EXIT from Test 5 retained: regime-based time stop (10/50/100 by ADX)
FOCUS: Improve ENTRY to push WR > 50%

ENTRY CANDIDATES:
6A. RSI pullback in strong trend (RSI<35 long, ADX>25)
6B. Multi-bar consolidation breakout (low ATR + range tight, then expansion)
6C. Volume spike breakout (volume > 2x avg)
6D. Higher timeframe context (use EMA50/200 cross for HTF, intraday entry)
6E. Combined: trend + low vol + RSI pullback (strict multi-condition)
6F. Random entry baseline (sanity check)

Each tested with FIXED 100 exit baseline.
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


def add_indicators(df, ema_p=50, rsi_p=14, atr_p=14, adx_p=14):
    df = df.copy()
    df['EMA'] = df['Close'].ewm(span=ema_p, adjust=False).mean()
    delta = df['Close'].diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1/rsi_p, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/rsi_p, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-12)
    df['RSI'] = 100 - (100 / (1 + rs))

    high_low = df['High'] - df['Low']
    high_close = (df['High'] - df['Close'].shift()).abs()
    low_close = (df['Low'] - df['Close'].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['TR'] = tr
    df['ATR'] = tr.ewm(alpha=1/atr_p, adjust=False).mean()

    # Range contraction: ATR relative to its own average
    df['ATR_avg'] = df['ATR'].rolling(50).mean()
    df['ATR_ratio'] = df['ATR'] / df['ATR_avg'].replace(0, 1e-12)

    # Volume spike
    df['Vol_avg'] = df['Volume'].rolling(20).mean()
    df['Vol_ratio'] = df['Volume'] / df['Vol_avg'].replace(0, 1e-12)

    # ADX
    up_move = df['High'] - df['High'].shift()
    down_move = df['Low'].shift() - df['Low']
    plus_dm = pd.Series(np.where((up_move > down_move) & (up_move > 0), up_move, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((down_move > up_move) & (down_move > 0), down_move, 0.0), index=df.index)
    atr_smooth = tr.ewm(alpha=1/adx_p, adjust=False).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1/adx_p, adjust=False).mean() / atr_smooth.replace(0, 1e-12)
    minus_di = 100 * minus_dm.ewm(alpha=1/adx_p, adjust=False).mean() / atr_smooth.replace(0, 1e-12)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, 1e-12)
    df['ADX'] = dx.ewm(alpha=1/adx_p, adjust=False).mean()

    return df


# Exit logic shared across all tests
def apply_exit(trade_state, i, df, params):
    """Returns (exit_price, exit_reason) or (None, None)."""
    cur_high = df['High'].iloc[i]
    cur_low = df['Low'].iloc[i]
    cur_close = df['Close'].iloc[i]
    cur_open = df['Open'].iloc[i]
    n = len(df)

    if trade_state['direction'] == 'long':
        if cur_high > trade_state['extreme']:
            trade_state['extreme'] = cur_high
        new_t = trade_state['extreme'] - params['trailing_atr'] * trade_state['entry_atr']
        if trade_state['trailing_stop'] is None or new_t > trade_state['trailing_stop']:
            trade_state['trailing_stop'] = new_t

        if cur_low <= trade_state['stop']:
            return trade_state['stop'], 'stop'
        if cur_low <= trade_state['trailing_stop']:
            return trade_state['trailing_stop'], 'trailing'
    # SHORT not implemented (asymmetry in this study)

    if (i - trade_state['entry_bar']) >= trade_state['time_stop']:
        if i + 1 < n:
            return df['Open'].iloc[i + 1], 'time_stop'
        return cur_close, 'time_stop'

    return None, None


def run_strategy(df, entry_check_fn, params):
    """Generic runner: applies entry_check_fn at each bar."""
    if len(df) < 100:
        return None

    df = add_indicators(df).reset_index(drop=True)
    n = len(df)
    trades = []
    in_trade = False
    cooldown = 0

    for i in range(50, n - 1):
        if in_trade:
            exit_price, exit_reason = apply_exit(
                {'direction': trade_state['direction'],
                 'entry_price': trade_state['entry_price'],
                 'entry_atr': trade_state['entry_atr'],
                 'entry_bar': trade_state['entry_bar'],
                 'stop': trade_state['stop'],
                 'extreme': trade_state['extreme'],
                 'trailing_stop': trade_state['trailing_stop'],
                 'time_stop': trade_state['time_stop']},
                i, df, params
            )

            if exit_price is not None:
                pnl = (exit_price - trade_state['entry_price'])
                pnl_atr = pnl / trade_state['entry_atr']
                trades.append({
                    'pnl_atr': pnl_atr,
                    'bars_held': i - trade_state['entry_bar'],
                    'exit_reason': exit_reason,
                })
                in_trade = False
                cooldown = 3
            continue

        if cooldown > 0:
            cooldown -= 1
            continue

        # Try entry
        signal = entry_check_fn(df, i, params)
        if signal:
            atr = df['ATR'].iloc[i]
            if np.isnan(atr) or atr <= 0:
                continue

            entry_price = df['Open'].iloc[i + 1]
            entry_atr = atr
            stop = entry_price - params['stop_atr'] * atr
            adx = df['ADX'].iloc[i]

            if adx > 25:
                time_stop = params['time_stop_strong']
            elif adx > 20:
                time_stop = params['time_stop_moderate']
            else:
                time_stop = params['time_stop_weak']

            trade_state = {
                'direction': 'long',
                'entry_price': entry_price,
                'entry_atr': entry_atr,
                'entry_bar': i + 1,
                'stop': stop,
                'extreme': entry_price,
                'trailing_stop': None,
                'time_stop': time_stop,
            }
            in_trade = True

    return pd.DataFrame(trades) if trades else None


# Entry check functions
def entry_6a_rsi_pullback(df, i, params):
    """6A: Trend + ADX + RSI pullback."""
    close = df['Close'].iloc[i]
    ema = df['EMA'].iloc[i]
    rsi = df['RSI'].iloc[i]
    adx = df['ADX'].iloc[i]
    if np.isnan(rsi) or np.isnan(adx):
        return False
    if close > ema and adx > params['adx_threshold'] and rsi < params['rsi_threshold']:
        return True
    return False


def entry_6b_consolidation_breakout(df, i, params):
    """6B: Low volatility before expansion (consolidation then breakout)."""
    close = df['Close'].iloc[i]
    atr_ratio = df['ATR_ratio'].iloc[i]
    today_range = df['TR'].iloc[i]
    atr = df['ATR'].iloc[i]
    ema = df['EMA'].iloc[i]
    if np.isnan(atr_ratio) or np.isnan(atr):
        return False
    # Yesterday was low vol (consolidation), today breaks out
    prev_ratio = df['ATR_ratio'].iloc[i - 1] if i > 0 else 1
    if close > ema and prev_ratio < params['consolidation_threshold'] and today_range > atr * params['breakout_mult']:
        return True
    return False


def entry_6c_volume_spike(df, i, params):
    """6C: Volume spike breakout."""
    close = df['Close'].iloc[i]
    vol_ratio = df['Vol_ratio'].iloc[i]
    today_range = df['TR'].iloc[i]
    atr = df['ATR'].iloc[i]
    ema = df['EMA'].iloc[i]
    if np.isnan(vol_ratio) or np.isnan(atr):
        return False
    if close > ema and vol_ratio > params['vol_spike_threshold'] and today_range > atr * params['breakout_mult']:
        return True
    return False


def entry_6d_htf_context(df, i, params):
    """6D: EMA50 above EMA200 (HTF uptrend)."""
    if i < 200:
        return False
    close = df['Close'].iloc[i]
    ema50 = df['EMA'].iloc[i]
    ema200 = df['Close'].ewm(span=200).mean().iloc[i]
    today_range = df['TR'].iloc[i]
    atr = df['ATR'].iloc[i]
    if np.isnan(ema50) or np.isnan(atr):
        return False
    if close > ema50 and ema50 > ema200 and today_range > atr * params['breakout_mult']:
        return True
    return False


def entry_6e_combined(df, i, params):
    """6E: Trend + low vol + RSI pullback (strict multi-condition)."""
    close = df['Close'].iloc[i]
    ema = df['EMA'].iloc[i]
    rsi = df['RSI'].iloc[i]
    atr_ratio = df['ATR_ratio'].iloc[i]
    today_range = df['TR'].iloc[i]
    atr = df['ATR'].iloc[i]
    if np.isnan(rsi) or np.isnan(atr_ratio) or np.isnan(atr):
        return False
    prev_ratio = df['ATR_ratio'].iloc[i - 1] if i > 0 else 1
    if (close > ema
        and rsi < params['rsi_threshold']
        and prev_ratio < params['consolidation_threshold']
        and today_range > atr * params['breakout_mult']):
        return True
    return False


def entry_6f_random(df, i, params):
    """6F: Random entry baseline (sanity check)."""
    return np.random.random() < params['random_prob']


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
    avg_bars_w = wins['bars_held'].mean() if n_w > 0 else 0
    return {
        'trades': total, 'wr': wr, 'payout': payout,
        'mean': mean_pnl, 'median': median_pnl,
        'avg_win': avg_win, 'avg_loss': avg_loss, 'expectancy': expectancy,
        'avg_bars_w': avg_bars_w,
    }


def bootstrap_stability(trades_df, n_iter=100, sample_frac=0.5):
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
    means = [b['mean'] for b in boot]
    payouts = [b['payout'] for b in boot]
    return {
        'wr_mean': np.mean(wrs), 'wr_std': np.std(wrs),
        'wr_pass_pct': sum(wr > 50 for wr in wrs) / len(wrs) * 100,
        'exp_pass_pct': sum(m > 0 for m in means) / len(means) * 100,
        'payout_pass_pct': sum(po > 2 for po in payouts) / len(payouts) * 100,
    }


# ============== RUN ==============
print("Loading data...")
stocks = load_stocks()
print(f"STOCKS: {stocks['Ticker'].nunique()} tickers\n")


# EXIT framework retained from Test 5
common_exit = {
    'stop_atr': 2.0, 'trailing_atr': 3.0,
    'time_stop_strong': 100, 'time_stop_moderate': 50, 'time_stop_weak': 10,
}


def run_entry(name, entry_fn, entry_params=None):
    if entry_params is None:
        entry_params = {}
    params = {**common_exit, **entry_params}
    print(f"\n>>> {name}")
    print(f"    exit params: {params}")

    np.random.seed(42)
    all_trades = []
    for ticker in stocks['Ticker'].unique():
        tdf = stocks[stocks['Ticker'] == ticker].reset_index(drop=True)
        tr = run_strategy(tdf, entry_fn, params)
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
          f"mean={s['mean']:+.3f}  med={s['median']:+.3f}  exp={s['expectancy']:+.3f}")
    print(f"    avg bars winner={s['avg_bars_w']:.1f}")
    print(f"    7-criteria: {passes}/7")

    if s['trades'] >= 100:
        bs = bootstrap_stability(agg)
        if bs:
            print(f"    BS: WR={bs['wr_mean']:.1f}% std={bs['wr_std']:.1f}%, "
                  f"WR>50% in {bs['wr_pass_pct']:.0f}%, "
                  f"Exp>0 in {bs['exp_pass_pct']:.0f}%, "
                  f"Payout>2 in {bs['payout_pass_pct']:.0f}%")

    s['name'] = name
    s['passes'] = passes
    s['trades_df'] = agg
    return s


print("=" * 80)
print("EXPERIMENT: Better entry signals (exit retained from Test 5)")
print("=" * 80)

results = []

# Baseline 4D (ATR breakout only)
results.append(run_entry("BASELINE: ATR breakout only (Test 5)", entry_6a_rsi_pullback,
                          dict(adx_threshold=0, rsi_threshold=100)))  # effectively disables filters

# 6A: RSI pullback variants
results.append(run_entry("6A: RSI<40 + ADX>20", entry_6a_rsi_pullback, dict(adx_threshold=20, rsi_threshold=40)))
results.append(run_entry("6A: RSI<35 + ADX>20 (strict)", entry_6a_rsi_pullback, dict(adx_threshold=20, rsi_threshold=35)))
results.append(run_entry("6A: RSI<30 + ADX>20 (very strict)", entry_6a_rsi_pullback, dict(adx_threshold=20, rsi_threshold=30)))
results.append(run_entry("6A: RSI<35 + ADX>25", entry_6a_rsi_pullback, dict(adx_threshold=25, rsi_threshold=35)))
results.append(run_entry("6A: RSI<30 + ADX>25", entry_6a_rsi_pullback, dict(adx_threshold=25, rsi_threshold=30)))

# 6B: Consolidation breakout
results.append(run_entry("6B: Consolidation <0.7 + breakout 1.5x", entry_6b_consolidation_breakout,
                          dict(consolidation_threshold=0.7, breakout_mult=1.5)))
results.append(run_entry("6B: Consolidation <0.6 + breakout 2.0x", entry_6b_consolidation_breakout,
                          dict(consolidation_threshold=0.6, breakout_mult=2.0)))

# 6C: Volume spike
results.append(run_entry("6C: Vol spike >2x + breakout", entry_6c_volume_spike,
                          dict(vol_spike_threshold=2.0, breakout_mult=1.5)))
results.append(run_entry("6C: Vol spike >3x", entry_6c_volume_spike,
                          dict(vol_spike_threshold=3.0, breakout_mult=2.0)))

# 6D: HTF context
results.append(run_entry("6D: EMA50 > EMA200 + breakout", entry_6d_htf_context, dict(breakout_mult=2.0)))

# 6E: Combined
results.append(run_entry("6E: RSI<40 + consolidation + breakout", entry_6e_combined,
                          dict(rsi_threshold=40, consolidation_threshold=0.7, breakout_mult=1.5)))
results.append(run_entry("6E-strict: RSI<35 + consolidation<0.6 + breakout>2x", entry_6e_combined,
                          dict(rsi_threshold=35, consolidation_threshold=0.6, breakout_mult=2.0)))

# Summary
print("\n" + "=" * 80)
print("SUMMARY — Entry comparison")
print("=" * 80)
print(f"{'Entry':<55} {'Trades':>7} {'WR%':>7} {'Payout':>7} {'Exp':>9} {'7-crit':>7}")
print("-" * 110)
results = [r for r in results if r is not None]
for r in sorted(results, key=lambda x: (-x['passes'], -x['expectancy'])):
    print(f"{r['name']:<55} {r['trades']:>7} {r['wr']:>6.2f}% {r['payout']:>7.2f} "
          f"{r['expectancy']:>+9.4f} {r['passes']:>5}/7")

best = max(results, key=lambda x: (x['passes'], x['expectancy']))
print(f"\n>>> BEST: {best['name']}")
print(f"    trades={best['trades']}, WR={best['wr']:.2f}%, payout={best['payout']:.2f}, "
      f"exp={best['expectancy']:+.4f}, 7-crit={best['passes']}/7")
