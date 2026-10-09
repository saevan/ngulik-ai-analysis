"""Breakdown EXIT strategy: which component contributes what"""
import os
import warnings
warnings.filterwarnings('ignore')
import numpy as np
import pandas as pd

DATA_DIR = r"C:\Users\ACER\OneDrive\Documents\Ngulik AI\Data"

def load():
    df = pd.read_csv(os.path.join(DATA_DIR, "Data kompas 100.csv"))
    df.columns = [c.strip() for c in df.columns]
    df['Date/Time'] = pd.to_datetime(df['Date/Time'], format='mixed', dayfirst=True)
    df = df.sort_values(['Ticker', 'Date/Time']).reset_index(drop=True)
    return df


def add_ind(df):
    df = df.copy().reset_index(drop=True)
    df['EMA'] = df['Close'].ewm(span=50, adjust=False).mean()
    delta = df['Close'].diff()
    gain = delta.clip(lower=0); loss = (-delta).clip(lower=0)
    ag = gain.ewm(alpha=1/14, adjust=False).mean()
    al = loss.ewm(alpha=1/14, adjust=False).mean()
    rs = ag / al.replace(0, 1e-12)
    df['RSI'] = 100 - (100 / (1 + rs))
    hl = df['High'] - df['Low']
    hc = (df['High'] - df['Close'].shift()).abs()
    lc = (df['Low'] - df['Close'].shift()).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    df['ATR'] = tr.ewm(alpha=1/14, adjust=False).mean()
    df['ATR_avg'] = df['ATR'].rolling(50).mean()
    df['ATR_ratio'] = df['ATR'] / df['ATR_avg'].replace(0, 1e-12)
    up = df['High'] - df['High'].shift()
    dn = df['Low'].shift() - df['Low']
    plus_dm = pd.Series(np.where((up > dn) & (up > 0), up, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((dn > up) & (dn > 0), dn, 0.0), index=df.index)
    atr_s = tr.ewm(alpha=1/14, adjust=False).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1/14, adjust=False).mean() / atr_s.replace(0, 1e-12)
    minus_di = 100 * minus_dm.ewm(alpha=1/14, adjust=False).mean() / atr_s.replace(0, 1e-12)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, 1e-12)
    df['ADX'] = dx.ewm(alpha=1/14, adjust=False).mean()
    return df


def run_breakdown(df, params):
    """Run 6B-like strategy with detailed exit logging per component."""
    if len(df) < 200:
        return None
    df = add_ind(df)
    n = len(df)
    closes = df['Close'].values; opens = df['Open'].values
    highs = df['High'].values; lows = df['Low'].values
    emas = df['EMA'].values; atrs = df['ATR'].values
    adxs = df['ADX'].values
    atr_ratios = df['ATR_ratio'].values

    rows = []
    in_trade = False; state = {}; cd = 0
    for i in range(60, n - 1):
        atr = atrs[i]
        if np.isnan(atr) or atr <= 0: continue
        if not in_trade:
            if cd > 0: cd -= 1; continue
            if any(np.isnan(x) for x in [atr_ratios[i], adxs[i]]): continue
            close = closes[i]; ema = emas[i]
            atr_ratio = atr_ratios[i]; adx = adxs[i]
            if (close > ema and atr_ratio < 0.6
                and (highs[i] - lows[i]) > atr * 1.5):
                entry_price = opens[i + 1]
                stop = entry_price - 2.0 * atr
                if adx > 25: ts = 100
                elif adx > 20: ts = 50
                else: ts = 10
                state = {'ep': entry_price, 'ea': atr, 'eb': i+1,
                         'stop': stop, 'ext': entry_price, 'tr': None, 'ts': ts}
                in_trade = True
            continue
        if highs[i] > state['ext']: state['ext'] = highs[i]
        new_t = state['ext'] - 3.0 * state['ea']
        if state['tr'] is None or new_t > state['tr']: state['tr'] = new_t
        ep = None; er = None
        hit_stop = lows[i] <= state['stop']
        hit_trail = lows[i] <= state['tr']
        hit_time = (i - state['eb']) >= state['ts']
        if hit_stop and hit_trail:
            ep = state['stop']; er = 'stop'  # stop takes priority
        elif hit_stop:
            ep = state['stop']; er = 'stop'
        elif hit_trail:
            ep = state['tr']; er = 'trail'
        if ep is None and hit_time:
            ep = opens[i + 1] if i + 1 < n else closes[i]; er = 'time'
        if ep is not None:
            pnl = (ep - state['ep']) / state['ea']
            rows.append({
                'pnl_atr': pnl,
                'exit_reason': er,
                'bars': i - state['eb'],
                'adx_entry': state['ts'],
                'stop_atr': state['ea'] * 2.0,
                'trail_atr': state['tr'] if state['tr'] else state['ea'] * 3.0,
                'exit_price': ep,
                'extreme_reached': state['ext'],
                'entry_price': state['ep'],
            })
            in_trade = False; cd = 3

    return pd.DataFrame(rows) if rows else None


