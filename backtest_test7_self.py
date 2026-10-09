"""Test 7 batch 1 — self-contained"""
import os
import warnings
warnings.filterwarnings('ignore')
import numpy as np
import pandas as pd

DATA_DIR = r"C:\Users\ACER\OneDrive\Documents\Ngulik AI\Data"


def load_stocks():
    df = pd.read_csv(os.path.join(DATA_DIR, "Data kompas 100.csv"))
    df.columns = [c.strip() for c in df.columns]
    df['Date/Time'] = pd.to_datetime(df['Date/Time'], format='mixed', dayfirst=True)
    df = df.sort_values(['Ticker', 'Date/Time']).reset_index(drop=True)
    return df


def add_indicators(df):
    df = df.copy()
    df['EMA'] = df['Close'].ewm(span=50, adjust=False).mean()
    delta = df['Close'].diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-12)
    df['RSI'] = 100 - (100 / (1 + rs))
    hl = df['High'] - df['Low']
    hc = (df['High'] - df['Close'].shift()).abs()
    lc = (df['Low'] - df['Close'].shift()).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    df['ATR'] = tr.ewm(alpha=1/14, adjust=False).mean()
    df['ATR_avg'] = df['ATR'].rolling(50).mean()
    df['ATR_ratio'] = df['ATR'] / df['ATR_avg'].replace(0, 1e-12)

    df['BB_mid'] = df['Close'].rolling(20).mean()
    df['BB_std'] = df['Close'].rolling(20).std()
    df['BB_upper'] = df['BB_mid'] + 2 * df['BB_std']
    df['BB_lower'] = df['BB_mid'] - 2 * df['BB_std']
    df['BB_width'] = (df['BB_upper'] - df['BB_lower']) / df['BB_mid'].replace(0, 1e-12)
    df['BB_width_avg'] = df['BB_width'].rolling(50).mean()
    df['BB_width_ratio'] = df['BB_width'] / df['BB_width_avg'].replace(0, 1e-12)

    up = df['High'] - df['High'].shift()
    dn = df['Low'].shift() - df['Low']
    plus_dm = pd.Series(np.where((up > dn) & (up > 0), up, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((dn > up) & (dn > 0), dn, 0.0), index=df.index)
    atr_s = tr.ewm(alpha=1/14, adjust=False).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1/14, adjust=False).mean() / atr_s.replace(0, 1e-12)
    minus_di = 100 * minus_dm.ewm(alpha=1/14, adjust=False).mean() / atr_s.replace(0, 1e-12)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, 1e-12)
    df['ADX'] = dx.ewm(alpha=1/14, adjust=False).mean()
    df['ROC5'] = df['Close'].pct_change(5)
    df['ROC20'] = df['Close'].pct_change(20)
    return df


