"""Breakout Stop ER — portfolio backtest engine with IDX execution rules.

Strategy (parameters in Params):
  Before each Open, for every stock not held: level = highest High of the previous N bars; the stock is ARMED when the
  previous Close <= level and ER(20) of Closes at the previous bar >= er_min. Armed stocks are ranked by 120-day momentum
  measured at the previous Close skipping the last 20 days, log(C[i-21]/C[i-141]). Buy-stop orders at `level` are placed
  for the top-K ranked armed stocks, K = free slots at the Open. A stock whose Open is more than `gap` above its level is
  skipped (order cancelled at the Open) and the next ranked stock takes the order.
  Fill: only if the bar trades through the level (High > level); fill reference = max(Open, level) (a gap through the
  level fills at the Open). Never at the High/Low and never at a level known only after the bar.
  Exits, decided at the Close of bar j and filled at the next tradable Open: (a) fading: Open[j]-Low[j] >= fade_atr *
  ATR14 known before bar j; (b) Close[j] < SMA(sma_exit). If that Open gaps down more than `gap` below the previous Close,
  the sale is moved to that day's Close (closing auction) instead.
Portfolio: `slots` equal slots, each buy = equity at the previous Close / slots, capped by cash and by `liquidity` x
  average daily traded value (Close x Volume) of the previous 20 bars; shares rounded down to 100-share lots.
Execution: buy at offer = reference rounded UP to the IDX tick + `ticks` ticks, sell at bid = rounded DOWN - `ticks`;
  fees buy/sell; no fill on zero-volume bars; no buy at/above ARA, no sell at/below ARB (order stays pending).
  `delay`=1: every fill happens one bar later (triggered stop -> next Open market buy; exits one Open later).
Equity: cash + shares x Close every day. Positions open at the end stay open (reported separately).
Compatibility switches (mark='liquidation', close_at_end=True, orderbook_tradable_filter=True, no lots/limits/liquidity)
reproduce the audited research engine backtest_stop_execution.run(strict_orders=True) exactly (uts/test_regression.py).
"""
import math
from dataclasses import dataclass, asdict
import numpy as np
import pandas as pd
from .indicators import atr_previous, efficiency_ratio, tick_size, limits


@dataclass
class Params:
    channel:int=20
    er_min:float=0.30
    sma_exit:int=30
    fade_atr:float=2.0
    gap:float=0.02
    er_len:int=20
    mom_len:int=120
    mom_skip:int=20
    slots:int=10


@dataclass
class Execution:
    buy_fee:float=0.0015
    sell_fee:float=0.0025
    ticks:float=1.0
    lot:int=100
    grid:bool=True              # IDX tick grid (False: price used as is, e.g. crypto/forex)
    spread_pct:float=0.0        # proportional spread per side when grid=False
    liquidity:float|None=0.05   # max order value as share of ADV20 traded value (None = off)
    price_limits:bool=True      # ARA/ARB (stocks only)
    delay:int=0
    capital:float=1e9
    mark:str='close'            # 'close' (market price) or 'liquidation' (research compat)
    close_at_end:bool=False
    orderbook_tradable_filter:bool=False
    entry:str='stop'            # 'stop' (strategy) or 'random' (benchmark)
    random_p:float=0.0
    seed:int=0


def prepare(f,p,ex):
    f=f.reset_index(drop=True);c=f.Close
    d={k:f[k].to_numpy() for k in ['Open','High','Low','Close','tradable']}
    d['date']=f['Date/Time'].to_numpy();d['vol']=f['Volume'].to_numpy(float) if 'Volume' in f else np.zeros(len(f))
    level=f.High.shift(1).rolling(p.channel).max()
    erp=efficiency_ratio(c,p.er_len).shift(1)
    d['level']=level.to_numpy(float)
    d['armed']=((c.shift(1)<=level)&(erp>=p.er_min)).fillna(False).to_numpy(bool)
    cp=c.shift(1);d['prio']=np.nan_to_num(np.log(cp.shift(p.mom_skip)/cp.shift(p.mom_skip+p.mom_len)).to_numpy(float),nan=-np.inf)
    d['adv']=(c*f.get('Volume',0)).shift(1).rolling(20).mean().to_numpy(float)
    a=atr_previous(f)
    d['fade']=np.isfinite(a)&(a>0)&((d['Open']-d['Low'])>=p.fade_atr*a)
    d['below_sma']=(c<c.rolling(p.sma_exit).mean()).to_numpy(bool)
    if ex.entry=='random':
        rng=np.random.default_rng([ex.seed,sum(map(ord,str(f.Ticker.iloc[0]))) if 'Ticker' in f else 0])
        d['rand']=rng.random(len(f))<ex.random_p;d['rprio']=rng.random(len(f))
    return d


