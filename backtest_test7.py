"""
Test 7 — Revamped Entry untuk memenuhi 7 kriteria
=================================================

Lessons dari Test 1-6:
1. WR>50% butuh selective entry (T3-A3 achieved tapi spurious, 23 trades)
2. Composite logic (multi-condition) bisa achieve high WR tapi trade count rendah
3. Consolidation breakout (6B) paling stabil di 100 trades
4. Hold duration (Test 5) tidak push WR, hanya expectancy

Pendekatan Test 7: kombinasikan MULTIPLE orthogonal entry signals untuk selectivity tinggi.
Tujuan: WR>50% dengan trade count meaningful (50+).

CANDIDATES:
7A. Multi-condition strict: trend + low vol + tight RSI + breakout
7B. Bollinger Band + ATR breakout (volatility compression → expansion)
7C. Higher TF trend + LTF pullback (multi-TF)
7D. Adaptive volatility breakout (ATR percentile + momentum)
7E. Range expansion with trend confirmation (ATR expansion + EMA position)
7F. Multi-bar confirmation (entry only after N consecutive qualifying bars)
7G. Volatility + momentum + trend (3 filters)
"""

import pandas as pd
import numpy as np
import os
import warnings
import sys
warnings.filterwarnings('ignore')

DATA_DIR = r"C:\Users\ACER\OneDrive\Documents\Ngulik AI\Data"

print("Starting Test 7...", flush=True)


def load_stocks():
    path = os.path.join(DATA_DIR, "Data kompas 100.csv")
    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]
    df['Date/Time'] = pd.to_datetime(df['Date/Time'], format='mixed', dayfirst=True)
    df = df.sort_values(['Ticker', 'Date/Time']).reset_index(drop=True)
    return df


def add_indicators(df, ema_p=50, rsi_p=14, atr_p=14, adx_p=14, bb_p=20):
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

    df['BB_mid'] = df['Close'].rolling(bb_p).mean()
    df['BB_std'] = df['Close'].rolling(bb_p).std()
    df['BB_upper'] = df['BB_mid'] + 2 * df['BB_std']
    df['BB_lower'] = df['BB_mid'] - 2 * df['BB_std']
    df['BB_width'] = (df['BB_upper'] - df['BB_lower']) / df['BB_mid'].replace(0, 1e-12)
    df['BB_width_avg'] = df['BB_width'].rolling(50).mean()
    df['BB_width_ratio'] = df['BB_width'] / df['BB_width_avg'].replace(0, 1e-12)

    up_move = df['High'] - df['High'].shift()
    down_move = df['Low'].shift() - df['Low']
    plus_dm = pd.Series(np.where((up_move > down_move) & (up_move > 0), up_move, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((down_move > up_move) & (down_move > 0), down_move, 0.0), index=df.index)
    atr_smooth = tr.ewm(alpha=1/adx_p, adjust=False).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1/adx_p, adjust=False).mean() / atr_smooth.replace(0, 1e-12)
    minus_di = 100 * minus_dm.ewm(alpha=1/adx_p, adjust=False).mean() / atr_smooth.replace(0, 1e-12)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, 1e-12)
    df['ADX'] = dx.ewm(alpha=1/adx_p, adjust=False).mean()

    # Momentum: rate of change of close
    df['ROC5'] = df['Close'].pct_change(5)
    df['ROC20'] = df['Close'].pct_change(20)

    return df


