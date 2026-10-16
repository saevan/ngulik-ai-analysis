"""Original Swinger AFL benchmark: ideal signal-bar level and causal comparators.
Decomposition modes (added 16 Oct 2026, defaults unchanged): 'ideal_clamped' = same Close-confirmed signals filled at the level but
clamped inside that bar's [Low, High] (removes physically impossible prices, keeps the same-bar confirmation look-ahead);
'close_fill' = same signals filled at that bar's Close (closing-auction approximation; decision uses the Close itself)."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
import grid_search_timehunter as engine

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'prototype_swinger_benchmark_results'


def signals(frame, swing=5):
    h=frame.High.rolling(swing).max();l=frame.Low.rolling(swing).min();c=frame.Close
    direction=pd.Series(np.where(c>h.shift(1),1,np.where(c<l.shift(1),-1,np.nan)),index=frame.index).ffill()
    # AFL IIf(ValueWhen(...)==1,sup,res); before first direction choose res.
    tsl=l.where(direction==1,h)
    buy=((c>tsl)&(c.shift(1)<=tsl.shift(1))).fillna(False)
    sell=((tsl>c)&(tsl.shift(1)<=c.shift(1))).fillna(False)
    return pd.DataFrame(dict(tsl=tsl,level=tsl.shift(1),buy=buy,sell=sell,
        next_buy=buy.shift(1,fill_value=False),next_sell=sell.shift(1,fill_value=False),
        armed_buy=(c.shift(1)<=tsl.shift(1)).fillna(False)))


def run_portfolio(frames,mode,buy_fee=.0015,sell_fee=.0025,reverse=False,slip=0.,liq_cap=None):
    data={};calendar={}
    for ticker,f in frames.items():
        f=f.reset_index(drop=True);s=signals(f)
        d={k:f[k].to_numpy() for k in ['Open','High','Low','Close','tradable','Date/Time']}
        d.update({k:s[k].to_numpy() for k in s.columns});data[ticker]=d
        d['adv']=(f.Close*f.Volume).shift(1).rolling(20).mean().to_numpy(float) if 'Volume' in f else np.full(len(f),np.nan)
        for i,day in enumerate(d['Date/Time']):
            if day>=np.datetime64('2000-01-01'):calendar.setdefault(pd.Timestamp(day),[]).append((ticker,i))
    capital=1e9;cash=capital;equity=capital;peak=capital
    positions={};lastclose={};daily=[];trades=[]
    rejected=outside=gapfills=0

    def exit_trade(ticker,i,price,reason,date):
        nonlocal cash,outside
        p=positions.pop(ticker);d=data[ticker];price=price*(1-slip)  # proportional slippage (default 0 = original)
        fee=p['qty']*price*sell_fee;proceeds=p['qty']*price-fee;cash+=proceeds
        out=price<d['Low'][i]-1e-9 or price>d['High'][i]+1e-9
        outside+=int(out)
        trades.append(dict(ticker=ticker,entry_date=p['date'],exit_date=date,
            entry_price=p['price'],exit_price=price,entry_cost=p['cost'],quantity=p['qty'],
            pnl=proceeds-p['cost'],net_return=proceeds/p['cost']-1,gross_return=price/p['price']-1,
            reason=reason,bars=i-p['index']+1,buy_fee=p['fee'],sell_fee=fee,
            entry_outside_bar=p['outside'],exit_outside_bar=out))

    for day,obs in sorted(calendar.items()):
        obs=sorted(obs,reverse=reverse);sold=set();budget=equity*.1
        # At causal-stop intraday exits don't finance today's entry orders.
        oldcash=cash;oldpositions=set(positions)
        for ticker,i in obs:
            if ticker not in positions:continue
            d=data[ticker];level=d['level'][i]
            signal=d['sell'][i] if mode in ('afl_ideal','ideal_clamped','close_fill') else d['next_sell'][i] if mode=='next_open' else np.isfinite(level) and d['Low'][i]<level
            if signal and d['tradable'][i]:
                price=level if mode=='afl_ideal' else d['Open'][i] if mode=='next_open' else min(max(level,d['Low'][i]),d['High'][i]) if mode=='ideal_clamped' \
                    else d['Close'][i] if mode=='close_fill' else min(d['Open'][i],level)
                gapfills+=int(mode=='stop_order' and d['Open'][i]<level)
                exit_trade(ticker,i,float(price),'signal',day);sold.add(ticker)
        available=cash if mode!='stop_order' else min(cash,oldcash)
        reserved_count=len(positions) if mode!='stop_order' else len(oldpositions)
        for ticker,i in obs:
            if ticker in positions or ticker in sold:continue
            d=data[ticker];level=d['level'][i]
            signal=d['buy'][i] if mode in ('afl_ideal','ideal_clamped','close_fill') else d['next_buy'][i] if mode=='next_open' else d['armed_buy'][i] and np.isfinite(level) and d['High'][i]>level
            if not signal or not d['tradable'][i]:continue
            if reserved_count>=10:rejected+=1;continue
            price=level if mode=='afl_ideal' else d['Open'][i] if mode=='next_open' else min(max(level,d['Low'][i]),d['High'][i]) if mode=='ideal_clamped' \
                else d['Close'][i] if mode=='close_fill' else max(d['Open'][i],level)
            if not np.isfinite(price) or price<=0:continue
            amount=min(budget,cash,available)
            if liq_cap is not None:amount=min(amount,liq_cap*d['adv'][i]) if np.isfinite(d['adv'][i]) else 0.
            if amount<=capital*1e-12:rejected+=1;continue
            price=price*(1+slip);qty=amount/(price*(1+buy_fee));fee=qty*price*buy_fee
            cash-=amount;available-=amount;reserved_count+=1
            out=price<d['Low'][i]-1e-9 or price>d['High'][i]+1e-9;outside+=int(out)
            gapfills+=int(mode=='stop_order' and d['Open'][i]>level)
            positions[ticker]=dict(date=day,index=i,price=float(price),qty=qty,cost=amount,fee=fee,outside=out)
        for ticker,i in obs:
            d=data[ticker];lastclose[ticker]=float(d['Close'][i])
            if ticker in positions and i==len(d['Close'])-1:
                exit_trade(ticker,i,float(d['Close'][i]),'period_end' if d['tradable'][i] else 'period_end_mark',day)
        marketvalue=sum(p['qty']*lastclose[t]*(1-slip)*(1-sell_fee) for t,p in positions.items())
        equity=cash+marketvalue
        assert cash>=-1e-4 and len(positions)<=10
        new=equity>peak+capital*1e-12;peak=max(peak,equity)
        daily.append(dict(date=day,cash=cash,market_value=marketvalue,equity=equity,positions=len(positions),new_high=new,drawdown=equity/peak-1))
    assert not positions
    assert np.isclose(equity,capital+sum(t['pnl'] for t in trades))
    return pd.DataFrame(daily).set_index('date'),pd.DataFrame(trades),dict(rejected=rejected,outside_bar_fills=outside,gap_fills=gapfills)


def main():
    OUT.mkdir(exist_ok=True)
    f,_=engine.load_data('stocks');frames={str(k):v.reset_index(drop=True) for k,v in f.groupby('Ticker',sort=True)}
    rows=[]
    for mode in ['afl_ideal','stop_order','next_open']:
        for fee in [False,True]:
            label=mode+('_net' if fee else '_gross')
            curve,trades,counts=run_portfolio(frames,mode,.0015 if fee else 0,.0025 if fee else 0)
            curve.to_csv(OUT/f'{label}_equity.csv');trades.to_csv(OUT/f'{label}_trades.csv',index=False)
            monthly=curve.groupby(curve.index.to_period('M')).agg(any_record=('new_high','any'),end_equity=('equity','last'))
            monthly.to_csv(OUT/f'{label}_months.csv')
            years=(curve.index[-1]-curve.index[0]).days/365.25
            r=trades.net_return.to_numpy();metrics=engine.metrics(r,0)
            loss=-trades.loc[trades.pnl<0,'pnl'].sum()
            rows.append(dict(variant=label,**counts,n=len(trades),wr=metrics['wr'],payout=metrics['payout'],
                money_pf=trades.loc[trades.pnl>0,'pnl'].sum()/loss,
                final_equity=curve.equity.iloc[-1],cagr=(curve.equity.iloc[-1]/1e9)**(1/years)-1,
                mdd=curve.drawdown.min(),record_months=int(monthly.any_record.sum()),months=len(monthly),
                fraction_record_months=monthly.any_record.mean(),numeric_passes=metrics['numeric_passes'],
                total_fees=trades.buy_fee.sum()+trades.sell_fee.sum()))
            print(label,'done',flush=True)
    results=pd.DataFrame(rows);results.to_csv(OUT/'comparison.csv',index=False)
    source=ROOT/'Prototype_Swinger_Source.afl'
    meta=dict(source_original=r'C:\Program Files (x86)\AmiBroker\Formulas\Custom\prototype swinger.afl',
        source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),swing=5,capital=1e9,max_positions=10,
        sizing='10% prior-close equity, includes buy fee, cash constrained; alphabetical priority; fractional units',
        start='2000-01-01',fee_buy=.0015,fee_sell=.0025,not_actual_amibroker_run=True)
    (OUT/'methodology.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
    lines=['# Prototype Swinger benchmark',json.dumps(meta,indent=2),
        'Source is installed AmiBroker original; matching Downloads/Test Algo copy. Other discovered versions change delays/fees or add averaging-down and are not used. MACD/RSI/Stoch calculations only affect chart color; final Buy/Sell are Cross(C,tsl) and Cross(tsl,C). Earlier Buy=Cross(C,res) is overwritten. No TimeHunter hold/fading/ER rules imported.',
        'res=HHV(High,5);sup=LLV(Low,5). Last nonzero directional event is Close>prior res =>+1, Close<prior sup =>-1. tsl=sup when last direction+1 else res. Original ideal fill is prior tsl on SAME BAR as Close-confirmed crossover. Mode afl_ideal reproduces that explicit level without price-bound clamping or gap correction. It is an optimistic/look-ahead benchmark, not executable causally. Counts of fills outside daily range are saved. Original file does not define external Analysis trade delays/price-bound settings; this is a clearly specified Python interpretation, not AmiBroker-native replication.',
        'stop_order comparator changes confirmation to intraday prior-level touch: flat and priorClose<=priorTSL arms buy-stop, trigger High>priorTSL, buy max(Open,priorTSL); long sell-stop triggers Low<priorTSL, sell min(Open,priorTSL). Stop level known before bar. Newly bought positions have no same-bar stop (OHLC sequencing unresolved); existing positions can exit. Intraday sale proceeds/slots conservatively not reused until next bar. Recompute TSL at each completed Close. Volume-zero triggers are skipped, not fabricated fills.',
        'next_open comparator keeps original Close crossover signals and executes next observed tradable signal bar Open; zero-volume signal days skipped. No Close fill except forced last-data liquidation. This comparator changes only signal execution timing, not the indicator rules.',
        'Same100stock data,2000–2025, ten allocations with compounding. Ideal fills omit spread/tick/round-lot adjustments on purpose; net variants keep user-approved0.15%/0.25% all-in fees. Mark open positions at closing prices less estimated exit fee; estimates are not charged repeatedly. Price-bound rules/auto-rejection/orderbook/liquidity/corporate actions not verified. Huge compounding returns on adjusted historical universe cannot be assumed achievable.',
        'Record month: at least one daily portfolio equity above all preceding daily equity and initial capital. Includes partial edge months. Never resets at trade or regime boundaries.',
        results.to_string(index=False)]
    (OUT/'REPORT.md').write_text('\n\n'.join(lines),encoding='utf-8')
    print(results.to_string(index=False))


if __name__=='__main__':main()
