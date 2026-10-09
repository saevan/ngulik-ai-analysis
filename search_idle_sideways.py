"""Independent rebound module fills spare slots after primary entries."""
from pathlib import Path
import numpy as np
import pandas as pd
import grid_search_timehunter as engine
from backtest_breakout_er_portfolio import portfolio
from backtest_idx_costs import Costs
from analyze_portfolio_regimes import regime_proxy, attribute

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'idle_sideways_results'


def main():
    OUT.mkdir(exist_ok=True)
    data,_=engine.load_data('stocks')
    frames={str(k):f.reset_index(drop=True) for k,f in data.groupby('Ticker',sort=True)}
    proxy=regime_proxy(data)
    allowed=set(proxy.index[proxy.regime=='sideways'])
    rows=[];modules=[]
    def run(scenario,band=None,hold=10,kind='combined',reverse=False):
        cfg=None if band is None else dict(style='band_reentry',band=band,hold=hold,slots=10,
            reserved=kind=='standalone',primary_first=True,allowed_dates=allowed)
        costs=Costs() if scenario=='fees' else Costs(grid=True,ticks_per_side=1,round_lot=100)
        curve,t,counts=portfolio(frames,hold=None,exit_sma=30,fade=2,cost_model=costs,secondary=cfg,reverse=reverse)
        label=f'{scenario}_{kind}_b{band}_h{hold}_reverse{reverse}'
        if band is None and not reverse:
            old=pd.read_csv(ROOT/'fading_sma30_results'/f'breakout_ER_{scenario}_fade2_equity.csv')
            np.testing.assert_allclose(curve.equity,old.equity,rtol=1e-10)
        range_t=t[t.module=='range']
        assert range_t.entry_date.isin(allowed).all()
        if kind=='standalone':assert (t.module=='range').all()
        stat,daily=attribute(curve,proxy,'stocks',label)
        side=stat[stat.regime=='sideways'].iloc[0]
        years=(curve.index[-1]-curve.index[0]).days/365.25
        r=t.net_return
        row=dict(label=label,scenario=scenario,kind=kind,band=band,hold=hold,reverse=reverse,
            cagr=(curve.equity.iloc[-1]/1e9)**(1/years)-1,mdd=curve.drawdown.min(),
            records=int(curve.new_high.groupby(curve.index.to_period('M')).any().sum()),trades=len(t),
            wr=(r>0).mean(),sideways_annual=side.conditional_annualized,sideways_records=side.months_record,
            sideways_cash=1-side.mean_invested_fraction,range_trades=len(range_t),
            range_mean_return=range_t.net_return.mean(),**counts)
        # Time slices are stability descriptions, not untouched holdout tests.
        for start,end in [('2000','2009'),('2010','2019'),('2020','2025')]:
            g=curve.loc[start:end];before=curve.equity.shift(1).fillna(1e9).loc[g.index[0]]
            row[f'return_{start}_{end}']=g.equity.iloc[-1]/before-1
        for mod,g in t.groupby('module'):
            modules.append(dict(label=label,module=mod,trades=len(g),wr=(g.net_return>0).mean(),
                mean_return=g.net_return.mean(),pnl=g.pnl.sum(),mean_bars=g.bars.mean()))
        rows.append(row)
        curve.to_csv(OUT/f'{label}_equity.csv');t.to_csv(OUT/f'{label}_trades.csv',index=False)
        pd.DataFrame(rows).to_csv(OUT/'comparison.csv',index=False)
        pd.DataFrame(modules).to_csv(OUT/'modules.csv',index=False)
        print(label,f'CAGR {row["cagr"]:.2%}, sideways {row["sideways_annual"]:.2%}, idle {row["sideways_cash"]:.2%}, range trades {len(range_t)}',flush=True)
    for scenario in ['fees','spread']:
        run(scenario)
        for band in [1,1.5,2]:
            for hold in [10,20]:run(scenario,band,hold)
    best=max((r for r in rows if r['scenario']=='spread' and r['band'] is not None),key=lambda r:r['sideways_annual'])
    for scenario in ['fees','spread']:
        run(scenario,best['band'],best['hold'],'standalone')
        run(scenario,reverse=True)
        run(scenario,best['band'],best['hold'],reverse=True)
    lines=['# Idle cash sideways module experiment','',
        'Primary is Breakout+ER, fade2 priorATR and SMA30 exit, no time cap. Secondary is new confirmed band rebound: prior Close<=prior lower Bollinger band, current Close>current lower band and >previous Close; stock ER20<0.30. Band=SMA20-k*population std20, k1/1.5/2. Secondary entry only when market proxy prior-bar regime is sideways AND stock prior-bar ER<0.30, next tradable Open. Queued secondary orders are canceled outside eligibility. Exits next tradable Open after Close>=SMA20, Close<=entry-2entryATR, or age10/20bars. Terminal marks remain.', '',
        'All eligible primary entries processed first in ticker order. Secondary fills residual slots/cash, max10 total positions, no reserved allocation, one position per ticker, no same-bar reentry or leverage. A secondary position already held can block future primary signals: primary-first is same-open priority, not a guarantee of zero opportunity cost. Standalone reserves all slots for secondary, disabling primary entries.', '',
        'Stocks2000-2025, initialRp1billion, each new position10% previous close equity cash-capped, compounding. Fee0.15%buy/0.25%sell. Fees model no spread/fractional units. Spread is modern grid/100share lot plus1tick each side counterfactually across history, not actual historical bid/ask. Existing data selection/adjustment/liquidity limitations remain.', '',
        'Six combinations per cost model plus baselines; best full-sample spread sideways annual equivalent selected for standalone/reverse sensitivity. In-sample selection, no untouched validation. Time slices are descriptive. Sideways annual equivalent attributes disjoint daily returns and is not independently executable CAGR. No automatic AFL adoption. Primary baseline exact equity regression, range entry regime eligibility, standalone module isolation, cash/slot/PnL and attribution checks passed.', '',
        '| Variant | CAGR | Sideways annual equivalent | Sideways idle | Records /308 | MDD | Secondary trades |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for r in pd.DataFrame(rows).itertuples():
        lines.append(f'| {r.label} | {r.cagr:.2%} | {r.sideways_annual:.2%} | {r.sideways_cash:.2%} | {r.records} | {r.mdd:.2%} | {r.range_trades} |')
    (OUT/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')


if __name__=='__main__':main()
