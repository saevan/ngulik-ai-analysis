"""
Test user's hypothesis: "Sama logic dengan indikator lebih kecil = hasil WR/payout sama,
tapi trade count naik. Kalau logic benar, shrinking = bootstrap stabil."

Approach: Scale down ALL indicator periods proportionally:
- Baseline: EMA(50), ADX(14), RSI(14), ATR(14), time_stop=25
- Shrunken A: EMA(25), ADX(7), RSI(7), ATR(7), time_stop=12
- Shrunken B: EMA(10), ADX(4), RSI(4), ATR(4), time_stop=5

If user's hypothesis TRUE:
- WR/payout/expectancy should be similar
- Trade count should jump massively
- Bootstrap stability test should be MORE robust (more trades = less variance)

If hypothesis FALSE:
- Either WR drops (logic only works at certain period scale)
- Or payout drops (MR exit only fires at certain volatility)
- Or results still fragile (logic has structural issue)
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
    df['ATR'] = tr.ewm(alpha=1/atr_p, adjust=False).mean()
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


def run_test3(df, **params):
    p = {
        'ema_p': 50, 'adx_threshold': 20,
        'rsi_entry_long': 35, 'rsi_entry_short': 65,
        'rsi_exit_long': 70, 'rsi_exit_short': 30,
        'stop_atr': 0.75, 'trailing_atr': 2.0, 'time_stop': 25,
    }
    p.update(params)

    if len(df) < 100:
        return None

    df = add_indicators(df, ema_p=p['ema_p'], rsi_p=14, atr_p=14, adx_p=14).reset_index(drop=True)
    n = len(df)
    closes = df['Close'].values
    opens = df['Open'].values
    highs = df['High'].values
    lows = df['Low'].values
    emas = df['EMA'].values
    adxs = df['ADX'].values
    rsis = df['RSI'].values
    atrs = df['ATR'].values

    trades = []
    in_trade = False

    for i in range(max(p['ema_p'], 50), n - 1):
        if not in_trade:
            atr = atrs[i]
            if np.isnan(atr) or atr <= 0:
                continue

            adx = adxs[i]; ema = emas[i]; rsi = rsis[i]; close = closes[i]
            if adx <= p['adx_threshold']:
                continue

            signal = None
            if close > ema and rsi < p['rsi_entry_long']:
                signal = 'long'
            elif close < ema and rsi > p['rsi_entry_short']:
                signal = 'short'

            if signal:
                entry_price = opens[i + 1]
                entry_bar = i + 1
                entry_atr = atr
                if signal == 'long':
                    stop = entry_price - p['stop_atr'] * atr
                    rsi_exit = p['rsi_exit_long']
                else:
                    stop = entry_price + p['stop_atr'] * atr
                    rsi_exit = p['rsi_exit_short']
                extreme = entry_price
                trailing_stop = None
                in_trade = True
                direction = signal

        else:
            cur_high = highs[i]; cur_low = lows[i]; cur_close = closes[i]
            cur_rsi = rsis[i]
            exit_price = None; exit_reason = None

            if direction == 'long':
                if cur_high > extreme: extreme = cur_high
                new_t = extreme - p['trailing_atr'] * entry_atr
                if trailing_stop is None or new_t > trailing_stop: trailing_stop = new_t
            else:
                if cur_low < extreme: extreme = cur_low
                new_t = extreme + p['trailing_atr'] * entry_atr
                if trailing_stop is None or new_t < trailing_stop: trailing_stop = new_t

            if direction == 'long':
                if cur_low <= stop: exit_price, exit_reason = stop, 'stop'
                elif cur_rsi >= rsi_exit:
                    exit_price = opens[i + 1] if i + 1 < n else cur_close
                    exit_reason = 'rsi_exit'
                elif cur_low <= trailing_stop: exit_price, exit_reason = trailing_stop, 'trailing'
            else:
                if cur_high >= stop: exit_price, exit_reason = stop, 'stop'
                elif cur_rsi <= rsi_exit:
                    exit_price = opens[i + 1] if i + 1 < n else cur_close
                    exit_reason = 'rsi_exit'
                elif cur_high >= trailing_stop: exit_price, exit_reason = trailing_stop, 'trailing'

            if exit_price is None:
                if (i - entry_bar) >= p['time_stop']:
                    exit_price = opens[i + 1] if i + 1 < n else cur_close
                    exit_reason = 'time_stop'

            if exit_price is not None:
                pnl = (exit_price - entry_price) if direction == 'long' else (entry_price - exit_price)
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
    return {
        'wr_mean': np.mean(wrs),
        'wr_std': np.std(wrs),
        'wr_min': np.min(wrs),
        'wr_max': np.max(wrs),
        'wr_pass_pct': sum(wr > 50 for wr in wrs) / len(wrs) * 100,
    }


# ============== RUN ==============
print("Loading data...")
stocks = load_stocks()
print(f"STOCKS: {stocks['Ticker'].nunique()} tickers\n")

# === Parameter sets: scale down progressively ===
# Same LOGIC (TF base + MR entry + MR exit + trailing), only scale periods

variants = [
    ("BASELINE: EMA50/RSI14/ADX14, ts=25", dict(ema_p=50, time_stop=25)),
    ("Scale 0.75: EMA37/RSI10/ADX10, ts=19", dict(ema_p=37, time_stop=19)),
    ("Scale 0.50: EMA25/RSI7/ADX7, ts=12", dict(ema_p=25, time_stop=12)),
    ("Scale 0.25: EMA12/RSI4/ADX4, ts=6", dict(ema_p=12, time_stop=6)),
    ("Scale 0.20: EMA10/RSI3/ADX3, ts=5", dict(ema_p=10, time_stop=5)),
]


print("=" * 100)
print("EXPERIMENT: SHRINK INDICATOR PERIODS — Test user's claim")
print("=" * 100)
print(f"{'Variant':<40} {'Trades':>8} {'WR%':>7} {'Payout':>8} {'Mean':>8} {'Exp':>8} {'7-crit':>8}")
print("-" * 100)

results = []
for label, params in variants:
    all_trades = []
    for ticker in stocks['Ticker'].unique():
        tdf = stocks[stocks['Ticker'] == ticker].reset_index(drop=True)
        tr = run_test3(tdf, **params)
        if tr is not None and len(tr) > 0:
            tr['ticker'] = ticker
            all_trades.append(tr)
    agg = pd.concat(all_trades) if all_trades else None
    s = summarize(agg)
    if s is None:
        print(f"{label:<40} No trades")
        continue

    passes = sum([
        s['mean'] > s['median'],
        s['avg_win'] > s['avg_loss'],
        s['payout'] > 2,
        s['wr'] > 50,
        s['expectancy'] > 0,
        True, True
    ])
    s['name'] = label
    s['passes'] = passes
    s['trades_df'] = agg
    results.append(s)

    print(f"{label:<40} {s['trades']:>8} {s['wr']:>6.2f}% {s['payout']:>8.2f} "
          f"{s['mean']:>+8.4f} {s['expectancy']:>+8.4f} {passes:>5}/7")


# === Bootstrap stability check ===
print("\n" + "=" * 100)
print("BOOTSTRAP STABILITY — Does shrinking make the result ROBUST?")
print("=" * 100)

print(f"\n{'Variant':<40} {'WR mean':>8} {'WR std':>8} {'WR range':>12} {'% WR>50%':>10}")
print("-" * 90)

for s in results:
    if s['trades'] < 5:
        print(f"{s['name']:<40} (insufficient trades for bootstrap)")
        continue
    bs = bootstrap_stability(s['trades_df'], n_iter=200, sample_frac=0.5)
    if bs:
        wr_pass_str = f"{bs['wr_pass_pct']:.1f}%"
        wr_range = f"[{bs['wr_min']:.1f}% - {bs['wr_max']:.1f}%]"
        print(f"{s['name']:<40} {bs['wr_mean']:>7.2f}% {bs['wr_std']:>7.2f}%  {wr_range:>12} {wr_pass_str:>10}")


# === Find best: most trades + 7/7 pass + stable bootstrap ===
print("\n" + "=" * 100)
print("RANKING: Best by 7-criteria + bootstrap stability + trade count")
print("=" * 100)

for s in sorted(results, key=lambda x: (-x['passes'], x['trades']), reverse=True):
    bs = bootstrap_stability(s['trades_df']) if s['trades'] >= 5 else None
    bs_score = (bs['wr_pass_pct'] if bs else 0)
    bs_std = (bs['wr_std'] if bs else 99)
    print(f"  {s['name']}: 7-crit={s['passes']}/7, trades={s['trades']}, "
          f"WR={s['wr']:.2f}%, BS pass={bs_score:.0f}%, BS std={bs_std:.2f}")


# === Hypothesis verification ===
print("\n" + "=" * 100)
print("VERDICT — Does user's claim hold?")
print("=" * 100)

baseline = results[0]
scaled = results[1:]

print(f"\nBaseline: {baseline['trades']} trades, WR={baseline['wr']:.2f}%, payout={baseline['payout']:.2f}")
print(f"Shrunk variants:")
for s in scaled:
    ratio = s['trades'] / baseline['trades']
    wr_diff = s['wr'] - baseline['wr']
    payout_diff = s['payout'] - baseline['payout']
    print(f"  {s['name']}: trades x{ratio:.1f} ({s['trades']}), "
          f"WR Δ{wr_diff:+.2f}, payout Δ{payout_diff:+.2f}")

# Pass criteria for hypothesis
# If shrunk: trades >> baseline, WR within ±5, payout within ±30%, ALL maintain 7-criteria or close
hypothesis_supports = []
for s in scaled:
    wr_stable = abs(s['wr'] - baseline['wr']) < 10
    payout_stable = abs(s['payout'] - baseline['payout']) / max(baseline['payout'], 1) < 0.5
    more_trades = s['trades'] > baseline['trades'] * 1.5
    hypothesis_supports.append({
        'name': s['name'],
        'wr_stable': wr_stable,
        'payout_stable': payout_stable,
        'more_trades': more_trades,
        'maintain_7': s['passes'] >= 5,
    })

print(f"\nHypothesis check:")
for h in hypothesis_supports:
    print(f"  {h['name']}: WR_stable={h['wr_stable']}, payout_stable={h['payout_stable']}, "
          f"more_trades={h['more_trades']}, 7-crit_ok={h['maintain_7']}")