def analyze_by_exit_reason(df):
    if df is None or len(df) == 0: return
    print(f"\n=== BREAKDOWN BY EXIT REASON ===", flush=True)
    print(f"{'Reason':<10} {'N':>5} {'%':>6} {'WR%':>6} {'Avg Win':>9} {'Avg Loss':>10} {'Sum PnL':>10} {'Avg Bars':>9}", flush=True)
    print("-" * 70, flush=True)
    for r in df['exit_reason'].unique():
        sub = df[df['exit_reason'] == r]
        n = len(sub)
        pct = n / len(df) * 100
        wins = sub[sub['pnl_atr'] > 0]
        losses = sub[sub['pnl_atr'] <= 0]
        wr = len(wins) / n * 100 if n > 0 else 0
        aw = wins['pnl_atr'].mean() if len(wins) > 0 else 0
        al = abs(losses['pnl_atr'].mean()) if len(losses) > 0 else 0
        sp = sub['pnl_atr'].sum()
        ab = sub['bars'].mean()
        print(f"{r:<10} {n:>5} {pct:>5.1f}% {wr:>5.1f}% {aw:>+9.3f} {al:>9.3f} {sp:>+10.3f} {ab:>9.1f}", flush=True)


def analyze_by_time_stop(df):
    if df is None or len(df) == 0: return
    print(f"\n=== BREAKDOWN BY ENTRY ADX REGIME (time_stop buckets) ===", flush=True)
    print(f"{'ADX Ts':<10} {'N':>5} {'%':>6} {'WR%':>6} {'Avg Win':>9} {'Avg Loss':>10} {'Sum PnL':>10} {'Avg Bars':>9}", flush=True)
    print("-" * 70, flush=True)
    for ts_val in sorted(df['adx_entry'].unique()):
        sub = df[df['adx_entry'] == ts_val]
        n = len(sub)
        pct = n / len(df) * 100
        wins = sub[sub['pnl_atr'] > 0]
        losses = sub[sub['pnl_atr'] <= 0]
        wr = len(wins) / n * 100 if n > 0 else 0
        aw = wins['pnl_atr'].mean() if len(wins) > 0 else 0
        al = abs(losses['pnl_atr'].mean()) if len(losses) > 0 else 0
        sp = sub['pnl_atr'].sum()
        ab = sub['bars'].mean()
        print(f"TS={ts_val:<5} {n:>5} {pct:>5.1f}% {wr:>5.1f}% {aw:>+9.3f} {al:>9.3f} {sp:>+10.3f} {ab:>9.1f}", flush=True)


def analyze_bars_held(df):
    if df is None or len(df) == 0: return
    print(f"\n=== BREAKDOWN BY BARS HELD (Time Stop Effect) ===", flush=True)
    print(f"{'Bars range':<15} {'N':>5} {'%':>6} {'WR%':>6} {'Sum PnL':>10} {'Hit time stop':>14}", flush=True)
    print("-" * 60, flush=True)
    bins = [(0, 5), (5, 15), (15, 30), (30, 60), (60, 100), (100, 200)]
    for lo, hi in bins:
        sub = df[(df['bars'] >= lo) & (df['bars'] < hi)]
        n = len(sub)
        if n == 0: continue
        pct = n / len(df) * 100
        wins = sub[sub['pnl_atr'] > 0]
        wr = len(wins) / n * 100
        sp = sub['pnl_atr'].sum()
        time_pct = sum(sub['exit_reason'] == 'time') / n * 100
        print(f"{lo}-{hi:<10} {n:>5} {pct:>5.1f}% {wr:>5.1f}% {sp:>+10.3f} {time_pct:>13.1f}%", flush=True)


