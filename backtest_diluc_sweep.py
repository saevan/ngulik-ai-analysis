"""
DILUC Parameter Sweep — find best variant empirically
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


def add_indicators(df):
    df = df.copy()
    df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()

    delta = df['Close'].diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-12)
    df['RSI'] = 100 - (100 / (1 + rs))

    high_low = df['High'] - df['Low']
    high_close = (df['High'] - df['Close'].shift()).abs()
    low_close = (df['Low'] - df['Close'].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['ATR'] = tr.ewm(alpha=1/14, adjust=False).mean()

    up_move = df['High'] - df['High'].shift()
    down_move = df['Low'].shift() - df['Low']
    plus_dm = pd.Series(np.where((up_move > down_move) & (up_move > 0), up_move, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((down_move > up_move) & (down_move > 0), down_move, 0.0), index=df.index)

    atr_smooth = tr.ewm(alpha=1/14, adjust=False).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1/14, adjust=False).mean() / atr_smooth.replace(0, 1e-12)
    minus_di = 100 * minus_dm.ewm(alpha=1/14, adjust=False).mean() / atr_smooth.replace(0, 1e-12)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, 1e-12)
    df['ADX'] = dx.ewm(alpha=1/14, adjust=False).mean()

    return df


def run_diluc(df, **params):
    """Diluc backtest with full parameter control."""
    p = {
        'adx_dawn': 25, 'adx_default': 20,
        'rsi_dawn_long': 40, 'rsi_dawn_short': 60,
        'rsi_default_long': 35, 'rsi_default_short': 65,
        'default_stop_atr': 1.0, 'default_target_atr': 2.0, 'default_time_stop': 10,
        'dawn_stop_atr': 1.5, 'dawn_partial_atr': 2.0, 'dawn_trailing_atr': 2.0, 'dawn_time_stop': 30,
    }
    p.update(params)

    if len(df) < 100:
        return None

    df = add_indicators(df).reset_index(drop=True)
    n = len(df)
    closes = df['Close'].values
    opens = df['Open'].values
    highs = df['High'].values
    lows = df['Low'].values
    emas = df['EMA50'].values
    adxs = df['ADX'].values
    rsis = df['RSI'].values
    atrs = df['ATR'].values

    trades = []
    in_trade = False

    for i in range(50, n - 1):
        if not in_trade:
            atr = atrs[i]
            if np.isnan(atr) or atr <= 0:
                continue

            adx = adxs[i]; ema = emas[i]; rsi = rsis[i]; close = closes[i]
            signal = None; chosen_mode = None

            if adx > p['adx_dawn']:
                if close > ema and rsi < p['rsi_dawn_long']:
                    signal = 'long'; chosen_mode = 'dawn'
                elif close < ema and rsi > p['rsi_dawn_short']:
                    signal = 'short'; chosen_mode = 'dawn'
            elif adx < p['adx_default']:
                if close > ema and rsi < p['rsi_default_long']:
                    signal = 'long'; chosen_mode = 'default'
                elif close < ema and rsi > p['rsi_default_short']:
                    signal = 'short'; chosen_mode = 'default'

            if signal:
                entry_price = opens[i + 1]
                entry_bar = i + 1
                entry_atr = atr

                if chosen_mode == 'default':
                    if signal == 'long':
                        stop = entry_price - p['default_stop_atr'] * atr
                        target = entry_price + p['default_target_atr'] * atr
                    else:
                        stop = entry_price + p['default_stop_atr'] * atr
                        target = entry_price - p['default_target_atr'] * atr
                    time_stop_bars = p['default_time_stop']
                    partial_taken = False
                else:
                    if signal == 'long':
                        stop = entry_price - p['dawn_stop_atr'] * atr
                        target1 = entry_price + p['dawn_partial_atr'] * atr
                    else:
                        stop = entry_price + p['dawn_stop_atr'] * atr
                        target1 = entry_price - p['dawn_partial_atr'] * atr
                    time_stop_bars = p['dawn_time_stop']
                    partial_taken = False
                    trailing_stop = None
                    extreme = entry_price

                in_trade = True
                direction = signal
                mode = chosen_mode

        else:
            cur_high = highs[i]; cur_low = lows[i]; cur_close = closes[i]
            exit_price = None; exit_reason = None

            if mode == 'default':
                if direction == 'long':
                    if cur_low <= stop: exit_price, exit_reason = stop, 'stop'
                    elif cur_high >= target: exit_price, exit_reason = target, 'target'
                else:
                    if cur_high >= stop: exit_price, exit_reason = stop, 'stop'
                    elif cur_low <= target: exit_price, exit_reason = target, 'target'

                if exit_price is None:
                    if (i - entry_bar) >= p['default_time_stop']:
                        exit_price = opens[i + 1] if i + 1 < n else cur_close
                        exit_reason = 'time_stop'
            else:
                if direction == 'long':
                    if cur_high > extreme: extreme = cur_high
                else:
                    if cur_low < extreme: extreme = cur_low

                if direction == 'long':
                    if not partial_taken:
                        if cur_low <= stop: exit_price, exit_reason = stop, 'stop'
                        elif cur_high >= target1:
                            partial_taken = True
                            trailing_stop = target1 - p['dawn_trailing_atr'] * entry_atr
                    else:
                        new_t = extreme - p['dawn_trailing_atr'] * entry_atr
                        if new_t > trailing_stop: trailing_stop = new_t
                        if cur_low <= trailing_stop: exit_price, exit_reason = trailing_stop, 'trailing'
                else:
                    if not partial_taken:
                        if cur_high >= stop: exit_price, exit_reason = stop, 'stop'
                        elif cur_low <= target1:
                            partial_taken = True
                            trailing_stop = target1 + p['dawn_trailing_atr'] * entry_atr
                    else:
                        new_t = extreme + p['dawn_trailing_atr'] * entry_atr
                        if new_t < trailing_stop: trailing_stop = new_t
                        if cur_high >= trailing_stop: exit_price, exit_reason = trailing_stop, 'trailing'

                if exit_price is None:
                    if (i - entry_bar) >= p['dawn_time_stop']:
                        exit_price = opens[i + 1] if i + 1 < n else cur_close
                        exit_reason = 'time_stop'

            if exit_price is not None:
                if mode == 'dawn' and partial_taken:
                    if direction == 'long':
                        pnl = 0.5 * (target1 - entry_price) + 0.5 * (exit_price - entry_price)
                    else:
                        pnl = 0.5 * (entry_price - target1) + 0.5 * (entry_price - exit_price)
                else:
                    pnl = (exit_price - entry_price) if direction == 'long' else (entry_price - exit_price)

                pnl_atr = pnl / entry_atr
                trades.append({
                    'pnl_atr': pnl_atr,
                    'direction': direction,
                    'mode': mode,
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
    n_def = (trades_df['mode'] == 'default').sum()
    n_dawn = (trades_df['mode'] == 'dawn').sum()

    return {
        'trades': total, 'wr': wr, 'payout': payout,
        'mean': mean_pnl, 'median': median_pnl,
        'avg_win': avg_win, 'avg_loss': avg_loss,
        'expectancy': expectancy,
        'n_default': n_def, 'n_dawn': n_dawn,
    }


# ============== RUN SWEEP ==============
print("Loading stocks data...")
stocks = load_stocks()
print(f"STOCKS: {stocks['Ticker'].nunique()} tickers, {len(stocks):,} rows")

# Pre-aggregate all trades per ticker for speed
print("\nPre-aggregating per ticker...")
all_tickers = stocks['Ticker'].unique()


def run_variant(label, params):
    print(f"\n>>> [{label}]")
    print(f"    params: {params}")
    all_trades = []
    for ticker in all_tickers:
        tdf = stocks[stocks['Ticker'] == ticker].reset_index(drop=True)
        trades = run_diluc(tdf, **params)
        if trades is not None and len(trades) > 0:
            all_trades.append(trades)
    agg = pd.concat(all_trades) if all_trades else None
    s = summarize(agg)
    if s is None:
        print("    No trades.")
        return s, label
    print(f"    trades={s['trades']} (def={s['n_default']}, dawn={s['n_dawn']})  "
          f"WR={s['wr']:.1f}%  payout={s['payout']:.2f}  "
          f"mean={s['mean']:+.3f}  med={s['median']:+.3f}  exp={s['expectancy']:+.3f}")
    # 7-criteria quick check
    passes = []
    passes.append(('1.M>M', s['mean'] > s['median']))
    passes.append(('2.W>L', s['avg_win'] > s['avg_loss']))
    passes.append(('3.P>2', s['payout'] > 2))
    passes.append(('4.WR>50', s['wr'] > 50))
    passes.append(('5.Exp>0', s['expectancy'] > 0))
    passes.append(('6.Uni', True))
    passes.append(('7.O(i+1)', True))
    score = sum(1 for _, ok in passes if ok)
    print(f"    7-criteria: {score}/7  -> " + " ".join(f"{n}:{'Y' if ok else 'N'}" for n, ok in passes))
    return s, label


# Baseline (original Diluc)
baseline = {}

# Variation A: Loosen DEFAULT trigger (ADX<25)
v_a = dict(adx_default=25)

# Variation B: Wider DAWN trailing (3.0)
v_b = dict(dawn_trailing_atr=3.0)

# Variation C: A + B
v_c = dict(adx_default=25, dawn_trailing_atr=3.0)

# Variation D: Tighter DAWN stop (1.0) for better R:R
v_d = dict(dawn_stop_atr=1.0)

# Variation E: A + D
v_e = dict(adx_default=25, dawn_stop_atr=1.0)

# Variation F: A + B + D (loose DEFAULT + wide trailing + tight DAWN stop)
v_f = dict(adx_default=25, dawn_trailing_atr=3.0, dawn_stop_atr=1.0)

# Variation G: even looser DEFAULT + larger partial TP for DAWN
v_g = dict(adx_default=25, dawn_partial_atr=2.5, dawn_trailing_atr=2.5)

# Variation H: DEFAULT trigger <25, looser RSI for both (catches more signals)
v_h = dict(adx_default=25, rsi_default_long=40, rsi_default_short=60,
           rsi_dawn_long=42, rsi_dawn_short=58)

# Variation I: Even looser DEFAULT ADX (30) — definitely catches ranging
v_i = dict(adx_default=30, rsi_default_long=40, rsi_default_short=60)

# Variation J: ADXdef<30 + DAWN stop=1.0 (combine)
v_j = dict(adx_default=30, rsi_default_long=40, rsi_default_short=60, dawn_stop_atr=1.0)

# Variation K: ADXdef<30 + DAWN stop=1.0 + trail=2.5 (best of both)
v_k = dict(adx_default=30, rsi_default_long=40, rsi_default_short=60,
           dawn_stop_atr=1.0, dawn_trailing_atr=2.5)

# Variation L: Try with F params but RSI looser for more trades
v_l = dict(adx_default=25, dawn_trailing_atr=3.0, dawn_stop_atr=1.0,
           rsi_default_long=40, rsi_default_short=60,
           rsi_dawn_long=42, rsi_dawn_short=58)

# Variation M: AGGRESSIVE DEFAULT — wider ADX, tighter stop, keep target 2.0
v_m = dict(adx_default=30, rsi_default_long=40, rsi_default_short=60,
           default_stop_atr=0.5, default_target_atr=2.0)

# Variation N: Very loose DEFAULT — catch every ranging market
v_n = dict(adx_default=35, rsi_default_long=40, rsi_default_short=60,
           default_stop_atr=0.5, default_target_atr=2.0,
           dawn_stop_atr=1.0)

# Variation O: DEFAULT always-on (no regime filter for DEFAULT)
# Default trigger is just Close > EMA + RSI<40 (DAWN-only filtering)
v_o = dict(adx_default=40, rsi_default_long=40, rsi_default_short=60,
           default_stop_atr=0.5, default_target_atr=2.0,
           dawn_stop_atr=1.0)

variants = [
    ("Baseline", baseline),
    ("F: A+B+D", v_f),
    ("L: F + loose RSI", v_l),
    ("M: AGGR default", v_m),
    ("N: VERY loose default", v_n),
    ("O: DEFAULT always-on", v_o),
]

results = []
for label, params in variants:
    s, name = run_variant(label, params)
    if s is not None:
        s['name'] = name
        results.append(s)


# Print comparison summary
print("\n\n" + "=" * 80)
print("COMPARISON SUMMARY")
print("=" * 80)
print(f"{'Variant':<35} {'Trades':>7} {'WR%':>6} {'Payout':>7} {'Mean':>8} {'Median':>8} {'Exp':>8} {'7-crit':>7}")
print("-" * 80)
for s in results:
    passes = sum([s['mean'] > s['median'], s['avg_win'] > s['avg_loss'],
                  s['payout'] > 2, s['wr'] > 50, s['expectancy'] > 0, True, True])
    print(f"{s['name']:<35} {s['trades']:>7} {s['wr']:>6.1f} {s['payout']:>7.2f} "
          f"{s['mean']:>+8.4f} {s['median']:>+8.4f} {s['expectancy']:>+8.4f} {passes:>5}/7")

# Find best by 7-criteria score, then by expectancy
print("\n--- Ranking by 7-criteria score, then expectancy ---")
results_sorted = sorted(results, key=lambda x: (
    sum([x['mean'] > x['median'], x['avg_win'] > x['avg_loss'],
         x['payout'] > 2, x['wr'] > 50, x['expectancy'] > 0, True, True]),
    x['expectancy']
), reverse=True)

for s in results_sorted[:5]:
    passes = sum([s['mean'] > s['median'], s['avg_win'] > s['avg_loss'],
                  s['payout'] > 2, s['wr'] > 50, s['expectancy'] > 0, True, True])
    print(f"  {s['name']}: 7-crit={passes}/7, exp={s['expectancy']:+.4f}, "
          f"WR={s['wr']:.1f}%, payout={s['payout']:.2f}, trades={s['trades']}")