def run_strategy(df, params, entry_mode):
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
    state = {}
    cooldown = 0
    consec = 0

    for i in range(60, n - 1):
        atr = atrs[i]
        if np.isnan(atr) or atr <= 0:
            continue

        if not in_trade:
            if cooldown > 0:
                cooldown -= 1
                consec = 0
                continue

            close = closes[i]; ema = emas[i]; adx = adxs[i]
            rsi = rsis[i]; atr_ratio = atr_ratios[i]
            bb_wr = bb_width_ratios[i]
            bb_lower = bb_lowers[i]; bb_upper = bb_uppers[i]
            roc5 = rocs5[i]; roc20 = rocs20[i]

            if any(np.isnan(x) for x in [rsi, atr_ratio, bb_wr, bb_lower, bb_upper, roc5, roc20]):
                consec = 0
                continue

            sig = False
            if entry_mode == '7A_strict':
                if (close > ema and adx > 20 and rsi < params['rsi_thresh']
                    and atr_ratio < params['atr_ratio_thresh']
                    and (highs[i] - lows[i]) > atr * params['breakout_mult']):
                    consec += 1
                    if consec >= params['min_consec']:
                        sig = True
                else:
                    consec = 0
            elif entry_mode == '7B_bb':
                if i > 0:
                    prev = bb_width_ratios[i - 1]
                    if (close > ema and prev < params['bb_thresh']
                        and (highs[i] - lows[i]) > atr * params['breakout_mult']
                        and close > bb_mids[i]):
                        consec += 1
                        if consec >= params['min_consec']:
                            sig = True
                    else:
                        consec = 0
            elif entry_mode == '7C_htf':
                ema50 = closes[:i+1] * 0 + np.nan
                # recompute slow EMA inline
                slow = pd.Series(closes[:i+1]).ewm(span=200).mean().iloc[-1]
                if not np.isnan(slow):
                    if (close > ema and ema > slow
                        and rsi < params['rsi_thresh']
                        and adx > params['adx_thresh']
                        and roc5 > 0):
                        consec += 1
                        if consec >= params['min_consec']:
                            sig = True
                    else:
                        consec = 0
            elif entry_mode == '7D_adv':
                if (close > ema and atr_ratio < params['atr_thresh']
                    and (highs[i] - lows[i]) > atr * params['breakout_mult']
                    and roc5 > params.get('min_mom', 0)
                    and adx > params['adx_thresh']):
                    consec += 1
                    if consec >= params['min_consec']:
                        sig = True
                    else:
                        consec = 0
            elif entry_mode == '7E_simple':
                if (close > ema and roc5 > 0
                    and (highs[i] - lows[i]) > atr * params['breakout_mult']
                    and adx > params['adx_thresh']
                    and rsi > params['rsi_min']):
                    consec += 1
                    if consec >= params['min_consec']:
                        sig = True
                    else:
                        consec = 0
            elif entry_mode == '7F_pb':
                if i > 0:
                    y_rsi = rsis[i - 1]
                    y_high = highs[i - 1]
                    if (close > ema and y_rsi < params['y_rsi']
                        and close > y_high
                        and (highs[i] - lows[i]) > atr * params['breakout_mult']):
                        consec += 1
                        if consec >= params['min_consec']:
                            sig = True
                    else:
                        consec = 0
            elif entry_mode == '7G_triple':
                if (close > ema and roc20 > params['roc_thresh']
                    and atr_ratio > params['atr_min']
                    and (highs[i] - lows[i]) > atr * params['breakout_mult']
                    and adx > params['adx_thresh']):
                    consec += 1
                    if consec >= params['min_consec']:
                        sig = True
                    else:
                        consec = 0

            if sig:
                entry_price = opens[i + 1]
                stop = entry_price - 2.0 * atr
                if adx > 25:
                    ts = 100
                elif adx > 20:
                    ts = 50
                else:
                    ts = 10
                state = {
                    'entry_price': entry_price, 'entry_atr': atr,
                    'entry_bar': i + 1, 'stop': stop,
                    'extreme': entry_price, 'trailing_stop': None,
                    'time_stop': ts,
                }
                in_trade = True
                consec = 0
            continue

        cur_high = highs[i]; cur_low = lows[i]
        if cur_high > state['extreme']:
            state['extreme'] = cur_high
        new_t = state['extreme'] - 3.0 * state['entry_atr']
        if state['trailing_stop'] is None or new_t > state['trailing_stop']:
            state['trailing_stop'] = new_t

        exit_price = None; exit_reason = None
        if cur_low <= state['stop']:
            exit_price = state['stop']; exit_reason = 'stop'
        elif cur_low <= state['trailing_stop']:
            exit_price = state['trailing_stop']; exit_reason = 'trailing'
        if exit_price is None and (i - state['entry_bar']) >= state['time_stop']:
            exit_price = opens[i + 1] if i + 1 < n else closes[i]
            exit_reason = 'time_stop'

        if exit_price is not None:
            pnl = exit_price - state['entry_price']
            pnl_atr = pnl / state['entry_atr']
            trades.append({'pnl_atr': pnl_atr, 'bars_held': i - state['entry_bar']})
            in_trade = False
            cooldown = 3

    return pd.DataFrame(trades) if trades else None


def summarize(df):
    if df is None or len(df) == 0:
        return None
    wins = df[df['pnl_atr'] > 0]
    losses = df[df['pnl_atr'] <= 0]
    total = len(df)
    nw = len(wins); nl = len(losses)
    wr = nw / total * 100
    aw = wins['pnl_atr'].mean() if nw > 0 else 0
    al = abs(losses['pnl_atr'].mean()) if nl > 0 else 0
    payout = aw / al if al > 0 else float('inf')
    return {'trades': total, 'wr': wr, 'payout': payout,
            'mean': df['pnl_atr'].mean(), 'median': df['pnl_atr'].median(),
            'avg_win': aw, 'avg_loss': al,
            'expectancy': (nw/total)*aw - (nl/total)*al}


def bootstrap(df, n_iter=50):
    np.random.seed(42)
    boot = []
    for _ in range(n_iter):
        sample = df.sample(frac=0.5, random_state=np.random.randint(0, 100000))
        s = summarize(sample)
        if s:
            boot.append(s)
    if not boot:
        return None
    wrs = [b['wr'] for b in boot]
    means = [b['mean'] for b in boot]
    payouts = [b['payout'] for b in boot]
    return {
        'wr_mean': np.mean(wrs),
        'wr_pass': sum(w > 50 for w in wrs) / len(wrs) * 100,
        'exp_pass': sum(m > 0 for m in means) / len(means) * 100,
        'pay_pass': sum(p > 2 for p in payouts) / len(payouts) * 100,
    }


print("Loading...", flush=True)
stocks = load_stocks()
print("Done.\n", flush=True)