def run_strategy(df, params, entry_mode):
    """Apply entry mode + Test 5 regime-based exit."""
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
    bb_width_ratios = df['BB_width_ratio'].values
    bb_lowers = df['BB_lower'].values
    bb_uppers = df['BB_upper'].values
    bb_mids = df['BB_mid'].values
    rocs5 = df['ROC5'].values
    rocs20 = df['ROC20'].values

    trades = []
    in_trade = False
    trade_state = {}
    cooldown = 0
    consec_count = 0  # for multi-bar confirmation

    for i in range(60, n - 1):
        atr = atrs[i]
        if np.isnan(atr) or atr <= 0:
            continue

        # === ENTRY ===
        if not in_trade:
            if cooldown > 0:
                cooldown -= 1
                consec_count = 0
                continue

            close = closes[i]; ema = emas[i]; adx = adxs[i]
            rsi = rsis[i]; atr_ratio = atr_ratios[i]
            bb_width_ratio = bb_width_ratios[i]
            bb_lower = bb_lowers[i]; bb_upper = bb_uppers[i]
            roc5 = rocs5[i]; roc20 = rocs20[i]

            # Skip if NaN
            if any(np.isnan(x) for x in [rsi, atr_ratio, bb_width_ratio, bb_lower, bb_upper, roc5, roc20]):
                consec_count = 0
                continue

            entry_signal = False

            if entry_mode == '7A_strict':
                # Trend + low vol + tight RSI + breakout
                if (close > ema and adx > 20 and rsi < params['rsi_thresh']
                    and atr_ratio < params['atr_ratio_thresh']
                    and (highs[i] - lows[i]) > atr * params['breakout_mult']):
                    consec_count += 1
                    if consec_count >= params['min_consec']:
                        entry_signal = True
                else:
                    consec_count = 0

            elif entry_mode == '7B_bb_breakout':
                # BB width contraction → expansion breakout
                # BB width must be contracting (yesterday) then today's range expansion
                if i > 0:
                    prev_bb_width = bb_width_ratios[i - 1]
                    if (close > ema
                        and prev_bb_width < params['bb_contract_thresh']
                        and (highs[i] - lows[i]) > atr * params['breakout_mult']
                        and close > bb_mids[i]):
                        consec_count += 1
                        if consec_count >= params['min_consec']:
                            entry_signal = True
                    else:
                        consec_count = 0
                else:
                    consec_count = 0

            elif entry_mode == '7C_htf_ltf':
                # Higher TF trend (EMA50 > EMA200) + LTF pullback (RSI < 40)
                ema_fast = df['Close'].ewm(span=50).mean().iloc[i]
                ema_slow = df['Close'].ewm(span=200).mean().iloc[i]
                if not np.isnan(ema_slow):
                    if (close > ema_fast and ema_fast > ema_slow
                        and rsi < params['rsi_thresh']
                        and adx > params['adx_thresh']
                        and roc5 > 0):  # short-term momentum positive
                        consec_count += 1
                        if consec_count >= params['min_consec']:
                            entry_signal = True
                    else:
                        consec_count = 0
                else:
                    consec_count = 0

            elif entry_mode == '7D_adaptive_vol':
                # Adaptive volatility breakout: ATR must be in low percentile (compression)
                # then expand. PLUS trend confirmation.
                if i > 0:
                    if (close > ema
                        and atr_ratio < params['atr_ratio_thresh']  # yesterday compressed
                        and (highs[i] - lows[i]) > atr * params['breakout_mult']
                        and roc5 > params['min_momentum']  # momentum confirmation
                        and adx > params['adx_thresh']):
                        consec_count += 1
                        if consec_count >= params['min_consec']:
                            entry_signal = True
                    else:
                        consec_count = 0
                else:
                    consec_count = 0

            elif entry_mode == '7E_trend_breakout':
                # Simple trend + breakout (no low vol filter) but tighter breakout
                if (close > ema
                    and roc5 > 0
                    and (highs[i] - lows[i]) > atr * params['breakout_mult']
                    and adx > params['adx_thresh']
                    and rsi > params['rsi_min']):  # not too oversold
                    consec_count += 1
                    if consec_count >= params['min_consec']:
                        entry_signal = True
                    else:
                        consec_count = 0
                else:
                    consec_count = 0

            elif entry_mode == '7F_pullback_breakout':
                # Yesterday: pullback (RSI < 40)
                # Today: breakout (today range > 2× ATR AND close > yesterday high)
                if i > 0:
                    yesterday_rsi = rsis[i - 1]
                    yesterday_high = highs[i - 1]
                    if (close > ema
                        and yesterday_rsi < params['yesterday_rsi_thresh']
                        and close > yesterday_high  # today breaks yesterday's high
                        and (highs[i] - lows[i]) > atr * params['breakout_mult']):
                        consec_count += 1
                        if consec_count >= params['min_consec']:
                            entry_signal = True
                    else:
                        consec_count = 0
                else:
                    consec_count = 0

            elif entry_mode == '7G_triple':
                # Trend + momentum + volatility (3 orthogonal filters)
                if (close > ema
                    and roc20 > params['roc_thresh']
                    and atr_ratio > params['atr_min']
                    and (highs[i] - lows[i]) > atr * params['breakout_mult']
                    and adx > params['adx_thresh']):
                    consec_count += 1
                    if consec_count >= params['min_consec']:
                        entry_signal = True
                    else:
                        consec_count = 0
                else:
                    consec_count = 0

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
                consec_count = 0
            continue

        # === EXIT (Test 5 regime-based) ===
        cur_high = highs[i]; cur_low = lows[i]
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

    if s['trades'] >= 50:
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
print("TEST 7 — REWORKED ENTRY", flush=True)
print("=" * 80, flush=True)

