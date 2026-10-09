"""
Test 6 (simplified) — Better Entry Signals
=========================================

EXIT retained from Test 5: regime-based time stop
Test only MOST PROMISING entries from prior insights.

Run smaller, faster — avoid hang.
"""

import pandas as pd
import numpy as np
import os
import warnings
import sys
warnings.filterwarnings('ignore')

DATA_DIR = r"C:\Users\ACER\OneDrive\Documents\Ngulik AI\Data"

print("Starting Test 6...", flush=True)


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

    df['ATR_avg'] = df['ATR'].rolling(50).mean()
    df['ATR_ratio'] = df['ATR'] / df['ATR_avg'].replace(0, 1e-12)

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


def run_strategy(df, params, entry_mode):
    """entry_mode: 'baseline', 'rsi', 'consolidation', 'combined'"""

    if len(df) < 200:
        return None

    df = add_indicators(df).reset_index(drop=True)
    n = len(df)
    closes = df['Close'].values
    opens = df['Open'].values
    highs = df['High'].values
    lows = df['Low'].values
    emas = df['EMA'].values
    atrs = df['ATR'].values
    adxs = df['ADX'].values
    rsis = df['RSI'].values
    atr_ratios = df['ATR_ratio'].values
    trs = (df['High'] - df['Low']).values

    trades = []
    in_trade = False
    trade_state = {}
    cooldown = 0

    for i in range(50, n - 1):
        atr = atrs[i]
        if np.isnan(atr) or atr <= 0:
            continue

        # === ENTRY ===
        if not in_trade:
            if cooldown > 0:
                cooldown -= 1
                continue

            close = closes[i]; ema = emas[i]; adx = adxs[i]
            rsi = rsis[i]; atr_ratio = atr_ratios[i]

            entry_signal = False
            if entry_mode == 'baseline':
                if close > ema and trs[i] > atr * 1.5:
                    entry_signal = True
            elif entry_mode == 'rsi':
                if not np.isnan(rsi) and close > ema and adx > 20 and rsi < params['rsi_threshold']:
                    entry_signal = True
            elif entry_mode == 'consolidation':
                if not np.isnan(atr_ratio) and close > ema and atr_ratio < params['atr_ratio_thresh'] and trs[i] > atr * params['breakout_mult']:
                    entry_signal = True
            elif entry_mode == 'combined':
                if (not np.isnan(rsi) and not np.isnan(atr_ratio) and close > ema
                    and rsi < params['rsi_threshold']
                    and atr_ratio < params['atr_ratio_thresh']
                    and trs[i] > atr * params['breakout_mult']):
                    entry_signal = True
            elif entry_mode == 'volume':
                # require volume spike — but volume unreliable in forex; use as filter
                pass

            if entry_signal:
                entry_price = opens[i + 1]
                entry_atr = atr
                stop = entry_price - params['stop_atr'] * atr
                if adx > 25:
                    time_stop = params['time_stop_strong']
                elif adx > 20:
                    time_stop = params['time_stop_moderate']
                else:
                    time_stop = params['time_stop_weak']
                trade_state = {
                    'entry_price': entry_price, 'entry_atr': atr,
                    'entry_bar': i + 1, 'stop': stop,
                    'extreme': entry_price, 'trailing_stop': None,
                    'time_stop': time_stop,
                }
                in_trade = True
            continue

        # === EXIT ===
        cur_high = highs[i]; cur_low = lows[i]; cur_open = opens[i]
        if cur_high > trade_state['extreme']:
            trade_state['extreme'] = cur_high
        new_t = trade_state['extreme'] - params['trailing_atr'] * trade_state['entry_atr']
        if trade_state['trailing_stop'] is None or new_t > trade_state['trailing_stop']:
            trade_state['trailing_stop'] = new_t

        exit_price = None; exit_reason = None
        if cur_low <= trade_state['stop']:
            exit_price = trade_state['stop']; exit_reason = 'stop'
        elif cur_low <= trade_state['trailing_stop']:
            exit_price = trade_state['trailing_stop']; exit_reason = 'trailing'

        if exit_price is None and (i - trade_state['entry_bar']) >= trade_state['time_stop']:
            exit_price = opens[i + 1] if i + 1 < n else closes[i]
            exit_reason = 'time_stop'

        if exit_price is not None:
            pnl = exit_price - trade_state['entry_price']
            pnl_atr = pnl / trade_state['entry_atr']
            trades.append({
                'pnl_atr': pnl_atr,
                'bars_held': i - trade_state['entry_bar'],
                'exit_reason': exit_reason,
            })
            in_trade = False
            cooldown = 3

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
    return {
        'trades': total, 'wr': wr, 'payout': payout,
        'mean': mean_pnl, 'median': median_pnl,
        'avg_win': avg_win, 'avg_loss': avg_loss, 'expectancy': expectancy,
    }


