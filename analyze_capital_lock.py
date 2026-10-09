"""Reconstruct daily open holdings to distinguish cash idle from capital tied up."""
from pathlib import Path
import numpy as np
import pandas as pd
import grid_search_timehunter as engine

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'capital_lock_results'


def main():
    OUT.mkdir(exist_ok=True)
    data,_=engine.load_data('stocks')
    frames={str(k):f.sort_values('Date/Time').set_index('Date/Time') for k,f in data.groupby('Ticker')}
    proxy=pd.read_csv(ROOT/'breakout_er_regime_results/stocks_proxy.csv',parse_dates=['date']).set_index('date')
    rows=[];trade_rows=[]
    variants={'our_ER':(ROOT/'breakout_er_idx_cost_results','fees_only'),
              'swinger_ideal':(ROOT/'prototype_swinger_benchmark_results','afl_ideal_net'),
              'swinger_next_open':(ROOT/'prototype_swinger_benchmark_results','next_open_net')}
    for label,(base,name) in variants.items():
        curve=pd.read_csv(base/f'{name}_equity.csv',parse_dates=['date']).set_index('date')
        trades=pd.read_csv(base/f'{name}_trades.csv',parse_dates=['entry_date','exit_date'])
        daily=pd.DataFrame(0.,index=curve.index,columns=['reconstructed_value','losing_value','age50_value','age100_value','age50_losing_value','age100_losing_value','age50_flat_value','value_age_sum'])
        for t in trades.itertuples():
            f=frames[t.ticker]
            days=curve.index[(curve.index>=t.entry_date)&(curve.index<t.exit_date)]
            if not len(days):continue
            close=f.Close.reindex(curve.index).ffill().loc[days]
            age=f.index.searchsorted(days,side='right')-f.index.searchsorted(t.entry_date,side='left')
            value=t.quantity*close*.9975
            cost=t.entry_notional if hasattr(t,'entry_notional') else t.entry_cost
            ret=value/cost-1
            daily.loc[days,'reconstructed_value']+=value
            daily.loc[days,'value_age_sum']+=value*age
            for col,mask in [('losing_value',ret<0),('age50_value',age>=50),('age100_value',age>=100),
                    ('age50_losing_value',(age>=50)&(ret<0)),('age100_losing_value',(age>=100)&(ret<0)),
                    ('age50_flat_value',(age>=50)&(ret.abs()<=.05))]:
                daily.loc[days,col]+=value.where(mask,0)
            trade_rows.append(dict(variant=label,ticker=t.ticker,entry_date=t.entry_date,exit_date=t.exit_date,
                bars=t.bars,final_net_return=t.net_return,observed_close_days=len(days),
                losing_close_days=int((ret<0).sum()),age100_losing_days=int(((age>=100)&(ret<0)).sum())))
        np.testing.assert_allclose(daily.reconstructed_value,curve.market_value,rtol=1e-9,atol=1e-4)
        daily=daily.join(curve[['cash','equity','positions']]).join(proxy[['regime']])
        for regime in ['all','sideways','uptrend','downtrend']:
            g=daily if regime=='all' else daily[daily.regime==regime]
            row=dict(variant=label,regime=regime,days=len(g),cash_fraction=(g.cash/g.equity).mean(),
                cash_gt20_days=(g.cash/g.equity>.2).mean(),full_slot_days=(g.positions==10).mean(),
                average_positions=g.positions.mean(),value_weighted_age=(g.value_age_sum/g.reconstructed_value.replace(0,np.nan)).mean())
            for col in ['losing_value','age50_value','age100_value','age50_losing_value','age100_losing_value','age50_flat_value']:
                row[col+'_equity_fraction']=(g[col]/g.equity).mean()
            rows.append(row)
        daily.to_csv(OUT/f'{label}_daily.csv')
    result=pd.DataFrame(rows);result.to_csv(OUT/'summary.csv',index=False)
    pd.DataFrame(trade_rows).to_csv(OUT/'trade_durations.csv',index=False)
    print(result[result.regime=='sideways'].to_string(index=False))
    (OUT/'METHODOLOGY.md').write_text('''# Capital lock diagnosis

Reconstructs exact daily closing open holdings from existing fee-only portfolio ledgers. Entry day included, exit day excluded; sold positions are already in cash at that close. Quantity times forward-filled Close times (1-0.25% hypothetical sell fee) reconciles to saved market_value for all three variants. Fees buy0.15% sell0.25%, no spread, same dates/capital. Does not use final trade outcomes to classify today's unrealized PnL.

Idle = cash/equity. Losing = current liquidation value below actual entry cost including buy fee. Age counts instrument bars since entry inclusive, not calendar days. Old positions use diagnostic thresholds50/100bars, not optimized exit rules. Flat = net unrealized return within +/-5% and age>=50; overlaps losing. Fractions are means of daily marked value/equity, not fractions of original principal or cumulative losses. Value-weighted age is calculated each day then averaged. These are descriptive categories, not proof of wasted capital: an old loser can later recover and an old winner can keep compounding.

Sideways uses saved prior-completed-bar equal-weight market proxy ER regime, not each stock's ER. Daily closing snapshots cannot measure intraday idle time. No cash interest. Module is existing Breakout+ER H200, not the active pullback AFL. Swinger ideal retains documented noncausal fills and is aspirational only; next-open comparator preserves completed-close signals more closely. No execution logic or AFL changed.

Whole-history rejected entry counts are signal events, not unique trades or proven missed profits. Correlation between occupancy and rejected entries does not establish better results from forced selling. Prior H20/H50 and activated-profit-trail tests already showed that releasing slots indiscriminately need not improve net results. An opportunity-cost claim needs a matched counterfactual with replacement trade, costs and capital constraints.
''',encoding='utf-8')


if __name__=='__main__':main()
