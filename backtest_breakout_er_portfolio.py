"""Cash-constrained ten-slot portfolio with entry sizing from prior-close equity."""
from pathlib import Path
import math
import numpy as np
import pandas as pd
import grid_search_timehunter as engine
from backtest_timehunter_atr import atr_previous
from backtest_breakout_er import entry_signal, efficiency_ratio
from backtest_timehunter_cross_market import forex_daily

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'breakout_er_compounding_results'


def portfolio(frames,threshold=.3,capital=1e9,slots=10,hold=200,fade=5.,reverse=False,cost_model=None,profit_trail=None,secondary=None,exit_sma=None,entry_builder=None,start='2000-01-01',exit_builder=None,max_age_signal=None,entry_stop_atr=None,early_failure=None,priority_builder=None):
    if entry_stop_atr is not None and entry_stop_atr<=0:
        raise ValueError('entry_stop_atr must be positive')
    if early_failure is not None and (len(early_failure)!=3 or min(early_failure)<1):
        raise ValueError('early_failure requires positive lookback, observation window and confirmation count')
    if profit_trail is not None and (len(profit_trail)!=2 or min(profit_trail)<=0):
        raise ValueError('profit_trail requires positive activation and retracement ATR multiples')
    data={};calendar={}
    for ticker,f in frames.items():
        f=f.reset_index(drop=True)
        a=atr_previous(f)
        d={k:f[k].to_numpy() for k in ['Open','High','Low','Close','tradable','Date/Time']}
        d['entry']=entry_signal(f,threshold) if entry_builder is None else entry_builder(f)
        if exit_sma is not None:
            d['sma_exit']=(f.Close<f.Close.rolling(exit_sma).mean()).to_numpy(bool)
        if exit_builder is not None:d['custom_exit']=exit_builder(f)
        d['atr']=a
        # Optional entry ranking score; builder must only use information known at bar i Open.
        if priority_builder is not None:d['priority']=np.nan_to_num(np.asarray(priority_builder(f),float),nan=-np.inf)
        if early_failure is not None:
            # Signal is previous bar. Its breakout reference excludes that signal bar.
            d['failure_level']=f.High.shift(2).rolling(early_failure[0]).max().to_numpy()
        if secondary is not None and secondary.get('style')=='inverse':
            d['range_entry']=secondary['entry_builder'](f)
            d['range_custom_exit']=secondary['exit_builder'](f)
            d['range_allowed']=f['Date/Time'].isin(secondary['allowed_dates']).to_numpy()&f.tradable.to_numpy(bool)
            d['range_entry']=d['range_entry']&d['range_allowed']
        elif secondary is not None:
            ma=f.Close.rolling(20).mean()
            choppy=efficiency_ratio(f.Close,20)<secondary.get('er_threshold',.3)
            if secondary.get('style')=='band_reentry':
                lower=ma-secondary['band']*f.Close.rolling(20).std(ddof=0)
                setup=choppy&(a>0)&(f.Close.shift(1)<=lower.shift(1))&(f.Close>lower)&(f.Close>f.Close.shift(1))
            else:
                setup=choppy&(f.Close<=ma-secondary['dip']*a)&(a>0)
            d['range_entry']=setup.shift(1,fill_value=False).to_numpy(bool)
            if 'allowed_dates' in secondary:
                d['range_allowed']=f['Date/Time'].isin(secondary['allowed_dates']).to_numpy()&choppy.shift(1,fill_value=False).to_numpy()
                d['range_entry'] = d['range_entry'] & d['range_allowed']
            d['range_mean_exit']=(f.Close>=ma).to_numpy(bool)
        d['fade']=np.isfinite(a)&(a>0)&((d['Open']-d['Low'])>=fade*a)
        data[ticker]=d
        for i,day in enumerate(d['Date/Time']):
            if day>=np.datetime64(start):
                calendar.setdefault(pd.Timestamp(day),[]).append((ticker,i))
    cash=float(capital);equity=float(capital);peak=float(capital)
    positions={};lastclose={};queued_entry={};ledger=[];daily=[]
    rejected_slots=rejected_cash=0

    def close_position(ticker,i,price,reason,day):
        nonlocal cash
        p=positions.pop(ticker)
        reference=price
        if cost_model is not None:
            prev=float(data[ticker]['Close'][i-1]) if i else price
            price=cost_model.quote(price,prev,'sell')
        sell_fee=p['quantity']*price*(cost_model.sell_fee if cost_model else 0)
        proceeds=p['quantity']*price-sell_fee;cash+=proceeds
        ledger.append(dict(ticker=ticker,entry_date=p['date'],exit_date=day,entry_price=p['price'],
            exit_price=price,quantity=p['quantity'],entry_notional=p['notional'],
            pnl=proceeds-p['notional'],gross_return=price/p['price']-1,
            bars=i-p['index']+1,reason=reason,module=p['module'],
            reference_exit_price=reference,buy_fee=p.get('buy_fee',0),sell_fee=sell_fee,
            net_return=proceeds/p['notional']-1))

    for day,observed in sorted(calendar.items()):
        observed=sorted(observed,reverse=reverse)
        exited=set()
        budget=equity/slots # Known PRIOR closing portfolio equity, not today's Close.
        # Phase1: earlier pending exits sell at Open and release cash before buys.
        for ticker,i in observed:
            d=data[ticker]
            if ticker in positions and positions[ticker]['pending'] and d['tradable'][i]:
                close_position(ticker,i,float(d['Open'][i]),positions[ticker]['pending'],day)
                exited.add(ticker)
        # Phase2: new entries at Open, alphabetical deterministic priority.
        entry_order=observed
        if secondary is not None and secondary.get('primary_first',False):
            entry_order=sorted(observed,key=lambda item:not(data[item[0]]['entry'][item[1]] or queued_entry.get(item[0])=='trend'))
        if priority_builder is not None:
            # Stable sort: higher score first, ticker order breaks ties; primary_first still dominates.
            first=(lambda item:not(data[item[0]]['entry'][item[1]] or queued_entry.get(item[0])=='trend')) if secondary is not None and secondary.get('primary_first',False) else (lambda item:False)
            entry_order=sorted(entry_order,key=lambda item:(first(item),-data[item[0]]['priority'][item[1]]))
        for ticker,i in entry_order:
            if ticker in positions or ticker in exited: continue
            d=data[ticker]
            if secondary is not None and 'range_allowed' in d and not d['range_allowed'][i] and queued_entry.get(ticker)=='range':
                queued_entry.pop(ticker)
            if d['entry'][i]: queued_entry[ticker]='trend'
            elif secondary is not None and d['range_entry'][i]: queued_entry[ticker]='range'
            if ticker not in queued_entry or not d['tradable'][i]: continue
            module=queued_entry.pop(ticker)
            if secondary is not None:
                cap=secondary['slots'] if module=='range' else (slots-secondary['slots'] if secondary['reserved'] else slots)
                if sum(p['module']==module for p in positions.values())>=cap:
                    rejected_slots+=1;continue
            if len(positions)>=slots:
                rejected_slots+=1;continue
            amount=min(budget,cash)
            if amount<=capital*1e-12:
                rejected_cash+=1;continue
            price=float(d['Open'][i])
            if cost_model is not None:
                prev=float(d['Close'][i-1]) if i else price
                price=cost_model.quote(price,prev,'buy')
                quantity=cost_model.quantity(amount,price)
                if quantity<=0:
                    rejected_cash+=1;continue
                buy_fee=quantity*price*cost_model.buy_fee
                amount=quantity*price+buy_fee
            else:
                quantity=amount/price;buy_fee=0
            cash-=amount
            positions[ticker]=dict(date=day,index=i,price=price,notional=amount,
                quantity=quantity,pending=None,buy_fee=buy_fee,
                entry_atr=d['atr'][i],peak_close=price,trail_armed=False,module=module,
                failure_level=d['failure_level'][i] if early_failure is not None else np.nan,failure_count=0)
        # Phase3: Close-time scheduled exits, terminal closures, then fade signals.
        for ticker,i in observed:
            d=data[ticker];lastclose[ticker]=float(d['Close'][i])
            if cost_model is not None and cost_model.liquidation_mark:
                prev=float(d['Close'][i-1]) if i else lastclose[ticker]
                lastclose[ticker]=cost_model.quote(lastclose[ticker],prev,'sell')*(1-cost_model.sell_fee)
            if ticker not in positions: continue
            p=positions[ticker];age=i-p['index']+1
            if p['module']=='range':
                if i==len(d['Close'])-1:
                    close_position(ticker,i,float(d['Close'][i]),'period_end' if d['tradable'][i] else 'period_end_mark',day)
                    continue
                # Independent secondary exits, signaled at Close and filled next tradable Open.
                if p['pending'] is None:
                    if secondary.get('style')=='inverse':
                        if d['range_custom_exit'][i]:p['pending']='inverse_original_buy'
                    elif d['Close'][i]<=p['price']-2*p['entry_atr']:p['pending']='range_stop'
                    elif d['range_mean_exit'][i]:p['pending']='range_mean'
                    elif age>=secondary['hold']:p['pending']='range_time'
                continue
            if hold is not None and age>=hold:
                if d['tradable'][i]:
                    close_position(ticker,i,float(d['Close'][i]),'time',day);continue
                if p['pending'] is None:p['pending']='time_delayed'
            if i==len(d['Close'])-1:
                reason='period_end' if d['tradable'][i] else 'period_end_mark'
                close_position(ticker,i,float(d['Close'][i]),reason,day);continue
            # Fixed entry ATR, completed-Close risk signal; execution remains next tradable Open.
            if early_failure is not None and age<=early_failure[1] and p['pending'] is None:
                failed=d['Close'][i]<p['failure_level'] and d['Close'][i]<p['price']
                p['failure_count']=p['failure_count']+1 if failed else 0
                if p['failure_count']>=early_failure[2]:p['pending']='early_breakout_failure'
            if entry_stop_atr is not None and np.isfinite(p['entry_atr']) and p['entry_atr']>0 and p['pending'] is None:
                if d['Close'][i]<=p['price']-entry_stop_atr*p['entry_atr']:
                    p['pending']='entry_atr_stop'
            if (hold is None or age<hold) and d['fade'][i] and p['pending'] is None:
                p['pending']='fading'
            if exit_sma is not None and d['sma_exit'][i] and p['pending'] is None:
                p['pending']='sma_exit'
            if exit_builder is not None and d['custom_exit'][i] and p['pending'] is None:
                p['pending']='custom_exit'
            if max_age_signal is not None and age>=max_age_signal and p['pending'] is None:
                p['pending']='max_age_next_open'
            if profit_trail is not None and np.isfinite(p['entry_atr']) and p['entry_atr']>0:
                # Completed-close signal, fixed ATR known before entry, next tradable Open fill.
                activation,retracement=profit_trail
                p['peak_close']=max(p['peak_close'],float(d['Close'][i]))
                p['trail_armed'] |= p['peak_close']-p['price']>=activation*p['entry_atr']
                if p['trail_armed'] and d['Close'][i]<=p['peak_close']-retracement*p['entry_atr'] and p['pending'] is None:
                    p['pending']='profit_trail'
        value=sum(p['quantity']*lastclose[t] for t,p in positions.items())
        equity=cash+value
        assert cash>=-capital*1e-10 and len(positions)<=slots
        new_high=equity>peak+capital*1e-12
        peak=max(peak,equity)
        daily.append(dict(date=day,cash=cash,market_value=value,equity=equity,
            positions=len(positions),new_high=new_high,drawdown=equity/peak-1))
    assert not positions
    # Near-total loss makes relative-to-final-equity tolerance unstable.
    # Sum accurately and allow at most 1e-12 of initial capital absolute roundoff.
    assert np.isclose(equity,math.fsum([capital]+[r['pnl'] for r in ledger]),rtol=1e-10,atol=capital*1e-12)
    return pd.DataFrame(daily).set_index('date'),pd.DataFrame(ledger),dict(rejected_slots=rejected_slots,rejected_cash=rejected_cash)


