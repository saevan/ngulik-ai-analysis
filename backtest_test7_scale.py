"""Test scaling Test 7A: shrink indicator periods, same logic"""
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


def add_ind(df, ema=50, rsi=14, atr=14, adx=14, atr_avg=50):
    df = df.copy().reset_index(drop=True)
    df['EMA'] = df['Close'].ewm(span=ema, adjust=False).mean()
    delta = df['Close'].diff()
    gain = delta.clip(lower=0); loss = (-delta).clip(lower=0)
    ag = gain.ewm(alpha=1/rsi, adjust=False).mean()
    al = loss.ewm(alpha=1/rsi, adjust=False).mean()
    rs = ag / al.replace(0, 1e-12)
    df['RSI'] = 100 - (100 / (1 + rs))
    hl = df['High'] - df['Low']
    hc = (df['High'] - df['Close'].shift()).abs()
    lc = (df['Low'] - df['Close'].shift()).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    df['ATR'] = tr.ewm(alpha=1/atr, adjust=False).mean()
    df['ATR_avg'] = df['ATR'].rolling(atr_avg).mean()
    df['ATR_ratio'] = df['ATR'] / df['ATR_avg'].replace(0, 1e-12)
    up = df['High'] - df['High'].shift()
    dn = df['Low'].shift() - df['Low']
    plus_dm = pd.Series(np.where((up > dn) & (up > 0), up, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((dn > up) & (dn > 0), dn, 0.0), index=df.index)
    atr_s = tr.ewm(alpha=1/adx, adjust=False).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1/adx, adjust=False).mean() / atr_s.replace(0, 1e-12)
    minus_di = 100 * minus_dm.ewm(alpha=1/adx, adjust=False).mean() / atr_s.replace(0, 1e-12)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, 1e-12)
    df['ADX'] = dx.ewm(alpha=1/adx, adjust=False).mean()
    return df


def run_7A(df, p, ema=50, rsi=14, atr=14, adx=14, atr_avg=50,
           rsi_thresh=45, atr_thresh=0.6, bo_mult=1.5):
    if len(df) < max(200, atr_avg*2): return None
    df = add_ind(df, ema=ema, rsi=rsi, atr=atr, adx=adx, atr_avg=atr_avg)
    n = len(df); closes = df['Close'].values; opens = df['Open'].values
    highs = df['High'].values; lows = df['Low'].values
    emas = df['EMA'].values; atrs = df['ATR'].values
    adxs = df['ADX'].values; rsis = df['RSI'].values
    atr_ratios = df['ATR_ratio'].values
    trades = []
    in_trade = False; state = {}; cd = 0
    for i in range(max(60, atr_avg), n - 1):
        atr = atrs[i]
        if np.isnan(atr) or atr <= 0: continue
        if not in_trade:
            if cd > 0: cd -= 1; continue
            if any(np.isnan(x) for x in [rsis[i], atr_ratios[i], adxs[i]]): continue
            close = closes[i]; ema = emas[i]
            rsi = rsis[i]; atr_ratio = atr_ratios[i]; adx = adxs[i]
            if (close > ema and adx > 20 and rsi < rsi_thresh
                and atr_ratio < atr_thresh
                and (highs[i] - lows[i]) > atr * bo_mult):
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
        if lows[i] <= state['stop']:
            ep = state['stop']; er = 'stop'
        elif lows[i] <= state['tr']:
            ep = state['tr']; er = 'trail'
        if ep is None and (i - state['eb']) >= state['ts']:
            ep = opens[i + 1] if i + 1 < n else closes[i]; er = 'time'
        if ep is not None:
            trades.append({'pnl_atr': (ep - state['ep']) / state['ea'],
                          'bars': i - state['eb']})
            in_trade = False; cd = 3
    return pd.DataFrame(trades) if trades else None


def summarize(df):
    if df is None or len(df) == 0: return None
    nw = (df['pnl_atr'] > 0).sum(); nl = (df['pnl_atr'] <= 0).sum()
    total = len(df)
    wins = df[df['pnl_atr'] > 0]
    losses = df[df['pnl_atr'] <= 0]
    aw = wins['pnl_atr'].mean() if nw > 0 else 0
    al = abs(losses['pnl_atr'].mean()) if nl > 0 else 0
    return {
        'trades': total, 'wr': nw/total*100, 'payout': aw/al if al > 0 else float('inf'),
        'mean': df['pnl_atr'].mean(), 'median': df['pnl_atr'].median(),
        'avg_win': aw, 'avg_loss': al,
        'expectancy': (nw/total)*aw - (nl/total)*al,
    }


def bootstrap(df, n_iter=100):
    np.random.seed(42)
    boot = []
    for _ in range(n_iter):
        s = df.sample(frac=0.5, random_state=np.random.randint(0, 100000))
        if len(s) > 0:
            nw = (s['pnl_atr'] > 0).sum()
            boot.append({'wr': nw/len(s)*100, 'mean': s['pnl_atr'].mean()})
    if not boot: return None
    return {
        'wr_std': np.std([b['wr'] for b in boot]),
        'wr_pass': sum(b['wr']>50 for b in boot)/len(boot)*100,
        'exp_pass': sum(b['mean']>0 for b in boot)/len(boot)*100,
    }


print("Loading...", flush=True)
stocks = load()
print("Done.\n", flush=True)


def run(name, ema, rsi, atr, adx, atr_avg):
    print(f">>> {name}: ema={ema}, rsi={rsi}, atr={atr}, adx={adx}, atr_avg={atr_avg}", flush=True)
    all_t = []
    for t in stocks['Ticker'].unique():
        tdf = stocks[stocks['Ticker'] == t].reset_index(drop=True)
        tr = run_7A(tdf, None, ema=ema, rsi=rsi, atr=atr, adx=adx, atr_avg=atr_avg)
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
    print(f"    trades={s['trades']:>5} WR={s['wr']:.2f}% pay={s['payout']:.2f} "
          f"mean={s['mean']:+.3f} med={s['median']:+.3f} exp={s['expectancy']:+.3f} "
          f"7c={passes}/7", flush=True)
    if s['trades'] >= 30:
        bs = bootstrap(agg)
        if bs:
            print(f"    BS: WR std={bs['wr_std']:.1f}% WR>50:{bs['wr_pass']:.0f}% "
                  f"Exp>0:{bs['exp_pass']:.0f}%", flush=True)
    s['name'] = name; s['passes'] = passes
    return s


results = []

# Baseline (the 7A winner)
results.append(run("BASELINE 7A", 50, 14, 14, 14, 50))

# Scale 0.75
results.append(run("Scale 0.75", 37, 10, 10, 10, 37))

# Scale 0.50
results.append(run("Scale 0.50", 25, 7, 7, 7, 25))

# Scale 0.25
results.append(run("Scale 0.25", 12, 4, 4, 4, 12))

print("\n" + "=" * 80, flush=True)
print("SCALING SUMMARY", flush=True)
print("=" * 80, flush=True)
for r in [r for r in results if r is not None]:
    print(f"  {r['name']:<15} trades={r['trades']:>5} WR={r['wr']:>5.1f}% "
          f"pay={r['payout']:>4.2f} exp={r['expectancy']:+.3f} 7c={r['passes']}/7", flush=True)