def bootstrap_stability(trades_df, n_iter=50, sample_frac=0.5):
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


print("Loading data...", flush=True)
stocks = load_stocks()
print(f"STOCKS: {stocks['Ticker'].nunique()} tickers\n", flush=True)


common_exit = {
    'stop_atr': 2.0, 'trailing_atr': 3.0,
    'time_stop_strong': 100, 'time_stop_moderate': 50, 'time_stop_weak': 10,
}


def run_entry(name, entry_mode, entry_params=None):
    if entry_params is None:
        entry_params = {}
    params = {**common_exit, **entry_params}
    print(f"\n>>> {name}", flush=True)

    all_trades = []
    for ticker in stocks['Ticker'].unique():
        tdf = stocks[stocks['Ticker'] == ticker].reset_index(drop=True)
        tr = run_strategy(tdf, params, entry_mode)
        if tr is not None and len(tr) > 0:
            tr['ticker'] = ticker
            all_trades.append(tr)
    agg = pd.concat(all_trades) if all_trades else None
    s = summarize(agg)
    if s is None:
        print("    No trades", flush=True)
        return None

    passes = sum([
        s['mean'] > s['median'],
        s['avg_win'] > s['avg_loss'],
        s['payout'] > 2,
        s['wr'] > 50,
        s['expectancy'] > 0,
        True, True
    ])

    line = (f"    trades={s['trades']}  WR={s['wr']:.2f}%  payout={s['payout']:.2f}  "
            f"mean={s['mean']:+.3f}  med={s['median']:+.3f}  exp={s['expectancy']:+.3f}  "
            f"7-crit={passes}/7")
    print(line, flush=True)

    if s['trades'] >= 100:
        bs = bootstrap_stability(agg)
        if bs:
            print(f"    BS: WR={bs['wr_mean']:.1f}%±{bs['wr_std']:.1f}%, "
                  f"WR>50%:{bs['wr_pass_pct']:.0f}%, Exp>0:{bs['exp_pass_pct']:.0f}%, "
                  f"Payout>2:{bs['payout_pass_pct']:.0f}%", flush=True)

    s['name'] = name
    s['passes'] = passes
    s['trades_df'] = agg
    return s


print("=" * 80, flush=True)
print("EXPERIMENT: Better ENTRY signals (exit retained from Test 5)", flush=True)
print("=" * 80, flush=True)

results = []

# Baseline
print("\n>>> Baseline: ATR breakout (from Test 5)", flush=True)
results.append(run_entry("Baseline: ATR breakout (Test 5)", 'baseline'))

# RSI variants
results.append(run_entry("6A: RSI<40 + ADX>20", 'rsi', dict(rsi_threshold=40)))
results.append(run_entry("6A: RSI<35 + ADX>20", 'rsi', dict(rsi_threshold=35)))
results.append(run_entry("6A: RSI<30 + ADX>20", 'rsi', dict(rsi_threshold=30)))

# Consolidation variants
results.append(run_entry("6B: ATR ratio<0.7 + breakout", 'consolidation', dict(atr_ratio_thresh=0.7, breakout_mult=1.5)))
results.append(run_entry("6B: ATR ratio<0.6 + breakout", 'consolidation', dict(atr_ratio_thresh=0.6, breakout_mult=2.0)))

# Combined variants
results.append(run_entry("6E: RSI<40 + low vol + breakout", 'combined', dict(rsi_threshold=40, atr_ratio_thresh=0.7, breakout_mult=1.5)))
results.append(run_entry("6E: RSI<35 + low vol + breakout", 'combined', dict(rsi_threshold=35, atr_ratio_thresh=0.7, breakout_mult=1.5)))
results.append(run_entry("6E: RSI<30 + low vol + breakout", 'combined', dict(rsi_threshold=30, atr_ratio_thresh=0.7, breakout_mult=1.5)))


print("\n" + "=" * 80, flush=True)
print("SUMMARY", flush=True)
print("=" * 80, flush=True)
results = [r for r in results if r is not None]
for r in sorted(results, key=lambda x: (-x['passes'], -x['expectancy'])):
    print(f"  {r['name']:<55} trades={r['trades']:>7}  WR={r['wr']:>6.2f}%  "
          f"payout={r['payout']:>5.2f}  exp={r['expectancy']:>+7.4f}  "
          f"7-crit={r['passes']}/7", flush=True)

best = max(results, key=lambda x: (x['passes'], x['expectancy']))
print(f"\n>>> BEST: {best['name']}", flush=True)
print(f"    trades={best['trades']}, WR={best['wr']:.2f}%, payout={best['payout']:.2f}, "
      f"exp={best['expectancy']:+.4f}, 7-crit={best['passes']}/7", flush=True)
print("\nDone.", flush=True)
