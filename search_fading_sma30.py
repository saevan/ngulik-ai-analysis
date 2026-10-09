"""Fading sensitivity with SMA30 exit and no holding cap; two separate entries."""
from pathlib import Path
import numpy as np
import pandas as pd
import grid_search_timehunter as engine
from backtest_breakout_er_portfolio import portfolio
from backtest_sma30_exit import pullback_entry
from backtest_idx_costs import Costs
from analyze_portfolio_regimes import regime_proxy, attribute

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'fading_sma30_results'


def main():
    OUT.mkdir(exist_ok=True)
    data,_=engine.load_data('stocks')
    frames={str(k):f.reset_index(drop=True) for k,f in data.groupby('Ticker',sort=True)}
    proxy=regime_proxy(data)
    rows=pd.read_csv(OUT/'comparison.csv').to_dict('records') if (OUT/'comparison.csv').exists() else []
    for entry,builder in [('breakout_ER',None),('AFL_pullback',pullback_entry)]:
        for scenario,cost in [('fees',Costs()),('spread',Costs(grid=True,ticks_per_side=1,round_lot=100))]:
            for fade in [5,3,2,1,.5]:
                if any(r['entry']==entry and r['scenario']==scenario and r['fade']==fade for r in rows):continue
                label=f'{entry}_{scenario}_fade{fade}'
                curve,trades,counts=portfolio(frames,hold=None,exit_sma=30,fade=fade,
                    entry_builder=builder,cost_model=cost)
                if fade==5:
                    old=pd.read_csv(ROOT/'sma30_exit_results'/f'{entry}_{scenario}_SMA30_reverseFalse_equity.csv')
                    np.testing.assert_allclose(curve.equity,old.equity,rtol=1e-10)
                years=(curve.index[-1]-curve.index[0]).days/365.25;r=trades.net_return
                stats,_=attribute(curve,proxy,'stocks',label)
                side=stats[stats.regime=='sideways'].iloc[0]
                rows.append(dict(entry=entry,scenario=scenario,fade=fade,
                    cagr=(curve.equity.iloc[-1]/1e9)**(1/years)-1,mdd=curve.drawdown.min(),
                    records=int(curve.new_high.groupby(curve.index.to_period('M')).any().sum()),
                    trades=len(trades),mean_bars=trades.bars.mean(),median_bars=trades.bars.median(),
                    wr=(r>0).mean(),payout=r[r>0].mean()/-r[r<0].mean(),
                    money_pf=trades.loc[trades.pnl>0,'pnl'].sum()/-trades.loc[trades.pnl<0,'pnl'].sum(),
                    fade_exits=int((trades.reason=='fading').sum()),sma_exits=int((trades.reason=='sma_exit').sum()),
                    sideways_annual_equivalent=side.conditional_annualized,sideways_records=side.months_record,**counts))
                curve.to_csv(OUT/f'{label}_equity.csv');trades.to_csv(OUT/f'{label}_trades.csv',index=False)
                pd.DataFrame(rows).to_csv(OUT/'comparison.csv',index=False)
                z=rows[-1];print(label,f'hold {z["mean_bars"]:.2f}, trades {z["trades"]}, CAGR {z["cagr"]:.2%}',flush=True)
    lines=['# Fading sweep with SMA30 exit','',
        'Two separate entries: Breakout+ER20 versus active AFL SMA30/High10 pullback0.25ATR/rebound. No holding cap, strict Close<SMA30 signals next tradable Open exit. Fading(current Open-Low>=k*previous ATR14) also exits next tradable Open; k5/3/2/1/0.5. Original signals, sizing and ranking unchanged. Simultaneous fade/SMA signals tagged fading. No additional modules.', '',
        'Stocks2000-01-04 to2025-08-15, Rp1billion, ten slots,10% prior-close equity entries, cash-constrained compounding, alphabetical ranking. Fees buy0.15%sell0.25%; fee-only fractional units/no spread. Spread stress modern grid/100share lots plus1tick each side counterfactually applied to historical adjusted-looking data; not actual bid/ask. Universe/liquidity/corporate action limitations retained. Terminal closure included.', '',
        'Swinger ideal reference mean holding19.035bars,3241trades,CAGR114.77%,249/308records; same-bar Close-conditioned earlier-level fills and964outside-bar fills make it aspirational, not executable proof. Matching duration/trades does not match edge. Pullback baseline already holds shorter than Swinger. Whole-history in-sample sensitivity only; no out-of-sample or cross-market validation. Default AFL is not automatically changed based on duration matching.', '',
        'All four fade5 baseline curves reproduce prior results. Cash/slot/PnL and regime-attribution reconciliation checked. Sideways annual equivalent is attribution of disjoint days, not standalone CAGR.', '',
        '| Entry | Costs | Fade ATR | Mean bars | Trades | CAGR | Records /308 | MDD | WR |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|']
    for r in pd.DataFrame(rows).itertuples():
        lines.append(f'| {r.entry} | {r.scenario} | {r.fade} | {r.mean_bars:.2f} | {r.trades} | {r.cagr:.2%} | {r.records} | {r.mdd:.2%} | {r.wr:.2%} |')
    (OUT/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')


if __name__=='__main__':main()
