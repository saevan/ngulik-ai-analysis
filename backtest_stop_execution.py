"""Breakout+ER portfolio with optional causal intraday stop orders (Swinger-like execution).

Base mode reproduces backtest_breakout_er_portfolio.portfolio(hold=None, fade=k, exit_sma=30)
exactly. Added levers, every level known before the bar trades:
- exit_mode 'fade_intraday': sell stop at current Open - k*ATR14(previous); fill at that level.
- llv: sell stop at LLV(Low, N) of the N previous bars; fill min(Open, level) when Low < level.
- entry_mode 'buy_stop': flat, previous Close <= HHV20(previous 20 Highs) and previous stock ER20>=.3;
  buy stop at that HHV20, fill max(Open, level) when High > level.
Intraday sale cash and slots are NOT reused the same day. Positions bought today get no same-bar
intraday stop (OHLC sequence unknown); their Close-based exits remain next tradable Open.
"""
import math
import numpy as np
import pandas as pd
from backtest_timehunter_atr import atr_previous
from backtest_breakout_er import entry_signal, efficiency_ratio
from backtest_idx_costs import tick_size


def limit_pct(prev):
    # Current IDX auto-reject bands applied counterfactually to all history (stress only).
    return .35 if prev<200 else .25 if prev<5000 else .20


def prepare(f,fade,llv,entry_mode,gate_dates,priority=None,channel=20):
    f=f.reset_index(drop=True);a=atr_previous(f)
    d={k:f[k].to_numpy() for k in ['Open','High','Low','Close','tradable','Date/Time']}
    d['atr']=a
    d['priority']=None if priority is None else np.nan_to_num(np.asarray(priority(f),float),nan=-np.inf)
    if entry_mode in ('next_open','next_open_vol'):
        e=entry_signal(f,.3)
        if entry_mode=='next_open_vol':
            surge=(f.Volume/f.Volume.shift(1).rolling(20).mean()>=1.5).shift(1,fill_value=False).to_numpy(bool)
            e=e&surge
        if gate_dates is not None:e=e&f['Date/Time'].isin(gate_dates).to_numpy()&f.tradable.to_numpy(bool)
        d['entry']=e
    else:
        level=f.High.shift(1).rolling(channel).max()
        er_prev=efficiency_ratio(f.Close,20).shift(1)
        armed=(f.Close.shift(1)<=level)&(er_prev>=.3)
        if gate_dates is not None:armed=armed&f['Date/Time'].isin(gate_dates)
        d['buy_level']=level.to_numpy(float);d['armed']=armed.fillna(False).to_numpy(bool)
    d['sma_exit']=(f.Close<f.Close.rolling(30).mean()).to_numpy(bool)
    d['fade']=np.isfinite(a)&(a>0)&((d['Open']-d['Low'])>=fade*a)
    d['llv']=f.Low.shift(1).rolling(llv).min().to_numpy(float) if llv else None
    d['llv5']=f.Low.shift(1).rolling(5).min().to_numpy(float)  # Swinger 'sup' known before bar i
    return d


