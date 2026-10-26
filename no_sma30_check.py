"""V1 without the Close < SMA30 exit (user question, 26 Oct 2026, exploratory). Breakout trades keep fade 2 ATR and the
failed-breakout exit; optionally the high-reset time exit (x bars without a new trade high). Monthly module unchanged.
Writes high_reset_exit_results/no_sma30.csv"""
from multiprocessing import Pool
import numpy as np, pandas as pd
import grid_search_timehunter as engine
import pit_universe as pu, pit_stale_liquidity as psl
import high_reset_exit as h

G = h.G

if __name__ == '__main__':
    st, _ = engine.load_data('stocks')
    G['fr'] = {str(k): f.reset_index(drop=True) for k, f in st.groupby('Ticker', sort=True)}
    cal = pd.Series(pd.DatetimeIndex(sorted(st['Date/Time'].unique())))
    G['me'] = set(cal.groupby(cal.dt.to_period('M')).max())
    pit, stale = pu.eligibility(G['fr'], .5), psl.stale_ok(G['fr'])
    G['gate'] = {t: pit[t] & stale[t] for t in G['fr']}
    cells = [('V1', {}), ('no SMA30', dict(sma_len=None))] + [(f'no SMA30 + reset x{x}', dict(sma_len=None, high_reset_bars=x)) for x in (10, 15, 20, 30)]
    with Pool(4) as p:
        D = pd.DataFrame(p.map(h.job, [(l, v, e) for l, e in cells for v in ('unrestricted', 'realistic')], chunksize=1))
    D.to_csv('high_reset_exit_results/no_sma30.csv', index=False)
    pd.set_option('display.width', 250)
    print(D[['label', 'version', 'win_rate', 'cagr', 'cagr_train', 'cagr_test', 'records', 'mdd', 'breakout_wr', 'breakout_e', 'breakout_bars', 'payout']].round(3).to_string(index=False))
