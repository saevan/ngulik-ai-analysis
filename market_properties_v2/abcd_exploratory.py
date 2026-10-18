"""Exploratory follow-ups to families A-D (NOT pre-registered; IDs X-...). Written after seeing the A-D primary results.
Focus: is the gap-down bounce (B4) a microstructure artifact (tick size, stale/odd opening prints, illiquidity)?
Where does the Monday effect (C2) sit (weekend overnight vs Monday intraday)? How did short-term trend persistence
(A1) evolve year by year? Writes results/ABCD_exploratory.csv."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from panel import load, universe, MAIN, SUBPERIODS
from mpstats import nw

P = load()
OUT = HERE / 'results'
ROWS = []


def add(xid, group, stat, value, n=None):
    ROWS.append(dict(id=xid, group=group, stat=stat, value=value, n=n))


def tick(price):
    """Current IDX price fractions (counterfactual for older years)."""
    return np.select([price < 200, price < 500, price < 2000, price < 5000], [1, 2, 5, 10], 25)


O, H, L, C, V, T = (P[k] for k in ['O', 'H', 'L', 'C', 'V', 'T'])
ron, rid = P['r_on'], P['r_id']
prevC = C.where(T).ffill().shift(1)
ab_id = rid.sub(rid.mean(axis=1), axis=0)
gd = (ron < np.log(.98)) & rid.notna()
gu = (ron > np.log(1.02)) & rid.notna()
liq = P['value'].rolling(60, min_periods=40).mean().shift(1)
liq_rank = liq.rank(axis=1, pct=True)
ticks_rel = pd.DataFrame(tick(prevC.values), index=C.index, columns=C.columns) / prevC
open_at_low = (O <= L * (1 + 1e-9))
open_at_high = (O >= H * (1 - 1e-9))
win = slice(*MAIN)


def summarize(xid, group, mask, series=ab_id, scale=1e4):
    s = series.where(mask).loc[win]
    daily = s.mean(axis=1)
    m, se, nd = nw(daily.values, 5)
    add(xid, group, 'day_weighted_mean', m * scale, nd)
    add(xid, group, 't', m / se if se else np.nan, nd)
    add(xid, group, 'events', int(mask.loc[win].values.sum()))


# X-B4-a: by relative tick size of the previous Close (modern fractions)
for lo, hi, lab in [(0, .004, 'tick<0.4%'), (.004, .01, '0.4-1%'), (.01, 1, 'tick>=1%')]:
    summarize('X-B4-a', f'gapdown_{lab}', gd & (ticks_rel >= lo) & (ticks_rel < hi))
    summarize('X-B3-a', f'gapup_{lab}', gu & (ticks_rel >= lo) & (ticks_rel < hi))
# X-B4-b: by liquidity tercile (60-day mean traded value known at t-1)
for lo, hi, lab in [(0, 1 / 3, 'low'), (1 / 3, 2 / 3, 'mid'), (2 / 3, 1.01, 'high')]:
    summarize('X-B4-b', f'gapdown_liq_{lab}', gd & (liq_rank > lo) & (liq_rank <= hi))
    summarize('X-B3-b', f'gapup_liq_{lab}', gu & (liq_rank > lo) & (liq_rank <= hi))
# X-B4-c: by gap size
for lo, hi, lab in [(np.log(.96), np.log(.98), '-2..-4%'), (np.log(.93), np.log(.96), '-4..-7%'), (-9, np.log(.93), '<-7%')]:
    summarize('X-B4-c', f'gapdown_{lab}', gd & (ron >= lo) & (ron < hi))
# X-B4-d: opening print at the day's Low (a single print can define both) vs not
summarize('X-B4-d', 'gapdown_open==low', gd & open_at_low)
summarize('X-B4-d', 'gapdown_open>low', gd & ~open_at_low)
summarize('X-B3-d', 'gapup_open==high', gu & open_at_high)
summarize('X-B3-d', 'gapup_open<high', gu & ~open_at_high)
add('X-B4-d', 'gapdown', 'share_open_at_low', float((gd & open_at_low).loc[win].values.sum() / gd.loc[win].values.sum()))
add('X-B4-d', 'all_days', 'share_open_at_low', float((open_at_low & T).loc[win].values.sum() / T.loc[win].values.sum()))
# X-B4-e: executable version: buy Open + 1 tick + 0.25%, sell Close - 1 tick - 0.25%, fee 0.15% / 0.25% (raw, not abnormal)
tk = pd.DataFrame(tick(O.values), index=C.index, columns=C.columns)
buy = (O + tk) * 1.0025 * 1.0015
sell = (C - pd.DataFrame(tick(C.values), index=C.index, columns=C.columns)) * .9975 * .9975
net = np.log(sell / buy).where(gd & ~P['bad'])
gross_raw = rid.where(gd)
for k, (a, b) in {'MAIN': MAIN, **SUBPERIODS}.items():
    add('X-B4-e', k, 'raw_gross_bps_event_weighted', float(gross_raw.loc[a:b].stack().mean() * 1e4))
    add('X-B4-e', k, 'net_after_tick_slip_fee_bps_event_weighted', float(net.loc[a:b].stack().mean() * 1e4))
    for lab, m in [('tick<0.4%', ticks_rel < .004), ('liq_high', liq_rank > 2 / 3)]:
        add('X-B4-e', k, f'net_bps_{lab}', float(net.where(m).loc[a:b].stack().mean() * 1e4))
# X-B4-f: all days, abnormal intraday by overnight bucket (is the gap reaction a general overnight-intraday reversal?)
for lo, hi in [(-9, -.04), (-.04, -.02), (-.02, -.005), (-.005, .005), (.005, .02), (.02, .04), (.04, 9)]:
    summarize('X-B4-f', f'r_on_{lo}_{hi}', (ron >= lo) & (ron < hi) & rid.notna())
# X-C2-a: Monday decomposition (EW r_on and r_id; Monday minus other days)
dow = pd.Series(C.index.dayofweek, index=C.index)
for name, fr in [('overnight', ron), ('intraday', rid), ('close_close', P['r_cc'])]:
    ew = fr.mean(axis=1).loc[win]
    d = dow.loc[win]
    for k, (a, b) in {'MAIN': MAIN, **SUBPERIODS}.items():
        e = ew.loc[a:b]
        dd = d.loc[a:b]
        add('X-C2-a', f'{name}_{k}', 'monday_minus_other_bps', float((e[dd == 0].mean() - e[dd != 0].mean()) * 1e4))
# X-A1-a: year-by-year TSMOM(1,1) and TSMOM(20,20), raw
lnP = P['lnP']
s1 = (np.sign(P['r_cc']).where(T) * P['fo'][1]).mean(axis=1)
s20 = (np.sign(lnP - lnP.shift(20)).where(T) * P['fo'][20]).mean(axis=1)
idx_ac = P['idx_ret']
for y in range(2000, 2026):
    a, b = f'{y}-01-01', f'{y}-12-31'
    add('X-A1-a', str(y), 'tsmom11_bps', float(s1.loc[a:b].mean() * 1e4))
    add('X-A1-a', str(y), 'tsmom2020_pct', float(s20.loc[a:b].mean() * 100))
    r = idx_ac.loc[a:b]
    add('X-A1-a', str(y), 'idx_ac1', float(r.autocorr(1)))
# X-A1-b: P4 split by universe for the decaying TSMOM effects
for u in ['all', 'pre2018']:
    c = universe(P, u)
    for lab, ser in [('tsmom11_bps', (np.sign(P['r_cc'][c]).where(T[c]) * P['fo'][1][c]).mean(axis=1) * 1e4),
                     ('tsmom2020_pct', (np.sign(lnP[c] - lnP[c].shift(20)).where(T[c]) * P['fo'][20][c]).mean(axis=1) * 100)]:
        for k in ['P3', 'P4']:
            a, b = SUBPERIODS[k]
            m, se, n = nw(ser.loc[a:b].values, 20 if '2020' in lab else 5)
            add('X-A1-b', f'{u}_{k}', lab, float(m), n)
            add('X-A1-b', f'{u}_{k}', lab + '_t', float(m / se) if se else np.nan, n)

if __name__ == '__main__':
    res = pd.DataFrame(ROWS)
    res.to_csv(OUT / 'ABCD_exploratory.csv', index=False)
    pd.set_option('display.width', 220)
    pd.set_option('display.max_rows', 400)
    print(res.to_string(index=False))