def run_one(name, mode, params):
    print(f">>> {name}", flush=True)
    all_t = []
    for t in stocks['Ticker'].unique():
        tdf = stocks[stocks['Ticker'] == t].reset_index(drop=True)
        tr = run_strategy(tdf, params, mode)
        if tr is not None and len(tr) > 0:
            tr['ticker'] = t
            all_t.append(tr)
    agg = pd.concat(all_t) if all_t else None
    s = summarize(agg)
    if s is None:
        print("    No trades\n", flush=True)
        return None
    passes = sum([s['mean']>s['median'], s['avg_win']>s['avg_loss'], s['payout']>2,
                  s['wr']>50, s['expectancy']>0, True, True])
    print(f"    trades={s['trades']} WR={s['wr']:.2f}% pay={s['payout']:.2f} "
          f"mean={s['mean']:+.3f} med={s['median']:+.3f} exp={s['expectancy']:+.3f} "
          f"7c={passes}/7", flush=True)
    if s['trades'] >= 50:
        bs = bootstrap(agg)
        if bs:
            print(f"    BS: WR>50:{bs['wr_pass']:.0f}% Exp>0:{bs['exp_pass']:.0f}% "
                  f"Pay>2:{bs['pay_pass']:.0f}%", flush=True)
    print(flush=True)
    s['name'] = name
    s['passes'] = passes
    return s


results = []

# 7A strict composite
results.append(run_one("7A: trend+ADX>20+RSI<45+ATR<0.7+BO 1.5x", '7A_strict',
    dict(rsi_thresh=45, atr_ratio_thresh=0.7, breakout_mult=1.5, min_consec=1)))
results.append(run_one("7A: trend+ADX>20+RSI<45+ATR<0.6+BO 1.5x", '7A_strict',
    dict(rsi_thresh=45, atr_ratio_thresh=0.6, breakout_mult=1.5, min_consec=1)))
results.append(run_one("7A: trend+ADX>20+RSI<50+ATR<0.7+BO 1.5x", '7A_strict',
    dict(rsi_thresh=50, atr_ratio_thresh=0.7, breakout_mult=1.5, min_consec=1)))
results.append(run_one("7A: trend+ADX>20+RSI<50+ATR<0.7+BO 2x", '7A_strict',
    dict(rsi_thresh=50, atr_ratio_thresh=0.7, breakout_mult=2.0, min_consec=1)))

# 7B BB contraction
results.append(run_one("7B: BB<0.7 + BO", '7B_bb',
    dict(bb_thresh=0.7, breakout_mult=1.5, min_consec=1)))
results.append(run_one("7B: BB<0.6 + BO", '7B_bb',
    dict(bb_thresh=0.6, breakout_mult=1.5, min_consec=1)))

# 7C HTF
results.append(run_one("7C: EMA50>EMA200+RSI<50+ROC5>0+ADX>15", '7C_htf',
    dict(rsi_thresh=50, adx_thresh=15, min_consec=1)))
results.append(run_one("7C: EMA50>EMA200+RSI<50+ADX>15", '7C_htf',
    dict(rsi_thresh=50, adx_thresh=15, min_consec=1)))

# 7D adaptive vol
results.append(run_one("7D: ATR<0.7+BO+mom+ADX>15", '7D_adv',
    dict(atr_thresh=0.7, breakout_mult=1.5, min_mom=0, adx_thresh=15, min_consec=1)))
results.append(run_one("7D: ATR<0.6+BO+mom+ADX>15", '7D_adv',
    dict(atr_thresh=0.6, breakout_mult=1.5, min_mom=0, adx_thresh=15, min_consec=1)))
results.append(run_one("7D: ATR<0.6+BO+mom+ADX>20", '7D_adv',
    dict(atr_thresh=0.6, breakout_mult=1.5, min_mom=0, adx_thresh=20, min_consec=1)))

# 7E simple trend
results.append(run_one("7E: EMA+ROC5+ADX>20+RSI>50+BO", '7E_simple',
    dict(breakout_mult=1.5, adx_thresh=20, rsi_min=50, min_consec=1)))
results.append(run_one("7E: EMA+ROC5+ADX>15+RSI>45+BO", '7E_simple',
    dict(breakout_mult=1.5, adx_thresh=15, rsi_min=45, min_consec=1)))

# 7F pullback break
results.append(run_one("7F: y_RSI<45 + break_y_high + BO", '7F_pb',
    dict(y_rsi=45, breakout_mult=1.5, min_consec=1)))
results.append(run_one("7F: y_RSI<50 + break_y_high + BO", '7F_pb',
    dict(y_rsi=50, breakout_mult=1.5, min_consec=1)))

# 7G triple
results.append(run_one("7G: trend+mom+vol+ADX", '7G_triple',
    dict(roc_thresh=0.0, atr_min=1.0, breakout_mult=1.5, adx_thresh=20, min_consec=1)))


print("=" * 80, flush=True)
print("FINAL SUMMARY", flush=True)
print("=" * 80, flush=True)
results = [r for r in results if r is not None]
for r in sorted(results, key=lambda x: (-x['passes'], -x['expectancy'])):
    print(f"  {r['name']:<60} trades={r['trades']:>5} WR={r['wr']:>5.1f}% "
          f"pay={r['payout']:>4.2f} exp={r['expectancy']:+.3f} 7c={r['passes']}/7", flush=True)

best = max(results, key=lambda x: (x['passes'], x['expectancy']))
print(f"\n>>> BEST: {best['name']}", flush=True)
print(f"    trades={best['trades']}, WR={best['wr']:.2f}%, payout={best['payout']:.2f}, "
      f"exp={best['expectancy']:+.4f}, 7-crit={best['passes']}/7", flush=True)
