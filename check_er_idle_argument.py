"""ER ablation on CURRENT SMA30/fade2 primary, not historical H200."""
from pathlib import Path
import numpy as np
import pandas as pd
import grid_search_timehunter as engine
from backtest_breakout_er_portfolio import portfolio
from backtest_idx_costs import Costs
from analyze_portfolio_regimes import regime_proxy, attribute

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'er_idle_argument_results'


def main():
    OUT.mkdir(exist_ok=True)
    data,_=engine.load_data('stocks')
    frames={str(k):f.reset_index(drop=True) for k,f in data.groupby('Ticker',sort=True)}
    proxy=regime_proxy(data);rows=[]
    for scenario,cost in [('fees',Costs()),('spread',Costs(grid=True,ticks_per_side=1,round_lot=100))]:
        for threshold in [.3,None]:
            label=f'{scenario}_ER{threshold}'
            curve,t,counts=portfolio(frames,threshold=threshold,hold=None,fade=2,exit_sma=30,cost_model=cost)
            if threshold==.3:
                old=pd.read_csv(ROOT/'fading_sma30_results'/f'breakout_ER_{scenario}_fade2_equity.csv')
                np.testing.assert_allclose(curve.equity,old.equity,rtol=1e-10)
            stats,_=attribute(curve,proxy,'stocks',label)
            side=stats[stats.regime=='sideways'].iloc[0]
            years=(curve.index[-1]-curve.index[0]).days/365.25
            rows.append(dict(scenario=scenario,er=threshold,cagr=(curve.equity.iloc[-1]/1e9)**(1/years)-1,
                mdd=curve.drawdown.min(),trades=len(t),sideways_entries=int((t.entry_date.map(proxy.regime)=='sideways').sum()),
                sideways_cash=1-side.mean_invested_fraction,sideways_annual=side.conditional_annualized,
                sideways_records=side.months_record,**counts))
            curve.to_csv(OUT/f'{label}_equity.csv');t.to_csv(OUT/f'{label}_trades.csv',index=False)
            pd.DataFrame(rows).to_csv(OUT/'comparison.csv',index=False)
            print(rows[-1],flush=True)
    (OUT/'METHOD.md').write_text('''# ER idle argument: controlled ablation

Current primary Breakout20+ER, no holding cap, SMA30 exit and fade2 previousATR from current Open. Only ER entry gate removed; same entry breakout, all exits, dates, fees, sizing and alphabetical ranking. 2000-2025 stocks, Rp1billion, ten slots, prior-close-equity10% sizing/cashcap compounding. Buy0.15%sell0.25%; spread scenario modern grid/100shares and1tick per side counterfactual, not historical actual quotes.

ER>=0.30 is individual-stock gate; market regime uses prior-completed-bar equal-weight proxy ER. Market sideways does not imply all stocks choppy or absence of entry. Removing ER tests existing breakout entries in choppy stocks, not every possible choppy strategy. Signal counts are stock-bar opportunities including capacity/held positions, not unique profitable trades. Baseline reproduced, accounting and return attribution reconciled. Sideways annual equivalent concatenates disjoint days, not standalone CAGR. In-sample diagnostic, no new strategy adopted or universal claim. Swinger ideal remains user-selected aspirational benchmark.
''',encoding='utf-8')


if __name__=='__main__':main()
