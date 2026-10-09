"""Causal market-proxy regime attribution; do not reset portfolio at regimes."""
from pathlib import Path
import numpy as np
import pandas as pd
import grid_search_timehunter as engine
from backtest_timehunter_cross_market import forex_daily
from backtest_breakout_er import efficiency_ratio

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'breakout_er_regime_results'


def regime_proxy(frame, threshold=.3):
    closes=frame.pivot(index='Date/Time',columns='Ticker',values='Close').sort_index().ffill()
    # Equal-weight daily return among symbols with an observed previous price.
    returns=closes.pct_change(fill_method=None).mean(axis=1).fillna(0)
    index=(1+returns).cumprod()*100
    er=efficiency_ratio(index,20)
    direction=index.diff(20)
    state=pd.Series('sideways',index=index.index)
    state.loc[(er>=threshold)&(direction>0)]='uptrend'
    state.loc[(er>=threshold)&(direction<0)]='downtrend'
    state.loc[er.isna()]='unknown'
    return pd.DataFrame(dict(proxy=index,proxy_return=returns,er=er,
        direction20=direction,regime=state.shift(1).fillna('unknown')))


def attribute(curve,proxy,market,variant):
    table=curve.join(proxy[['proxy','er','regime']],how='left')
    table['regime']=table.regime.fillna('unknown')
    table['equity_return']=table.equity.pct_change().fillna(table.equity.iloc[0]/1e9-1)
    table['log_return']=np.log1p(table.equity_return)
    table['elapsed_days']=table.index.to_series().diff().dt.total_seconds().div(86400).fillna(0)
    total_days=table.elapsed_days.sum()
    rows=[]
    for state,g in table.groupby('regime'):
        duration=g.elapsed_days.sum();logsum=g.log_return.sum()
        monthly=g.groupby(g.index.to_period('M')).agg(any_record=('new_high','any'))
        rows.append(dict(market=market,variant=variant,regime=state,
            observations=len(g),calendar_days=duration,time_fraction=duration/total_days,
            cumulative_attributed_return=np.expm1(logsum),
            conditional_annualized=np.expm1(logsum*365.25/duration) if duration>0 else np.nan,
            annualized_contribution=np.expm1(logsum*365.25/total_days),
            months_present=len(monthly),months_record=int(monthly.any_record.sum()),
            fraction_months_record=monthly.any_record.mean(),record_days=int(g.new_high.sum()),
            fraction_positive_days=(g.equity_return>0).mean(),
            mean_invested_fraction=(g.market_value/g.equity).mean()))
    result=pd.DataFrame(rows)
    actual=(table.equity.iloc[-1]/1e9)**(365.25/total_days)-1
    assert np.isclose(np.prod(1+result.annualized_contribution)-1,actual,rtol=1e-9,atol=1e-12)
    # Regime must not alter actual all-time-high flags or portfolio history.
    assert result.record_days.sum()==curve.new_high.sum()
    return result,table


def main():
    OUT.mkdir(exist_ok=True)
    stocks,_=engine.load_data('stocks');fx,_=engine.load_data('forex')
    crypto=pd.concat([pd.read_csv(p,parse_dates=['Date/Time']) for p in sorted((ROOT/'Data'/'crypto_binance_daily').glob('*.csv'))],ignore_index=True)
    all_results=[]
    for market,frame in {'stocks':stocks,'forex04':forex_daily(fx,4),'forex00':forex_daily(fx,0),'crypto':crypto}.items():
        proxy=regime_proxy(frame)
        # Appending future data must not relabel past regimes.
        cut=proxy.index[len(proxy)//2]
        before=regime_proxy(frame[frame['Date/Time']<=cut])
        pd.testing.assert_series_equal(before.regime,proxy.loc[:cut,'regime'])
        proxy.to_csv(OUT/f'{market}_proxy.csv',index_label='date')
        variants=['er_0.3','no_filter']
        if market=='stocks': variants+=['er_0.3_reverse_priority']
        for variant in variants:
            curve=pd.read_csv(ROOT/'breakout_er_compounding_results'/f'{market}_{variant}_equity.csv',parse_dates=['date']).set_index('date')
            result,table=attribute(curve,proxy,market,variant)
            all_results.append(result)
            table.to_csv(OUT/f'{market}_{variant}_daily_attribution.csv',index_label='date')
    result=pd.concat(all_results,ignore_index=True)
    result.to_csv(OUT/'regime_summary.csv',index=False)
    lines=['# Breakout ER portfolio: regime attribution',
        'Uses existing ten-slot compounding equity, initial1billion, new buy10% prior-close equity capped cash. No new trades, no exit/rule changes. Primary variant ER20>=0.30, plus no-filter control and reversed-stock-priority sensitivity.',
        'Market proxy=equal-weight daily return of available instrument closes, chained into an index; forward-fill missing closes, first listing has no return until prior price exists. Retains historical universe selection/survivorship limitations. Not IHSG, a crypto market-cap index or a USD index. Forex is a basket of the provided pair orientations.',
        'Regime uses ONLY prior completed close: ER20 of proxy>=0.30 and positive20-bar displacement =>uptrend; negative=>downtrend; lowerER=>sideways. Unknown warmup labeled separately. Lag one observation; present-day return cannot classify itself. Exposure attribution uses actual days between observations, including weekends in the interval that ends at next observation. Current er column is diagnostic only; regime column is lagged.',
        'Conditional annualized return=exp(sum of portfolio log returns in regime / calendar days assigned to regime *365.25)-1. It concatenates disjoint regime intervals; NOT the actual CAGR of a separately tradable strategy nor an expectation of future return. Annualized contribution uses total whole-history days instead, and product(1+contribution)-1 exactly reconciles to total portfolio CAGR.',
        'Record month fraction=months with a portfolio all-time daily-closing equity record ON a day labeled with this regime / months containing at least one day in the regime. Portfolio peak never resets. Months may occur in multiple regimes, so counts/fractions must not be added. First/last partial months included; regimes with few days have weak annualized estimates.',
        '| Market | Variant | Regime | Time share | Equivalent annual return | Whole-history annualized contribution | Record months / months present |',
        '|---|---|---|---:|---:|---:|---:|']
    for r in result.itertuples():
        lines.append(f'| {r.market} | {r.variant} | {r.regime} | {r.time_fraction:.2%} | {r.conditional_annualized:.2%} | {r.annualized_contribution:.2%} | {r.months_record}/{r.months_present} ({r.fraction_months_record:.2%}) |')
    lines+=['\nChecks passed: regime prefix causality on every market, exact log-return attribution/CAGR reconciliation, and no reset of all-time-high records. No claim of causal regime predictability or out-of-sample validation.']
    (OUT/'REPORT.md').write_text('\n\n'.join(lines[:6])+'\n'+'\n'.join(lines[6:]),encoding='utf-8')
    print(result[result.variant=='er_0.3'][['market','regime','time_fraction','conditional_annualized','annualized_contribution','months_present','months_record','fraction_months_record']].to_string(index=False))


if __name__=='__main__':main()
