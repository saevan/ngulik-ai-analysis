"""Calibration v3 (plan: calibrate_v3_results/PLAN.md): knowledge-driven levers on top of V2, train/test selection."""
import sys
from itertools import product
from multiprocessing import Pool
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'market_properties_v2'))
from mpstats import nw
import grid_search_timehunter as engine
import search_realistic_chase_v2 as rc
import pit_universe as pu, pit_stale_liquidity as psl
from backtest_stop_execution import run
from backtest_breakout_er import efficiency_ratio
from backtest_open_next import stats
from analyze_portfolio_regimes import regime_proxy
import wr_gap_v1 as w
import monthly_filter_grid as m1

OUT = ROOT / 'calibrate_v3_results'
G = w.G
LEVERS = dict(swing=('off', 'skip_down', 'need_up'), er=(.2, .3, .5), rank=('mom120', 'er20'), crash=('off', 'on'), monthly=('off', 'on'), size=(4, 3))
REF = ('off', .2, 'mom120', 'off', 'on', 4)
BO = ('off', .2, 'mom120', 'off', 'off', 4)


def swing_sets(f):
    """Dates (tradable bars) whose PREVIOUS tradable bar had a down (LH+LL) / up (HH+HL) swing structure, pivots +-3."""
    x = f[f.tradable].reset_index(drop=True)
    h, l, n, m = x.High.to_numpy(float), x.Low.to_numpy(float), len(x), 3
    hw = pd.Series(h).rolling(2 * m + 1, center=True).max().to_numpy()
    lw = pd.Series(l).rolling(2 * m + 1, center=True).min().to_numpy()
    conf = sorted([(k + m, 0, h[k]) for k in np.flatnonzero(h == hw)] + [(k + m, 1, l[k]) for k in np.flatnonzero(l == lw)])
    up, dn, H_, L_, j = np.zeros(n, bool), np.zeros(n, bool), [], [], 0
    for i in range(n):
        while j < len(conf) and conf[j][0] <= i:
            (H_ if conf[j][1] == 0 else L_).append(conf[j][2]); j += 1
        if len(H_) >= 2 and len(L_) >= 2:
            up[i] = H_[-1] > H_[-2] and L_[-1] > L_[-2]
            dn[i] = H_[-1] < H_[-2] and L_[-1] < L_[-2]
    d = x['Date/Time']
    return set(d[1:][dn[:-1]]), set(d[1:][up[:-1]])


def kw(cfg, version):
    swing, er, rank, crash, monthly, size = cfg
    k = dict(rc.kw(m1.BASE, 'B'), failed_exit=None, er_min=er, size_div=size)
    if rank == 'er20':
        k['priority'] = lambda f: efficiency_ratio(f.Close, 20).shift(1).to_numpy(float)
    if monthly == 'on':
        k.update(w.extra())
    base = G['elig'] if version == 'realistic' else None
    if swing == 'off' and crash == 'off':
        gate = base
    else:
        gate = {}
        for t in G['fr']:
            s = set(base[t]) if base is not None else set(G['alld'][t])
            if swing == 'skip_down':
                s -= G['down'][t]
            elif swing == 'need_up':
                s &= G['up'][t]
            if crash == 'on':
                s -= G['crash']
            gate[t] = s
    if gate is not None:
        k['gate_dates'] = gate
    if version == 'realistic':
        k['liq_cap'] = .25
    return k


def job(a):
    cfg, version, period = a
    fr, start = G['fr'], '2000-01-01'
    if period == 'holdout':
        fr, start = {t: g for t, f in fr.items() if len(g := f[f['Date/Time'] <= '1999-12-31'].reset_index(drop=True))}, '1996-01-01'
    with np.errstate(invalid='ignore', divide='ignore'):
        c, t = run(fr, start=start, **kw(cfg, version))
    if period != 'holdout':
        c = c.loc[:'2025-08-15']
    s = stats(c, t)
    row = dict(cfg=cfg, version=version, period=period, cagr=s['cagr'], records=s['records'], mdd=s['mdd'], win_rate=s['wr'], trades=s['n'])
    if period == 'full':
        row['cagr_train'], row['mdd_train'] = m1.piece(c.equity, '2000-01-01', '2015-12-31')
        row['cagr_test'], row['mdd_test'] = m1.piece(c.equity, '2016-01-01', '2025-08-15')
    return row, (c.equity if period == 'full' and version == 'realistic' and cfg in G.get('keep_eq', ()) else None)


