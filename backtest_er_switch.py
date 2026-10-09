"""Test stricter ER and mutually exclusive market-regime entry gates."""
from pathlib import Path
import numpy as np
import pandas as pd
import grid_search_timehunter as engine
from backtest_breakout_er import entry_signal
from backtest_breakout_er_portfolio import portfolio
from backtest_idx_costs import Costs
from analyze_portfolio_regimes import regime_proxy, attribute

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'er_switch_results'


def regime_dates(proxy,threshold):
    er=proxy.er.shift(1)
    trend=set(proxy.index[er>=threshold]);choppy=set(proxy.index[er<threshold])
    assert not trend.intersection(choppy)
    assert len(trend|choppy)==int(er.notna().sum())
    return trend,choppy


def main():
    OUT.mkdir(exist_ok=True)
    data,_=engine.load_data('stocks')
    frames={str(k):f.reset_index(drop=True) for k,f in data.groupby('Ticker',sort=True)}
    proxy=regime_proxy(data) # Keep evaluation labels fixed at .30 for fair comparisons.
    rows=[];periods=[]
    for threshold in [.3,.4,.5,.6]:
        trend,choppy=regime_dates(proxy,threshold)
        for mode in ['stock_ER_only','trend_gate_only','switch']:
            builder=None
            if mode!='stock_ER_only':
                def builder(f):
                    return entry_signal(f,threshold)&f['Date/Time'].isin(trend).to_numpy()&f.tradable.to_numpy(bool)
            secondary=None if mode!='switch' else dict(style='band_reentry',band=2,hold=20,slots=10,
                reserved=False,primary_first=True,allowed_dates=choppy,er_threshold=threshold)
            for scenario,cost in [('fees',Costs()),('spread',Costs(grid=True,ticks_per_side=1,round_lot=100))]:
                curve,t,counts=portfolio(frames,threshold=threshold,hold=None,fade=2,exit_sma=30,
                    entry_builder=builder,secondary=secondary,cost_model=cost)
                if mode!='stock_ER_only':assert t.loc[t.module=='trend','entry_date'].isin(trend).all()
                if mode=='switch':assert t.loc[t.module=='range','entry_date'].isin(choppy).all()
                if mode=='stock_ER_only' and threshold==.3:
                    old=pd.read_csv(ROOT/'fading_sma30_results'/f'breakout_ER_{scenario}_fade2_equity.csv')
                    np.testing.assert_allclose(curve.equity,old.equity,rtol=1e-10)
                name=f'{scenario}_{mode}_ER{threshold}'
                stats,_=attribute(curve,proxy,'stocks',name)
                side=stats[stats.regime=='sideways'].iloc[0];up=stats[stats.regime=='uptrend'].iloc[0]
                years=(curve.index[-1]-curve.index[0]).days/365.25
                current=proxy.loc[curve.index].er.shift(1) # Only diagnostic share; gates use full warmup above.
                row=dict(scenario=scenario,mode=mode,threshold=threshold,
                    cagr=(curve.equity.iloc[-1]/1e9)**(1/years)-1,mdd=curve.drawdown.min(),
                    records=int(curve.new_high.groupby(curve.index.to_period('M')).any().sum()),trades=len(t),
                    trend_trades=int((t.module=='trend').sum()),range_trades=int((t.module=='range').sum()),
                    cash=(curve.cash/curve.equity).mean(),sideways_cash=1-side.mean_invested_fraction,
                    sideways_annual=side.conditional_annualized,uptrend_annual=up.conditional_annualized,
                    sideways_records=side.months_record,trend_gate_day_fraction=curve.index.isin(trend).mean(),
                    choppy_gate_day_fraction=curve.index.isin(choppy).mean(),**counts)
                rows.append(row)
                for start,end in [('2000','2015'),('2016','2020'),('2021','2025')]:
                    g=curve.loc[start:end];before=curve.equity.shift(1).fillna(1e9).loc[g.index[0]]
                    periods.append(dict(variant=name,period=f'{start}-{end}',total_return=g.equity.iloc[-1]/before-1))
                curve.to_csv(OUT/f'{name}_equity.csv');t.to_csv(OUT/f'{name}_trades.csv',index=False)
                pd.DataFrame(rows).to_csv(OUT/'comparison.csv',index=False)
                pd.DataFrame(periods).to_csv(OUT/'periods.csv',index=False)
                print(name,f'CAGR{row["cagr"]:.2%}, side{row["sideways_annual"]:.2%}, idleSide{row["sideways_cash"]:.2%}, N{len(t)}',flush=True)
    lines=['# ER-based automatic entry switching','',
        'Three controls at threshold0.30/0.40/0.50/0.60: stock_ER_only raises individual-stock ER requirement only; trend_gate_only additionally permits primary entry only when previous market-proxy ER>=threshold; switch enables secondary only when previous market ER<threshold. Unknown warmup allows neither gate. Higher threshold classifies MORE days as choppy; it does not make a choppy entry intrinsically better.', '',
        'Primary unchanged: breakout priorHHV20, stockER>=threshold, no holding cap, exitSMA30 or fade2 priorATR from current Open, next tradable Open. Secondary fixed diagnostic prototype: previousClose<=previous lowerBollinger20(2std), currentClose reenters above band and rises, stockER<threshold; recoverySMA20/entryATR2stop/age20, next tradable Open. Previously this secondary did not pass standalone tests. This run tests the switching proposal, not an assertion it now has positive edge.', '',
        'Entry gates complementary at market level, main and secondary entries never enabled on same market date. Existing holdings retain their own exits when gate changes; positions from both modules can overlap. This is entry switching, not forced-liquidation or separate fixed budgets. Same sharedRp1billion/10slots/10%prior-equity size/cashcap compounding, one holding per ticker, no leverage. New main gate signals only on tradable bars so stale queued entry cannot cross regime.', '',
        'Saham2000-2025Aug15. Fee0.15%buy/0.25%sell. Spread stress uses modern grid/100share lots and1tick per side counterfactually, not actual historical quotes. Same universe/adjustment/market-impact limits. Market proxy is equal-weight supplied stocks, not IHSG. ER magnitude does not distinguish up/down; primary remains long-only breakout. Evaluation regimes remain ORIGINAL0.30 for every threshold, avoiding changing the yardstick. Sideways/uptrend annual equivalent attributes disjoint days, not standalone CAGR.', '',
        'All tests in-sample, chronological slices descriptive only. Baseline exact equity regression, complementary gates, actual entry date eligibility, accounting/attribution checks passed. No active AFL change, no adoption of unproven secondary.', '',
        '| Costs | Mode | ER | CAGR | Record months /308 | MDD | Sideways equivalent | Sideways cash | Trend trades | Choppy trades |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in pd.DataFrame(rows).itertuples():
        lines.append(f'| {r.scenario} | {r.mode} | {r.threshold} | {r.cagr:.2%} | {r.records} | {r.mdd:.2%} | {r.sideways_annual:.2%} | {r.sideways_cash:.2%} | {r.trend_trades} | {r.range_trades} |')
    (OUT/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')


if __name__=='__main__':main()
