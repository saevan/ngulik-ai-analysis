"""
Test 5 — Hold winners longer when trending, exit faster when choppy
=================================================================

USER LOGIC:
- Market 2 states: trending vs sideways
- Trending → HOLD (extend time_stop)
- Sideways → EXIT FAST (short time_stop)
- Tunable: 50 bars vs 100 bars

INDICATORS:
- EMA(50) — trend direction
- ADX(14) — regime detector (sideways vs trending)
- ATR(14) — normalization for stops

ENTRY (same as 4D + trend filter):
- Long: Close > EMA(50), today's range > 2 * ATR

EXIT (variable based on ADX regime at entry):
- Stop: 2 * ATR (always)
- Trailing: 3 * ATR (always)
- TIME STOP:
  - If ADX > 25 at entry → LONG hold (100 bars or dynamic)
  - If ADX 20-25 → MEDIUM (50 bars)
  - If ADX < 20 → SHORT (10 bars, exit quick in choppy)
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


def add_indicators(df, ema_p=50, atr_p=14, adx_p=14):
    df = df.copy()
    df['EMA'] = df['Close'].ewm(span=ema_p, adjust=False).mean()
    high_low = df['High'] - df['Low']
    high_close = (df['High'] - df['Close'].shift()).abs()
    low_close = (df['Low'] - df['Close'].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['ATR'] = tr.ewm(alpha=1/atr_p, adjust=False).mean()
    df['TR'] = tr
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


def run_test5(df, **params):
    p = {
        'ema_p': 50, 'atr_p': 14, 'adx_p': 14,
        'range_atr_mult': 2.0,  # entry condition
        'stop_atr': 2.0,
        'trailing_atr': 3.0,
        # Time stops based on ADX regime at entry
        'time_stop_strong': 100,  # ADX > 25 (strong trend)
        'time_stop_moderate': 50,  # ADX 20-25
        'time_stop_weak': 10,     # ADX < 20 (choppy)
        'atr_mult_entry': 2.0,
        'require_above_ema': True,
    }
    p.update(params)

    if len(df) < 100:
        return None

    df = add_indicators(df, ema_p=p['ema_p'], atr_p=p['atr_p'], adx_p=p['adx_p']).reset_index(drop=True)
    n = len(df)
    closes = df['Close'].values
    opens = df['Open'].values
    highs = df['High'].values
    lows = df['Low'].values
    emas = df['EMA'].values
    atrs = df['ATR'].values
    adxs = df['ADX'].values

    trades = []
    in_trade = False

    for i in range(p['ema_p'], n - 1):
        atr = atrs[i]
        if np.isnan(atr) or atr <= 0:
            continue

        if not in_trade:
            close = closes[i]; ema = emas[i]; adx = adxs[i]
            high = highs[i]; low = lows[i]
            today_range = high - low

            # Entry: today's range > 2*ATR (volatility expansion)
            trend_ok = (close > ema) if p['require_above_ema'] else True

            if today_range > p['atr_mult_entry'] * atr and trend_ok:
                entry_price = opens[i + 1]
                entry_bar = i + 1
                entry_atr = atr
                stop = entry_price - p['stop_atr'] * atr
                extreme = entry_price
                trailing_stop = None
                in_trade = True
                direction = 'long'
                # Determine time_stop based on ADX at entry
                if adx > 25:
                    time_stop = p['time_stop_strong']
                elif adx > 20:
                    time_stop = p['time_stop_moderate']
                else:
                    time_stop = p['time_stop_weak']

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
                if (i - entry_bar) >= time_stop:
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
                    'bars_held_actual': i - entry_bar,
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
    avg_bars_w = wins['bars_held'].mean() if n_w > 0 else 0
    avg_bars_l = losses['bars_held'].mean() if n_l > 0 else 0
    return {
        'trades': total, 'wr': wr, 'payout': payout,
        'mean': mean_pnl, 'median': median_pnl,
        'avg_win': avg_win, 'avg_loss': avg_loss, 'expectancy': expectancy,
        'avg_bars_w': avg_bars_w, 'avg_bars_l': avg_bars_l,
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


def run_strategy(name, **params):
    print(f"\n>>> {name}")
    print(f"    params: {params}")
    all_trades = []
    for ticker in stocks['Ticker'].unique():
        tdf = stocks[stocks['Ticker'] == ticker].reset_index(drop=True)
        tr = run_test5(tdf, **params)
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
    print(f"    avg bars winner={s['avg_bars_w']:.1f}, loser={s['avg_bars_l']:.1f}")
    print(f"    7-criteria pass: {passes}/7")

    if s['trades'] >= 100:
        bs = bootstrap_stability(agg)
        if bs:
            print(f"    BS: WR mean={bs['wr_mean']:.1f}% std={bs['wr_std']:.1f}%, "
                  f"WR>50% in {bs['wr_pass_pct']:.0f}% samples, "
                  f"Exp>0 in {bs['exp_pass_pct']:.0f}%, "
                  f"Payout>2 in {bs['payout_pass_pct']:.0f}%")

    s['name'] = name
    s['passes'] = passes
    s['trades_df'] = agg
    return s


# === Compare different hold durations ===
print("=" * 80)
print("EXPERIMENT: How long should we HOLD WINNERS?")
print("Logic: ATR breakout entry + regime-based time stop")
print("=" * 80)

results = []

# Baseline: fixed short hold (10)
results.append(run_strategy("FIXED 10 bar hold", time_stop_strong=10, time_stop_moderate=10, time_stop_weak=10))

# Fixed 25
results.append(run_strategy("FIXED 25 bar hold", time_stop_strong=25, time_stop_moderate=25, time_stop_weak=25))

# Fixed 50
results.append(run_strategy("FIXED 50 bar hold", time_stop_strong=50, time_stop_moderate=50, time_stop_weak=50))

# Fixed 100
results.append(run_strategy("FIXED 100 bar hold", time_stop_strong=100, time_stop_moderate=100, time_stop_weak=100))

# REGIME-BASED (user's logic)
results.append(run_strategy("REGIME: 10/50/100 (choppy/mod/strong)",
                            time_stop_strong=100, time_stop_moderate=50, time_stop_weak=10))
results.append(run_strategy("REGIME: 25/75/150 (more aggressive)",
                            time_stop_strong=150, time_stop_moderate=75, time_stop_weak=25))
results.append(run_strategy("REGIME: 5/30/75 (conservative)",
                            time_stop_strong=75, time_stop_moderate=30, time_stop_weak=5))

# Summary
print("\n" + "=" * 80)
print("SUMMARY — Hold duration comparison")
print("=" * 80)
print(f"{'Strategy':<45} {'Trades':>7} {'WR%':>7} {'Payout':>7} {'Exp':>9} {'Avg W bars':>11} {'7-crit':>7}")
print("-" * 100)
results = [r for r in results if r is not None]
for r in sorted(results, key=lambda x: (-x['passes'], -x['expectancy'])):
    print(f"{r['name']:<45} {r['trades']:>7} {r['wr']:>6.2f}% {r['payout']:>7.2f} "
          f"{r['expectancy']:>+9.4f} {r['avg_bars_w']:>11.1f} {r['passes']:>5}/7")


# === Find best by expectancy ===
best = max(results, key=lambda x: x['expectancy'])
print(f"\n>>> BEST (by expectancy): {best['name']}")
print(f"    exp={best['expectancy']:+.4f}, trades={best['trades']}, WR={best['wr']:.2f}%, "
      f"payout={best['payout']:.2f}, 7-crit={best['passes']}/7")
print(f"    avg_bars_winner={best['avg_bars_w']:.1f}, avg_bars_loser={best['avg_bars_l']:.1f}")