if __name__ == '__main__':
    st, _ = engine.load_data('stocks')
    G['fr'] = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
    cal = pd.Series(pd.DatetimeIndex(sorted(st['Date/Time'].unique())))
    G['me'] = set(cal.groupby(cal.dt.to_period('M')).max())
    pit, stale = pu.eligibility(G['fr'], .5), psl.stale_ok(G['fr'])
    G['gate'] = {t: pit[t] & stale[t] for t in G['fr']}       # used by w.kw elsewhere
    G['elig'] = G['gate']
    G['alld'] = {t: set(f['Date/Time']) for t, f in G['fr'].items()}
    sw = {t: swing_sets(f) for t, f in G['fr'].items()}
    G['down'] = {t: v[0] for t, v in sw.items()}
    G['up'] = {t: v[1] for t, v in sw.items()}
    px = regime_proxy(st)['proxy']
    r60 = px / px.shift(60) - 1
    G['crash'] = set(r60.index[(r60.shift(1) < -.10).to_numpy()])
    cfgs = list(product(*LEVERS.values()))
    with Pool(4) as p:
        res = p.map(job, [(c_, v, 'full') for c_ in cfgs for v in ('realistic', 'unrestricted')], chunksize=2)
    D = pd.DataFrame([r for r, _ in res])
    D[list(LEVERS)] = pd.DataFrame(D.cfg.tolist(), index=D.index)
    D.drop(columns='cfg').to_csv(OUT / 'grid.csv', index=False)
    R, U = D[D.version == 'realistic'].set_index('cfg'), D[D.version == 'unrestricted'].set_index('cfg')
    ref_r, ref_u = R.loc[[REF]].iloc[0], U.loc[[REF]].iloc[0]
    ok = (U.cagr >= ref_u.cagr - .05) & (R.mdd >= ref_r.mdd - .05) & (U.mdd >= ref_u.mdd - .05)
    elig = R[ok.reindex(R.index).fillna(False)]
    pick = elig.cagr_train.idxmax()
    # holdout + paired t for pick and reference
    G['keep_eq'] = (pick, REF)
    with Pool(2) as p:
        extra = p.map(job, [(pick, 'realistic', 'holdout'), (REF, 'realistic', 'holdout'), (pick, 'realistic', 'full'), (REF, 'realistic', 'full')])
    ho = {r['cfg']: r for r, _ in extra[:2]}
    eq = {extra[2][0]['cfg']: extra[2][1], 'REF': extra[3][1]}
    a_ = np.log(eq[pick].resample('ME').last()).diff()
    b_ = np.log(eq['REF'].resample('ME').last()).diff()
    dd = (a_ - b_).dropna()
    mu, se, _ = nw(dd.to_numpy(), 6)
    better = pick != REF and R.loc[[pick]].iloc[0].cagr_test >= ref_r.cagr_test and ho[pick]['cagr'] >= ho[REF]['cagr'] and mu / se >= 1.5
    pd.set_option('display.width', 260); pd.set_option('display.max_columns', 30)
    cols = ['cagr', 'cagr_train', 'cagr_test', 'records', 'mdd', 'win_rate']
    top = R.sort_values('cagr_train', ascending=False).head(12)[cols].join(U[['cagr', 'mdd', 'records', 'win_rate']], rsuffix='_U')
    print('TOP 12 by realistic train CAGR\n', top.round(3).to_string())
    print('\nREFERENCE V2 now', REF, ref_r[cols].round(3).to_dict(), '| unrestricted', ref_u[['cagr', 'mdd', 'records', 'win_rate']].round(3).to_dict())
    print('BREAKOUT ONLY', R.loc[[BO]].iloc[0][cols].round(3).to_dict(), '| unrestricted', U.loc[[BO]].iloc[0][['cagr', 'mdd', 'records', 'win_rate']].round(3).to_dict())
    print('\nPICK', pick, R.loc[[pick]].iloc[0][cols].round(3).to_dict(), '| unrestricted', U.loc[[pick]].iloc[0][['cagr', 'mdd', 'records', 'win_rate']].round(3).to_dict())
    print(f'holdout 1996-99 realistic: pick {ho[pick]["cagr"]:.3f} (MDD {ho[pick]["mdd"]:.3f}) vs V2 {ho[REF]["cagr"]:.3f} (MDD {ho[REF]["mdd"]:.3f}); paired monthly diff {mu*100:.3f}%/mo t={mu/se:.2f}')
    print('BETTER THAN V2 NOW:', better, '| eligible configs:', len(elig))
    for lv in LEVERS:
        m_ = D.groupby(['version', lv]).cagr.median().unstack(0)
        print(f'\nlever {lv}: median CAGR over the other levers\n', m_.round(3).to_string())
    pd.DataFrame([dict(pick=str(pick), holdout_pick=ho[pick]['cagr'], holdout_ref=ho[REF]['cagr'], t=mu / se, better=better)]).to_csv(OUT / 'selection.csv', index=False)
