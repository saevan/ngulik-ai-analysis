"""Daily marked-to-market equity using the candidate AFL's fixed notional."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import grid_search_timehunter as engine
from backtest_timehunter_cross_market import forex_daily

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'timehunter_candidate_equity_results'
CAPITAL=1_000_000_000.
NOTIONAL=100_000.


def equity_curve(frame,trades,capital=CAPITAL,notional=NOTIONAL):
    frame=frame[frame['Date/Time']>=pd.Timestamp('2000-01-01')].copy()
    dates=pd.DatetimeIndex(sorted(frame['Date/Time'].unique()))
    n=len(dates)
    cash_delta=np.zeros(n); market_value=np.zeros(n); cost=np.zeros(n); count=np.zeros(n)
    for ticker,t in trades.groupby('ticker'):
        f=frame[frame.Ticker==ticker].set_index('Date/Time').sort_index()
        close=f.Close.reindex(dates).ffill().to_numpy()
        for r in t.itertuples():
            entry=pd.Timestamp(r.entry_date);exit_date=pd.Timestamp(r.exit_date)
            a=dates.get_indexer([entry])[0];b=dates.get_indexer([exit_date])[0]
            assert 0<=a<=b<n
            quantity=notional/r.entry_price
            cash_delta[a]-=notional
            cash_delta[b]+=quantity*r.exit_price
            # At end-of-day entry is owned, exit is no longer owned.
            market_value[a:b]+=quantity*close[a:b]
            cost[a:b]+=notional;count[a:b]+=1
    cash=capital+cash_delta.cumsum()
    equity=cash+market_value
    assert np.isfinite(equity).all()
    assert (cash>=0).all(), 'Insufficient funding; need order-level portfolio backtester'
    assert count.max()<=1000
    assert np.isclose(equity[-1],capital+notional*trades.gross_return.sum())
    prior_peak=np.maximum.accumulate(np.r_[capital,equity])[:-1]
    new_high=equity>prior_peak+capital*1e-12
    peak=np.maximum.accumulate(np.r_[capital,equity])[1:]
    return pd.DataFrame(dict(cash=cash,market_value=market_value,equity=equity,
        open_positions=count,entry_cost_invested=cost,new_high=new_high,drawdown=equity/peak-1),index=dates)


def main():
    OUT.mkdir(exist_ok=True)
    stocks,_=engine.load_data('stocks');fx,_=engine.load_data('forex')
    crypto=pd.concat([pd.read_csv(p,parse_dates=['Date/Time']) for p in sorted((ROOT/'Data'/'crypto_binance_daily').glob('*.csv'))],ignore_index=True)
    rows=[]
    for market,frame in {'stocks':stocks,'forex04':forex_daily(fx,4),'forex00':forex_daily(fx,0),'crypto':crypto}.items():
        trades=pd.read_csv(ROOT/'timehunter_shared_search_results'/f'candidate_{market}_full_trades.csv')
        curve=equity_curve(frame,trades)
        curve.index.name='date';curve.to_csv(OUT/f'{market}_daily_equity.csv')
        monthly=curve.groupby(curve.index.to_period('M')).agg(end_equity=('equity','last'),
            any_new_high=('new_high','any'),end_is_new_high=('new_high','last'),observations=('equity','size'))
        # Historical peaks use all prior daily closes, not only month ends.
        monthly.to_csv(OUT/f'{market}_monthly.csv')
        years=(curve.index[-1]-curve.index[0]).days/365.25
        total=curve.equity.iloc[-1]/CAPITAL-1
        complete=monthly.iloc[1:-1]  # Sensitivity omits partial edge months.
        rows.append(dict(market=market,start=str(curve.index[0].date()),end=str(curve.index[-1].date()),
            initial_capital=CAPITAL,fixed_entry_notional=NOTIONAL,final_equity=float(curve.equity.iloc[-1]),
            total_return=total,cagr=(1+total)**(1/years)-1,max_drawdown=float(curve.drawdown.min()),
            months=len(monthly),months_any_high=int(monthly.any_new_high.sum()),
            fraction_months_any_high=float(monthly.any_new_high.mean()),
            months_end_high=int(monthly.end_is_new_high.sum()),fraction_months_end_high=float(monthly.end_is_new_high.mean()),
            interior_months=len(complete),interior_fraction_any_high=float(complete.any_new_high.mean()),
            max_positions=int(curve.open_positions.max()),max_entry_cost=float(curve.entry_cost_invested.max()),
            minimum_cash=float(curve.cash.min())))
    results=pd.DataFrame(rows);results.to_csv(OUT/'summary.csv',index=False)
    (OUT/'summary.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
    lines=['# Candidate portfolio equity: literal AFL sizing',
        'Initial equity1,000,000,000; each buy fixed100,000; fractional units, no leverage, fees, spread, interest or cash yield. Daily close mark-to-market, carried last close on dates missing for an asset. Positions closed per existing candidate ledger. This reproduces the economic sizing assumptions, not an actual AmiBroker execution. Cost-basis peak exposure reported separately from market value.',
        'CAGR=(final equity/initial equity)^(365.25/elapsed days)-1, from first available observation >=2000 to last observation for each market. Histories differ. Cash is asserted nonnegative at daily close; initial capital exceeds all possible simultaneous entry notionals for each tested universe, so capital is not restrictive here.',
        'A new highest equity means a daily Close equity strictly above ALL earlier daily Close equity values and initial capital. Monthly fraction=months containing at least one such record / months with observations. Also report month-end being a new daily-closing record. First/last partial months included; interior-only sensitivity excludes both. New highs not measured from intraday High and not from realized-only closed trades.',
        'No capital allocation strategy was previously designed; current AFL sizing was a test harness. Most capital remains idle. Do not mistake per-trade mean or sum of returns for portfolio CAGR. Same fixed-notional cash flow underlies high-record timing; changing to compounding/position limits/rebalancing requires a new portfolio simulation. Corporate actions and survivorship remain unverified.',
        results.to_string(index=False)]
    (OUT/'REPORT.md').write_text('\n\n'.join(lines),encoding='utf-8')
    print(results.to_string(index=False))


if __name__=='__main__':main()