def run(frames,fade=2.,exit_mode='close',llv=None,entry_mode='next_open',cost_model=None,start='2000-01-01',capital=1e9,slots=10,gate_dates=None,
        block_dates=None,derisk_dates=None,size_dates=None,size_factor=1.,llv_dates=None,
        gap_skip=None,gapdown_close=None,priority=None,price_limits=False,max_tick_frac=None,gapup_exit=None,
        channel=20,init_stop=None,trail_after=None,take_profit=None,breakeven=None,strict_orders=False):
    """gap_skip: skip a buy whose Open is more than gap_skip above the stop level (buy stop) or prior Close.
    gapdown_close: a pending Close-signal exit whose Open gaps below prior Close by this fraction is sold at
    that day's Close instead of the Open. priority: score known at Open; higher entries first."""
    """Condition actions use day labels known before that day's Open: block new entries, sell all at Open
    (derisk), scale new entry size, or activate the LLV stop only on those days.
    Swinger-like risk levers: init_stop 'llv5' (fixed at LLV5 of the 5 bars before entry) or 'atr2' (entry - 2 ATR),
    intraday sell stop. trail_after=k: once a Close reaches entry + k*entry ATR, a trailing intraday stop at
    LLV5 of the previous 5 bars is active. channel: HHV length of the buy stop.
    take_profit=k: sell limit at entry + k*entry ATR (fill max(Open, level) when High reaches it; if a stop is
    also hit the same bar the stop is assumed first unless the Open already passed the target).
    breakeven=b: once a Close reaches entry + b*entry ATR, an intraday stop at the entry price is active.
    strict_orders (buy_stop only): orders are decided before the Open from information known then; only the top-K armed
    names by priority (K = slots free at the Open) get a buy-stop order, and only those can fill. Without it the engine
    picks among names that actually triggered during the day (end-of-day knowledge) when slots or cash bind."""
    data={};calendar={}
    for t,f in frames.items():
        d=prepare(f,fade,llv,entry_mode,gate_dates,priority,channel);data[t]=d
        for i,day in enumerate(d['Date/Time']):
            if day>=np.datetime64(start):calendar.setdefault(pd.Timestamp(day),[]).append((t,i))
    cash=equity=peak=float(capital);positions={};lastclose={};queued=set();ledger=[];daily=[]
    def quote(price,d,i,side):
        if cost_model is None:return price
        return cost_model.quote(price,float(d['Close'][i-1]) if i else price,side)
    def close(t,i,price,reason,day):
        nonlocal cash
        p=positions.pop(t);d=data[t];ref=price;price=quote(price,d,i,'sell')
        fee=p['q']*price*(cost_model.sell_fee if cost_model else 0);proceeds=p['q']*price-fee;cash+=proceeds
        ledger.append(dict(ticker=t,entry_date=p['date'],exit_date=day,entry_price=p['price'],exit_price=price,reference_exit_price=ref,
            pnl=proceeds-p['notional'],net_return=proceeds/p['notional']-1,gross_return=price/p['price']-1,bars=i-p['index']+1,reason=reason,
            entry_outside_bar=p['outside'],exit_outside_bar=bool(ref<d['Low'][i]-1e-9 or ref>d['High'][i]+1e-9)))
        return proceeds
    for day,obs in sorted(calendar.items()):
        exited=set();budget=equity/slots*(size_factor if size_dates is not None and day in size_dates else 1.);locked=0.;intraday_exits=0
        if derisk_dates is not None and day in derisk_dates:
            for t,i in obs:
                if t in positions and data[t]['tradable'][i]:close(t,i,float(data[t]['Open'][i]),'derisk',day);exited.add(t)
        for t,i in obs:  # pending Close-signal exits at Open
            if t in positions and positions[t]['pending'] and data[t]['tradable'][i]:
                d=data[t]
                if price_limits and i and d['Open'][i]<=d['Close'][i-1]*(1-limit_pct(d['Close'][i-1]))*1.005:continue
                if gapdown_close is not None and i and d['Open'][i]<d['Close'][i-1]*(1-gapdown_close):
                    positions[t]['sell_at_close']=True;continue
                close(t,i,float(d['Open'][i]),positions[t]['pending'],day);exited.add(t)
        if gapup_exit is not None:  # take profit at Open when a held winner gaps up (gap ups fade intraday)
            for t,i in obs:
                if t in positions and t not in exited and data[t]['tradable'][i] and i:
                    d=data[t];p=positions[t]
                    if d['Open'][i]>d['Close'][i-1]*(1+gapup_exit) and d['Open'][i]>p['price']:
                        close(t,i,float(d['Open'][i]),'gapup_take_profit',day);exited.add(t)
        for t,i in obs:  # intraday stops for positions held before today
            if t not in positions or not data[t]['tradable'][i]:continue
            d=data[t];o=float(d['Open'][i]);levels=[]
            if exit_mode=='fade_intraday' and np.isfinite(d['atr'][i]) and d['atr'][i]>0 and d['Low'][i]<=o-fade*d['atr'][i]:
                levels.append((o-fade*d['atr'][i],'fade_stop'))
            if llv and (llv_dates is None or day in llv_dates) and np.isfinite(d['llv'][i]) and d['Low'][i]<d['llv'][i]:levels.append((min(o,d['llv'][i]),'llv_stop'))
            p=positions[t]
            if p.get('stop') is not None and d['Low'][i]<p['stop']:levels.append((min(o,p['stop']),'initial_stop'))
            if p.get('trail') and np.isfinite(d['llv5'][i]) and d['Low'][i]<d['llv5'][i]:levels.append((min(o,d['llv5'][i]),'trail_llv5'))
            if p.get('be') and d['Low'][i]<p['price']:levels.append((min(o,p['price']),'breakeven_stop'))
            tp=p['price']+take_profit*p['atr0'] if take_profit is not None and np.isfinite(p['atr0']) and p['atr0']>0 else None
            if tp is not None and o>=tp:
                locked+=close(t,i,o,'take_profit_open',day);exited.add(t);intraday_exits+=1;continue
            if not levels and tp is not None and d['High'][i]>=tp:
                locked+=close(t,i,float(tp),'take_profit',day);exited.add(t);intraday_exits+=1;continue
            if levels:
                # Price falls from Open: the higher triggered level is reached first.
                price,reason=max(levels);locked+=close(t,i,float(price),reason,day);exited.add(t);intraday_exits+=1
        entry_obs=obs if priority is None else sorted(obs,key=lambda x:-data[x[0]]['priority'][x[1]])
        order_book=None
        if strict_orders and entry_mode=='buy_stop':
            free=slots-len(positions)-intraday_exits;order_book=set()
            for t,i in entry_obs:  # pre-Open information only: armed level, Open-time gap rule
                if len(order_book)>=free:break
                if t in positions or t in exited:continue
                d=data[t]
                if not(d['armed'][i] and d['tradable'][i]):continue
                if gap_skip is not None and d['Open'][i]>d['buy_level'][i]*(1+gap_skip):continue
                order_book.add(t)
        for t,i in entry_obs:  # entries
            if t in positions or t in exited:continue
            d=data[t]
            if block_dates is not None and day in block_dates:
                queued.discard(t);continue
            if entry_mode!='buy_stop':
                if d['entry'][i]:queued.add(t)
                if t not in queued or not d['tradable'][i]:continue
                queued.discard(t);price=float(d['Open'][i]);outside=False
                if gap_skip is not None and i and price>d['Close'][i-1]*(1+gap_skip):continue
            else:
                if order_book is not None and t not in order_book:continue
                if not(d['armed'][i] and d['tradable'][i] and d['High'][i]>d['buy_level'][i]):continue
                if gap_skip is not None and d['Open'][i]>d['buy_level'][i]*(1+gap_skip):continue
                price=max(float(d['Open'][i]),float(d['buy_level'][i]));outside=False
            if max_tick_frac is not None and i and tick_size(d['Close'][i-1])/d['Close'][i-1]>max_tick_frac:continue
            if price_limits and i and d['High'][i]>=d['Close'][i-1]*(1+limit_pct(d['Close'][i-1]))*.995:continue
            if len(positions)+intraday_exits>=slots:continue
            amount=min(budget,cash-locked)
            if amount<=capital*1e-12:continue
            if cost_model is not None:
                price=quote(price,d,i,'buy');q=cost_model.quantity(amount,price)
                if q<=0:continue
                amount=q*price*(1+cost_model.buy_fee)
            else:q=amount/price
            cash-=amount
            stop=None
            if init_stop=='llv5' and np.isfinite(d['llv5'][i]):stop=float(d['llv5'][i])
            elif init_stop=='atr2' and np.isfinite(d['atr'][i]) and d['atr'][i]>0:stop=price-2*float(d['atr'][i])
            positions[t]=dict(date=day,index=i,price=price,notional=amount,q=q,pending=None,outside=outside,stop=stop,trail=False,atr0=float(d['atr'][i]))
        for t,i in obs:  # Close: marks and next-Open exit signals
            d=data[t];lastclose[t]=float(d['Close'][i])
            if cost_model is not None and cost_model.liquidation_mark:
                lastclose[t]=quote(lastclose[t],d,i,'sell')*(1-cost_model.sell_fee)
            if t not in positions:continue
            p=positions[t]
            if p.get('sell_at_close') and d['tradable'][i]:
                close(t,i,float(d['Close'][i]),p['pending']+'_gapdown_close',day);continue
            if i==len(d['Close'])-1:
                close(t,i,float(d['Close'][i]),'period_end' if d['tradable'][i] else 'period_end_mark',day);continue
            if breakeven is not None and np.isfinite(p['atr0']) and d['Close'][i]>=p['price']+breakeven*p['atr0']:p['be']=True
            if trail_after is not None and np.isfinite(p['atr0']) and d['Close'][i]>=p['price']+trail_after*p['atr0']:p['trail']=True
            close_fade=exit_mode=='close' or p['index']==i
            if close_fade and d['fade'][i] and p['pending'] is None:p['pending']='fading'
            if d['sma_exit'][i] and p['pending'] is None:p['pending']='sma_exit'
        value=sum(p['q']*lastclose[t] for t,p in positions.items());equity=cash+value
        assert cash>=-capital*1e-10 and len(positions)<=slots
        new=equity>peak+capital*1e-12;peak=max(peak,equity)
        daily.append(dict(date=day,cash=cash,market_value=value,equity=equity,positions=len(positions),new_high=new,drawdown=equity/peak-1))
    assert not positions
    assert np.isclose(equity,math.fsum([capital]+[r['pnl'] for r in ledger]),rtol=1e-10,atol=capital*1e-12)
    return pd.DataFrame(daily).set_index('date'),pd.DataFrame(ledger)
