"""Cost sensitivity, not historical bid/ask reconstruction."""
from dataclasses import dataclass
from pathlib import Path
import math
import numpy as np
import pandas as pd
import grid_search_timehunter as engine
from backtest_breakout_er_portfolio import portfolio

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'breakout_er_idx_cost_results'


def tick_size(previous_close):
    # Present five-band grid used as an explicitly counterfactual full-history scenario.
    if previous_close<200:return 1.
    if previous_close<500:return 2.
    if previous_close<2000:return 5.
    if previous_close<5000:return 10.
    return 25.


@dataclass
class Costs:
    buy_fee:float=.0015
    sell_fee:float=.0025
    ticks_per_side:float=0.
    grid:bool=False
    round_lot:int=0
    liquidation_mark:bool=True

    def quote(self,reference,previous_close,side):
        if not self.grid:return float(reference)
        tick=tick_size(previous_close)
        if side=='buy':return math.ceil(reference/tick+self.ticks_per_side-1e-10)*tick
        return max(tick,math.floor(reference/tick-self.ticks_per_side+1e-10)*tick)

    def quantity(self,budget,price):
        q=budget/(price*(1+self.buy_fee))
        return math.floor(q/self.round_lot)*self.round_lot if self.round_lot else q


def main():
    OUT.mkdir(exist_ok=True)
    stocks,_=engine.load_data('stocks')
    frames={str(k):f.reset_index(drop=True) for k,f in stocks.groupby('Ticker',sort=True)}
    scenarios={'gross':None,'fees_only':Costs(),
        'fees_grid_roundlot':Costs(grid=True,round_lot=100),
        'fees_1tick_each_side':Costs(ticks_per_side=1,grid=True,round_lot=100),
        'fees_2ticks_each_side':Costs(ticks_per_side=2,grid=True,round_lot=100),
        'fees_3ticks_each_side':Costs(ticks_per_side=3,grid=True,round_lot=100)}
    rows=[]
    for name,model in scenarios.items():
        for reverse in ([False,True] if name=='fees_1tick_each_side' else [False]):
            label=name+('_reverse_priority' if reverse else '')
            curve,trades,counts=portfolio(frames,cost_model=model,reverse=reverse)
            monthly=curve.groupby(curve.index.to_period('M')).agg(any_record=('new_high','any'),end_record=('new_high','last'),end_equity=('equity','last'))
            years=(curve.index[-1]-curve.index[0]).days/365.25
            if name=='gross':
                old=pd.read_csv(ROOT/'breakout_er_compounding_results'/'stocks_er_0.3_equity.csv')
                np.testing.assert_allclose(curve.equity,old.equity,rtol=1e-10)
            loss=-trades.loc[trades.pnl<0,'pnl'].sum()
            rows.append(dict(scenario=label,n=len(trades),final_equity=curve.equity.iloc[-1],
                cagr=(curve.equity.iloc[-1]/1e9)**(1/years)-1,mdd=curve.drawdown.min(),
                record_months=int(monthly.any_record.sum()),months=len(monthly),
                record_month_fraction=monthly.any_record.mean(),end_record_fraction=monthly.end_record.mean(),
                total_fees=trades.buy_fee.sum()+trades.sell_fee.sum(),money_pf=trades.loc[trades.pnl>0,'pnl'].sum()/loss,
                wr=(trades.pnl>0).mean(),**counts))
            curve.to_csv(OUT/f'{label}_equity.csv')
            trades.to_csv(OUT/f'{label}_trades.csv',index=False)
            monthly.to_csv(OUT/f'{label}_months.csv')
            print(label,'done',flush=True)
    result=pd.DataFrame(rows);result.to_csv(OUT/'comparison.csv',index=False)
    noninteger=int((abs(stocks.Open-stocks.Open.round())>1e-6).sum())
    lines=['# IDX fee and spread sensitivity — not executable historical quotes',
        'User-approved all-in buy fee0.15%, sell fee0.25%. No extra tax/levy added on top. Portfolio remains initialRp1billion,10slots, target10% prior-close equity per buy including fee, cash-constrained, no leverage. Quantity and fees sized together, profits/losses compounded through actual cash. ER20>=0.30 breakoutHigh20, hold200/fade5 ATR14 unchanged.',
        'Gross reproduces previous exact curve. Fee-only uses original OHLC prices and fractional units. Net scenarios mark open holdings at modeled sell price minus hypothetical liquidation fee; daily estimate is not repeatedly charged to cash. Actual fees charged once on each buy/sell. End-of-period nontradable marks remain synthetic valuations, not proven fills.',
        'Tick scenarios use five bands from official IDX current table: previousClose<200=>1;200–<500=>2;500–<2000=>5;2000–<5000=>10;>=5000=>25. Tick fixed within the day from prior Close. Offer proxy=ceil(reference/tick+s)*tick; bid proxy=max(tick,floor(reference/tick-s)*tick). One tick EACH SIDE implies about2ticks total modeled spread, not1tick total. Grid-only scenario adds rounding but no extra tick. Reference is strategy execution Open or scheduled Close. Round quantity down to100 shares; this exchange lot is separate from10 capital slots.',
        f'CRITICAL DATA LIMITATION: {noninteger} stock Opens are noninteger. Raw unadjusted price/adjustment factors and historical bid/ask/depth are unavailable. Treat grid/round-lot scenarios as stress assumptions on the supplied series, NOT an accurate historical fill model. Current tick and100-share lot rules are applied counterfactually over2000–2025; historical tick/lot regimes, corporate-action prices, minimum prices, auction/special-board rules and price limits are not reconstructed. Tick ladder changed historically. Source: https://www.idx.id/id/produk-layanan/jam-dan-mekanisme-perdagangan/',
        'No order-book depth, queue, spread observations, market impact, fill-capacity or settlement-credit model. Buying at modeled offer/selling at modeled bid does not prove full quantity can match. Synthetic quotes may lie outside recorded OHLC. Do not clamp to observed day High/Low using future information. Results are provisional estimates; accurate reconstruction needs raw OHLC plus actions and bid/ask/depth history.',
        'CAGR uses2000-01-04–2025-08-15. Record months count at least one daily net equity above all prior daily equity and initial capital; partial edge months included. Source universe and priority selection limitations remain. Reverse ticker priority sensitivity included for1tick-side scenario.',
        '| Scenario | Trades | Final equity | CAGR | Record months | MDD |',
        '|---|---:|---:|---:|---:|---:|']
    for r in result.itertuples():lines.append(f'| {r.scenario} | {r.n} | {r.final_equity:,.0f} | {r.cagr:.2%} | {r.record_months}/{r.months} ({r.record_month_fraction:.2%}) | {r.mdd:.2%} |')
    (OUT/'REPORT.md').write_text('\n\n'.join(lines[:7])+'\n'+'\n'.join(lines[7:]),encoding='utf-8')
    print(result.to_string(index=False))


if __name__=='__main__':main()