def run(frames,p=Params(),ex=Execution(),start='2000-01-01',end=None,market='stocks'):
    stocks=market=='stocks'
    data={};cal={}
    end_ts=np.datetime64(end) if end else None
    for t,f in frames.items():
        if end_ts is not None:f=f[f['Date/Time']<=pd.Timestamp(end)]
        if not len(f):continue
        d=prepare(f,p,ex);data[t]=d
        for i,day in enumerate(d['date']):
            if day>=np.datetime64(start):cal.setdefault(pd.Timestamp(day),[]).append((t,i))
    cash=float(ex.capital);equity=cash;peak=cash;pos={};last={};ledger=[];daily=[];queued={}

    def prev_close(d,i,ref):return float(d['Close'][i-1]) if i else ref
    def buy_px(ref,d,i):
        if ex.grid:
            tk=tick_size(prev_close(d,i,ref));return math.ceil(ref/tk+ex.ticks-1e-10)*tk
        return ref*(1+ex.spread_pct)
    def sell_px(ref,d,i):
        if ex.grid:
            tk=tick_size(prev_close(d,i,ref));return max(tk,math.floor(ref/tk-ex.ticks+1e-10)*tk)
        return ref*(1-ex.spread_pct)
    def ara_blocked(ref,px,d,i,day):
        if not(stocks and ex.price_limits and i):return False
        pc=float(d['Close'][i-1]);lo,up=limits(pc,day);tol=tick_size(pc)/2
        return ref>=up-tol or px>up+tol
    def arb_blocked(ref,d,i,day):
        if not(stocks and ex.price_limits and i):return False
        pc=float(d['Close'][i-1]);lo,up=limits(pc,day);return ref<=lo+tick_size(pc)/2
    def sell(t,i,ref,why,day,when):
        nonlocal cash
        p_=pos.pop(t);d=data[t];px=sell_px(ref,d,i)
        if stocks and ex.price_limits and ex.grid and i:
            lo,_=limits(float(d['Close'][i-1]),day);tk=tick_size(float(d['Close'][i-1]));px=max(px,math.ceil(lo/tk-1e-10)*tk)
        fee=p_['q']*px*ex.sell_fee;proceeds=p_['q']*px-fee;cash+=proceeds
        ledger.append(dict(ticker=t,entry_date=p_['date'],entry_time=p_['time'],entry_ref=p_['ref'],entry_price=p_['price'],shares=p_['q'],
            buy_fee=p_['fee'],exit_date=day,exit_time=when,exit_ref=ref,exit_price=px,sell_fee=fee,
            spread_cost=p_['q']*(p_['price']-p_['ref'])+p_['q']*(ref-px),gross_pnl=p_['q']*(ref-p_['ref']),
            pnl=proceeds-p_['notional'],net_return=proceeds/p_['notional']-1,notional=p_['notional'],bars=i-p_['index'],
            days=(pd.Timestamp(day)-pd.Timestamp(p_['date'])).days,reason=why,rank_score=p_['score']))
    def buy(t,i,ref,day,when,score,budget):
        nonlocal cash
        d=data[t];px=buy_px(ref,d,i)
        if ara_blocked(ref,px,d,i,day):return 'ara'
        amount=min(budget,cash)
        if ex.liquidity is not None:
            adv=d['adv'][i]
            if not(np.isfinite(adv) and adv>0):return 'liquidity'
            amount=min(amount,ex.liquidity*adv)
        if amount<=ex.capital*1e-12:return 'cash'
        q=amount/(px*(1+ex.buy_fee))
        if ex.lot:q=math.floor(q/ex.lot)*ex.lot
        if q<=0:return 'lot'
        fee=q*px*ex.buy_fee;notional=q*px+fee;cash-=notional
        pos[t]=dict(date=day,time=when,index=i,ref=ref,price=px,q=q,fee=fee,notional=notional,pending=None,pend_i=None,at_close=False,score=score)
        return None

    for day,obs in sorted(cal.items()):
        exited=set();budget=equity/p.slots
        # 1. Open: pending exits (signal at an earlier Close).
        for t,i in obs:
            if t not in pos:continue
            q=pos[t];d=data[t]
            if not q['pending'] or not d['tradable'][i] or i-q['pend_i']<1+ex.delay:continue
            o=float(d['Open'][i])
            if ex.delay==0 and p.gap is not None and i and o<d['Close'][i-1]*(1-p.gap):q['at_close']=True;continue
            if arb_blocked(o,d,i,day):continue
            sell(t,i,o,q['pending'],day,'09:00');exited.add(t)
        # 2. Entries.
        if ex.delay and queued:  # delayed fills of yesterday's triggers: market buy at this Open
            for t,i in sorted([(t,i) for t,i in obs if t in queued],key=lambda x:-queued[x[0]]):
                sc=queued.pop(t);d=data[t]
                if t in pos or t in exited or not d['tradable'][i] or len(pos)>=p.slots:continue
                buy(t,i,float(d['Open'][i]),day,'09:00',sc,budget)
            queued.clear()
        if ex.entry=='random':
            cands=sorted([(t,i) for t,i in obs if t not in pos and t not in exited and data[t]['rand'][i]],key=lambda x:-data[x[0]]['rprio'][x[1]])
            for t,i in cands:
                d=data[t]
                if len(pos)>=p.slots:break
                if d['tradable'][i]:buy(t,i,float(d['Open'][i]),day,'09:00',float(d['rprio'][i]),budget)
        else:
            ranked=sorted(obs,key=lambda x:-data[x[0]]['prio'][x[1]])
            free=p.slots-len(pos);book=[]
            for t,i in ranked:  # pre-Open/at-Open information only
                if len(book)>=free:break
                d=data[t]
                if t in pos or t in exited or not d['armed'][i]:continue
                if ex.orderbook_tradable_filter and not d['tradable'][i]:continue
                if p.gap is not None and d['Open'][i]>d['level'][i]*(1+p.gap):continue
                book.append((t,i))
            for t,i in book:
                d=data[t]
                if not(d['tradable'][i] and d['High'][i]>d['level'][i]):continue
                if len(pos)>=p.slots:break
                ref=max(float(d['Open'][i]),float(d['level'][i]))
                if ex.delay:queued[t]=float(d['prio'][i]);continue
                buy(t,i,ref,day,'09:00' if d['Open'][i]>=d['level'][i] else 'intraday',float(d['prio'][i]),budget)
        # 3. Close: closing-auction sales, marks, exit signals.
        for t,i in obs:
            d=data[t];c=float(d['Close'][i])
            last[t]=c if ex.mark=='close' else sell_px(c,d,i)*(1-ex.sell_fee)
            if t not in pos:continue
            q=pos[t]
            if q['at_close'] and d['tradable'][i]:
                if arb_blocked(c,d,i,day):q['at_close']=False
                else:sell(t,i,c,q['pending']+'_close_auction',day,'16:00');continue
            if ex.close_at_end and i==len(d['Close'])-1:
                sell(t,i,c,'period_end' if d['tradable'][i] else 'period_end_mark',day,'16:00');continue
            if q['pending'] is None:
                if d['fade'][i]:q['pending']='fading';q['pend_i']=i
                elif d['below_sma'][i]:q['pending']='sma_exit';q['pend_i']=i
        value=sum(q['q']*last[t] for t,q in pos.items());equity=cash+value
        assert cash>=-ex.capital*1e-9 and len(pos)<=p.slots
        new=equity>peak+ex.capital*1e-12;peak=max(peak,equity)
        daily.append(dict(date=day,equity=equity,cash=cash,market_value=value,positions=len(pos),new_high=new,drawdown=equity/peak-1))
    eq=pd.DataFrame(daily).set_index('date');tr=pd.DataFrame(ledger)
    openpos=pd.DataFrame([dict(ticker=t,entry_date=q['date'],entry_time=q['time'],entry_price=q['price'],shares=q['q'],buy_fee=q['fee'],
        notional=q['notional'],last_close=last[t],market_value=q['q']*last[t],unrealized_pnl=q['q']*last[t]-q['notional'],
        unrealized_return=q['q']*last[t]/q['notional']-1,pending_exit=q['pending']) for t,q in pos.items()])
    closed=math.fsum([ex.capital]+(tr.pnl.tolist() if len(tr) else []))
    assert np.isclose(cash,closed-sum(q['notional'] for q in pos.values()),rtol=1e-9,atol=ex.capital*1e-9)
    return eq,tr,openpos