def analyze_win_loss_distance(df):
    if df is None or len(df) == 0: return
    print(f"\n=== STOP vs TRAIL: which triggered first? ===", flush=True)
    print(f"For each trade, what would have been the ALTERNATIVE exit?", flush=True)
    wins = df[df['pnl_atr'] > 0]
    losses = df[df['pnl_atr'] <= 0]
    if len(wins) > 0:
        print(f"\nWINNERS ({len(wins)}):", flush=True)
        print(f"  Avg pnl: {wins['pnl_atr'].mean():+.3f}", flush=True)
        print(f"  Avg bars: {wins['bars'].mean():.1f}", flush=True)
        print(f"  By exit: stop={sum(wins['exit_reason']=='stop')}, trail={sum(wins['exit_reason']=='trail')}, time={sum(wins['exit_reason']=='time')}", flush=True)
    if len(losses) > 0:
        print(f"\nLOSERS ({len(losses)}):", flush=True)
        print(f"  Avg pnl: {losses['pnl_atr'].mean():+.3f}", flush=True)
        print(f"  Avg bars: {losses['bars'].mean():.1f}", flush=True)
        print(f"  By exit: stop={sum(losses['exit_reason']=='stop')}, trail={sum(losses['exit_reason']=='trail')}, time={sum(losses['exit_reason']=='time')}", flush=True)


def analyze_counterfactual(df):
    """What if we used only ONE exit type?"""
    if df is None or len(df) == 0: return
    print(f"\n=== COUNTERFACTUAL: what if only specific exit type existed? ===", flush=True)

    print(f"\nFull strategy (all 3 exits): total pnl = {df['pnl_atr'].sum():+.3f}, "
          f"WR = {(df['pnl_atr']>0).mean()*100:.1f}%", flush=True)

    for r in ['stop', 'trail', 'time']:
        sub = df[df['exit_reason'] == r]
        if len(sub) == 0: continue
        nw = (sub['pnl_atr'] > 0).sum()
        wr = nw / len(sub) * 100 if len(sub) > 0 else 0
        sp = sub['pnl_atr'].sum()
        avg_pnl = sub['pnl_atr'].mean()
        print(f"  Only {r}: N={len(sub)}, WR={wr:.1f}%, sum={sp:+.3f}, avg={avg_pnl:+.3f}", flush=True)


def summary_compare(df):
    """Compare exit contribution to overall expectancy."""
    if df is None or len(df) == 0: return
    print(f"\n=== EXPECTANCY CONTRIBUTION BY EXIT ===", flush=True)
    total_pnl = df['pnl_atr'].sum()
    for r in sorted(df['exit_reason'].unique()):
        sub = df[df['exit_reason'] == r]
        contrib = sub['pnl_atr'].sum() / total_pnl * 100
        nw = (sub['pnl_atr'] > 0).sum()
        wr = nw / len(sub) * 100 if len(sub) > 0 else 0
        avg = sub['pnl_atr'].mean()
        print(f"  {r:<6}: pnl {sub['pnl_atr'].sum():+.3f}, "
              f"N={len(sub):>3}, WR={wr:.1f}%, avg={avg:+.3f}, "
              f"contributes {contrib:>5.1f}% of total", flush=True)


print("Loading...", flush=True)
stocks = load()
print(f"Done. {stocks['Ticker'].nunique()} tickers.\n", flush=True)

print("Running Test 6 6B with exit logging on full sample...", flush=True)
all_t = []
for t in stocks['Ticker'].unique():
    tdf = stocks[stocks['Ticker'] == t].reset_index(drop=True)
    tr = run_breakdown(tdf, None)
    if tr is not None and len(tr) > 0:
        tr['ticker'] = t
        all_t.append(tr)

agg = pd.concat(all_t) if all_t else None
print(f"Total trades: {len(agg)}", flush=True)

if agg is not None:
    analyze_by_exit_reason(agg)
    analyze_by_time_stop(agg)
    analyze_bars_held(agg)
    analyze_win_loss_distance(agg)
    counterfactual = analyze_counterfactual(agg)
    summary_compare(agg)

print("\nDone.", flush=True)