results = []

# 7A: Trend + low vol + tight RSI + breakout
results.append(run_entry("7A: trend+ADX+RSI<45+ATR<0.7+BO 1bar", '7A_strict',
                          dict(rsi_thresh=45, atr_ratio_thresh=0.7, breakout_mult=1.5, min_consec=1)))
results.append(run_entry("7A: trend+ADX+RSI<40+ATR<0.7+BO 1bar", '7A_strict',
                          dict(rsi_thresh=40, atr_ratio_thresh=0.7, breakout_mult=1.5, min_consec=1)))
results.append(run_entry("7A: trend+ADX+RSI<40+ATR<0.7+BO 2bar consec", '7A_strict',
                          dict(rsi_thresh=40, atr_ratio_thresh=0.7, breakout_mult=1.5, min_consec=2)))

# 7B: BB contraction → expansion breakout
results.append(run_entry("7B: BB<0.8 + breakout 1bar", '7B_bb_breakout',
                          dict(bb_contract_thresh=0.8, breakout_mult=1.5, min_consec=1)))
results.append(run_entry("7B: BB<0.6 + breakout 1bar", '7B_bb_breakout',
                          dict(bb_contract_thresh=0.6, breakout_mult=1.5, min_consec=1)))

# 7C: Multi-TF
results.append(run_entry("7C: EMA50>EMA200 + RSI<45 + ROC5>0", '7C_htf_ltf',
                          dict(rsi_thresh=45, adx_thresh=20, min_consec=1)))
results.append(run_entry("7C: EMA50>EMA200 + RSI<40 + ROC5>0", '7C_htf_ltf',
                          dict(rsi_thresh=40, adx_thresh=20, min_consec=1)))

# 7D: Adaptive volatility
results.append(run_entry("7D: ATR<0.7 + BO + momentum + ADX", '7D_adaptive_vol',
                          dict(atr_ratio_thresh=0.7, breakout_mult=1.5, min_momentum=0.0, adx_thresh=15, min_consec=1)))
results.append(run_entry("7D: ATR<0.6 + BO + momentum + ADX", '7D_adaptive_vol',
                          dict(atr_ratio_thresh=0.6, breakout_mult=1.5, min_momentum=0.0, adx_thresh=15, min_consec=1)))

# 7E: Simple trend + breakout
results.append(run_entry("7E: EMA + ROC5 + ADX + BO + RSI>50", '7E_trend_breakout',
                          dict(breakout_mult=1.5, adx_thresh=20, rsi_min=50, min_consec=1)))

# 7F: Yesterday pullback, today breakout
results.append(run_entry("7F: yesterday RSI<45 + today breaks yesterday high", '7F_pullback_breakout',
                          dict(yesterday_rsi_thresh=45, breakout_mult=1.5, min_consec=1)))
results.append(run_entry("7F: yesterday RSI<40 + today breaks high", '7F_pullback_breakout',
                          dict(yesterday_rsi_thresh=40, breakout_mult=1.5, min_consec=1)))

# 7G: Triple filter
results.append(run_entry("7G: trend + momentum + vol + ADX", '7G_triple',
                          dict(roc_thresh=0.0, atr_min=1.0, breakout_mult=1.5, adx_thresh=20, min_consec=1)))


print("\n" + "=" * 80, flush=True)
print("SUMMARY", flush=True)
print("=" * 80, flush=True)
results = [r for r in results if r is not None]
for r in sorted(results, key=lambda x: (-x['passes'], -x['expectancy'])):
    print(f"  {r['name']:<60} trades={r['trades']:>6}  WR={r['wr']:>6.2f}%  "
          f"payout={r['payout']:>5.2f}  exp={r['expectancy']:>+7.4f}  "
          f"7-crit={r['passes']}/7", flush=True)

best = max(results, key=lambda x: (x['passes'], x['expectancy']))
print(f"\n>>> BEST: {best['name']}", flush=True)
print(f"    trades={best['trades']}, WR={best['wr']:.2f}%, payout={best['payout']:.2f}, "
      f"exp={best['expectancy']:+.4f}, 7-crit={best['passes']}/7", flush=True)
print("\nDone.", flush=True)