def main():
    OUT.mkdir(exist_ok=True)
    stocks,_=engine.load_data('stocks');fx,_=engine.load_data('forex')
    crypto=pd.concat([pd.read_csv(p,parse_dates=['Date/Time']) for p in sorted((ROOT/'Data'/'crypto_binance_daily').glob('*.csv'))],ignore_index=True)
    crypto['tradable']=crypto.Volume>0
    rows=[]
    for market,frame in {'stocks':stocks,'forex04':forex_daily(fx,4),'forex00':forex_daily(fx,0),'crypto':crypto}.items():
        frames={str(k):f.reset_index(drop=True) for k,f in frame.groupby('Ticker',sort=True)}
        for threshold in [None,.3]:
            label='no_filter' if threshold is None else 'er_0.3'
            for reverse in ([False,True] if market=='stocks' else [False]):
                variant=label+('_reverse_priority' if reverse else '')
                curve,trades,counts=portfolio(frames,threshold,reverse=reverse)
                months=curve.groupby(curve.index.to_period('M')).agg(any_record=('new_high','any'),end_record=('new_high','last'),end_equity=('equity','last'))
                years=(curve.index[-1]-curve.index[0]).days/365.25
                total=curve.equity.iloc[-1]/1e9-1
                s=engine.metrics(trades.gross_return.to_numpy(),0)
                loss=-trades.loc[trades.pnl<0,'pnl'].sum()
                pf=float(trades.loc[trades.pnl>0,'pnl'].sum()/loss) if loss else np.nan
                rows.append(dict(market=market,variant=variant,**counts,n=len(trades),wr=s['wr'],
                    money_pf=pf,payout=s['payout'],final_equity=curve.equity.iloc[-1],total_return=total,
                    cagr=(1+total)**(1/years)-1,mdd=curve.drawdown.min(),months=len(months),
                    record_months=int(months.any_record.sum()),record_month_fraction=months.any_record.mean(),
                    end_record_month_fraction=months.end_record.mean(),
                    interior_record_month_fraction=months.iloc[1:-1].any_record.mean(),
                    average_invested_fraction=(curve.market_value/curve.equity).mean(),
                    max_positions=int(curve.positions.max()),start=str(curve.index[0].date()),end=str(curve.index[-1].date())))
                curve.to_csv(OUT/f'{market}_{variant}_equity.csv')
                trades.to_csv(OUT/f'{market}_{variant}_trades.csv',index=False)
                months.to_csv(OUT/f'{market}_{variant}_months.csv')
                print(market,variant,'done',flush=True)
    result=pd.DataFrame(rows);result.to_csv(OUT/'comparison.csv',index=False)
    lines=['# Breakout + ER: ten-slot compounding portfolio',
        'Initial capital1,000,000,000; maximum10 positions, one per instrument. Target new entry=10% of previous daily closing portfolio equity, capped by available cash. Initial target100,000,000. No leverage/fees/cash yield. Units fractional: lot means capital allocation, not exchange round lot. No periodic rebalance, existing quantities unchanged; winners may grow above10% equity. No forced investment without signals.',
        'Entry Close>High20 of preceding bars, ER20>=0.30 optional. Same exits: hold200th Close or current Open-Low>=5*prior ATR14 then next tradable Open. Entries use only completed signal bars. Process pending Open sells, then Open buys in ticker alphabetical order, then Close exits and pending fade orders. Close-sale proceeds cannot fund earlier same-day Open buys. Insufficient-slot/cash entries rejected, fresh signals required; suspended-volume entry queues retained. No same-bar reentry.',
        'Reverse-alphabetical priority sensitivity provided for stocks. All portfolio runs start flat on first available observation>=2000, earlier indicators warmed. Source session timezone forex uncertain;04 and00 tested independently. Daily bars across instruments treated as synchronized opens/closes (no intraday timing or FX currency-conversion model). Local quote-price percentage return applied to common account notional for forex/crypto; no leveraged FX margin model.',
        'CAGR from actual first-last observation dates. A record month contains at least one daily closing equity above all prior daily closes and initial capital. Includes unrealized PnL and partial edge months. Terminal closes/marks, missing-close carry-forward follow earlier assumptions. Crypto only8 instruments and forex9, so maximum10 allocations cannot always be used. Unequal listing dates and absent signals leave cash idle.',
        'Historical observed universe, stock corporate actions/survivorship unverified, selected surviving crypto, shared/correlated samples. Not independent validation, no guaranteed expected returns. No changes to main AFL: portfolio allocation tests are Python implementations, not AmiBroker validation.',
        '| Market | Variant | Trades | Final equity | CAGR | MDD | Record months | Mean invested |',
        '|---|---|---:|---:|---:|---:|---:|---:|']
    for r in result.itertuples():
        lines.append(f'| {r.market} | {r.variant} | {r.n} | {r.final_equity:,.0f} | {r.cagr:.2%} | {r.mdd:.2%} | {r.record_months}/{r.months} ({r.record_month_fraction:.2%}) | {r.average_invested_fraction:.2%} |')
    (OUT/'REPORT.md').write_text('\n\n'.join(lines[:6])+'\n'+'\n'.join(lines[6:]),encoding='utf-8')
    print(result[['market','variant','n','final_equity','cagr','mdd','record_month_fraction','record_months','months','average_invested_fraction']].to_string(index=False))


if __name__=='__main__':main()
