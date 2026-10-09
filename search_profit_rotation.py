"""Test extra activated ATR trailing exits, retaining original entry and exits."""
from pathlib import Path
import numpy as np
import pandas as pd
import grid_search_timehunter as engine
from backtest_breakout_er_portfolio import portfolio
from backtest_idx_costs import Costs

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'profit_rotation_results'


def main():
    OUT.mkdir(exist_ok=True)
    data,_=engine.load_data('stocks')
    frames={str(k):f.reset_index(drop=True) for k,f in data.groupby('Ticker',sort=True)}
    rows=[]
    def run(scenario,trail,reverse=False):
        cost=Costs() if scenario=='fees' else Costs(grid=True,ticks_per_side=1,round_lot=100)
        curve,trades,counts=portfolio(frames,cost_model=cost,profit_trail=trail,reverse=reverse)
        years=(curve.index[-1]-curve.index[0]).days/365.25
        r=trades.net_return;wins=r[r>0];losses=r[r<0]
        stats=engine.metrics(r.to_numpy(),0)
        row=dict(scenario=scenario,reverse=reverse,activation=trail[0] if trail else 0,
            retracement=trail[1] if trail else 0,cagr=(curve.equity.iloc[-1]/1e9)**(1/years)-1,
            mdd=curve.drawdown.min(),records=int(curve.new_high.groupby(curve.index.to_period('M')).any().sum()),
            trades=len(trades),mean_bars=trades.bars.mean(),wr=(r>0).mean(),
            payout=wins.mean()/-losses.mean(),mean_return=r.mean(),median_return=r.median(),
            money_pf=trades.loc[trades.pnl>0,'pnl'].sum()/-trades.loc[trades.pnl<0,'pnl'].sum(),
            trail_exits=int((trades.reason=='profit_trail').sum()),**counts)
        for start,end in [('2000','2009'),('2010','2019'),('2020','2025')]:
            g=curve.loc[start:end]
            initial=curve.equity.shift(1).fillna(1e9).loc[g.index[0]]
            row[f'return_{start}_{end}']=g.equity.iloc[-1]/initial-1
        if trail is None and not reverse:
            baseline='fees_only' if scenario=='fees' else 'fees_1tick_each_side'
            old=pd.read_csv(ROOT/'breakout_er_idx_cost_results'/f'{baseline}_equity.csv')
            np.testing.assert_allclose(curve.equity,old.equity,rtol=1e-10)
        name=f'{scenario}_a{row["activation"]}_r{row["retracement"]}_reverse{reverse}'
        curve.to_csv(OUT/f'{name}_equity.csv');trades.to_csv(OUT/f'{name}_trades.csv',index=False)
        rows.append(row);pd.DataFrame(rows).to_csv(OUT/'comparison.csv',index=False)
        print(name,f'CAGR {row["cagr"]:.2%}, records {row["records"]}/308, trades {len(trades)}',flush=True)
    for scenario in ['fees','spread']:
        for trail in [None]+[(a,r) for a in [2,4,8] for r in [1,2,4]]:
            run(scenario,trail)
    # Selected on spread CAGR; this sensitivity is not independent validation.
    best=max((r for r in rows if r['scenario']=='spread' and r['activation']>0),key=lambda r:r['cagr'])
    for scenario in ['fees','spread']:
        run(scenario,None,True)
        run(scenario,(best['activation'],best['retracement']),True)
    results=pd.DataFrame(rows)
    lines=['# Profit rotation experiment','',
        'Existing Breakout+ER, hold200, fade5 ATR unchanged. Added exit: fix ATR14 from prior completed bar at entry; arm once highest subsequent closing price minus actual entry fill >= activation*entryATR; when completed Close <= highest Close - retracement*entryATR, sell next tradable Open. Full exit; next entries still require original breakout/ER signals, cash and free slots. No same-bar reentry. Existing fade/time exits retain priority. Gaps and costs can turn a profit-trail exit into a loss. No same-bar ideal level fills.', '',
        'Stocks 2000-01-04 to 2025-08-15; Rp1 billion, ten slots, prior-close equity sizing/compounding. Buy0.15% sell0.25%. Fees scenario no spread/fractional units; spread scenario modern IDX ticks plus100-share lots and one tick per side counterfactually applied to history. Not observed historical bid/ask. Original universe/corporate-action/market-impact limitations remain.', '',
        'Grid activation2/4/8 and retracement1/2/4 ATR. Selected spread-CAGR winner tested with reverse ticker priority. Entire history is searched in-sample; time slices and reverse priority are sensitivities, not independent holdout validation. Not a claim of seven-criteria or cross-market success. Baseline exact equity regression checked; every run has engine cash/slot/PnL assertions. No active AFL change.', '',
        '| Costs | Reverse | Activate ATR | Retrace ATR | CAGR | Record months | MDD | Trades | WR | Payout |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in results.itertuples():
        lines.append(f'| {r.scenario} | {r.reverse} | {r.activation} | {r.retracement} | {r.cagr:.2%} | {r.records}/308 ({r.records/308:.2%}) | {r.mdd:.2%} | {r.trades} | {r.wr:.2%} | {r.payout:.2f} |')
    (OUT/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')


if __name__=='__main__':main()
