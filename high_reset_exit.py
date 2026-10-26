"""High-reset time exit on V1's breakout trades (plan: high_reset_exit_results/PLAN.md). Writes high_reset_exit_results/results.csv"""
from multiprocessing import Pool
import numpy as np, pandas as pd
import grid_search_timehunter as engine
import pit_universe as pu, pit_stale_liquidity as psl
from backtest_stop_execution import run
from backtest_open_next import stats
import wr_gap_v1 as w
import monthly_filter_grid as m1

G = w.G
VAR = {'R_only': dict(fade=None, sma_len=None, failed_exit=None), 'R_plus': {}, 'R_failed': dict(fade=None, sma_len=None)}


def job(a):
    label, version, extra = a
    k = dict(w.kw(version, True, None), **extra)
    with np.errstate(invalid='ignore', divide='ignore'):
        c, t = run(G['fr'], start='2000-01-01', **k)
    c = c.loc[:'2025-08-15']
    s = stats(c, t)
    m, x = t[t.kind == 'main'], t[t.kind == 'extra']
    tr, mtr = m1.piece(c.equity, '2000-01-01', '2015-12-31')
    te, mte = m1.piece(c.equity, '2016-01-01', '2025-08-15')
    return dict(label=label, version=version, cagr=s['cagr'], records=s['records'], mdd=s['mdd'], win_rate=s['wr'], expectancy=s['mean'],
                payout=s['payout'], breakout_wr=(m.net_return > 0).mean(), breakout_e=m.net_return.mean(), breakout_bars=m.bars.mean(),
                monthly_wr=(x.net_return > 0).mean(), cagr_train=tr, cagr_test=te, mdd_train=mtr, mdd_test=mte)


if __name__ == '__main__':
    st, _ = engine.load_data('stocks')
    G['fr'] = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
    cal = pd.Series(pd.DatetimeIndex(sorted(st['Date/Time'].unique())))
    G['me'] = set(cal.groupby(cal.dt.to_period('M')).max())
    pit, stale = pu.eligibility(G['fr'], .5), psl.stale_ok(G['fr'])
    G['gate'] = {t: pit[t] & stale[t] for t in G['fr']}
    cells = [('V1', {})] + [(f'{v} x{x}', dict(VAR[v], high_reset_bars=x)) for v in VAR for x in (5, 10, 15, 20, 30)]
    with Pool(4) as p:
        D = pd.DataFrame(p.map(job, [(l, v, e) for l, e in cells for v in ('unrestricted', 'realistic')], chunksize=1))
    D.to_csv('high_reset_exit_results/results.csv', index=False)
    U, R = D[D.version == 'unrestricted'].set_index('label'), D[D.version == 'realistic'].set_index('label')
    S = R[['win_rate', 'cagr', 'cagr_train', 'cagr_test', 'records', 'mdd', 'breakout_wr', 'breakout_bars']].add_prefix('R_').join(
        U[['win_rate', 'cagr', 'cagr_train', 'cagr_test', 'records', 'mdd', 'breakout_wr', 'payout']].add_prefix('U_'))
    v = S.loc['V1']
    S['improves'] = (S.R_cagr_train >= v.R_cagr_train) & (S.R_cagr_test >= v.R_cagr_test) & (S.U_cagr >= v.U_cagr - .05) & \
                    (S.R_mdd >= v.R_mdd - .05) & (S.U_mdd >= v.U_mdd - .05)
    S.loc['V1', 'improves'] = False
    S.to_csv('high_reset_exit_results/summary.csv')
    pd.set_option('display.width', 250)
    print(S.round(3).to_string())
