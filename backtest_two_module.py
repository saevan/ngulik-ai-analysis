"""Two-module Open(i+1) portfolio: system 1 first, a choppy module that only uses idle capital.

Semantics follow backtest_breakout_er_portfolio.portfolio (pending Close-signal exits fill at the next tradable Open and
release cash before that Open's buys; budget = prior-close equity / slots capped by cash; one position per ticker;
queued signals wait for a tradable bar; rejected signals are dropped; liquidation marks; terminal close at the last bar).
With only system 1 it reproduces that engine exactly (test in test_two_module_regression.py).

modules: ordered list, index 0 = highest priority. Each module dict:
  name, cap (max positions), prepare(f) -> dict with
    'entry'   bool, entry-day aligned (signal at Close i-1 for the Open of bar i, regime/tradable masks applied)
    'sigclose' bool at Close i (module 0 only, used for preemption: a candidate for the next Open)
    'score'   optional float, entry-day aligned (higher first inside the module)
    plus any arrays the exit rule needs,
  exit_fn(d, i, p, age) -> reason or None, evaluated at each Close (p has price/ref/index/entry_atr).
preempt: True/'weakest' -> after the Close exits, if module-0 candidates for the next Open exceed the slots that will be free,
  module>0 positions with the lowest unrealized return are marked to sell at that Open (decided at the Close);
  'losers' -> only module>0 positions whose marked value is at or below their entry cost may be taken.
"""
import math
import numpy as np
import pandas as pd
from backtest_timehunter_atr import atr_previous


def run(frames,modules,cost_model=None,start='2000-01-01',capital=1e9,slots=10,preempt=False):
    data={};calendar={}
    for t,f in frames.items():
        f=f.reset_index(drop=True)
        d={k:f[k].to_numpy() for k in ['Open','High','Low','Close','tradable','Date/Time']}
        d['atr']=atr_previous(f);d['mods']=[m['prepare'](f) for m in modules]
        data[t]=d
        for i,day in enumerate(d['Date/Time']):
            if day>=np.datetime64(start):calendar.setdefault(pd.Timestamp(day),[]).append((t,i))
    cash=equity=peak=float(capital);pos={};last={};queued={};ledger=[];daily=[];rej=dict(slots=0,cash=0,cap=0)
    def quote(px,d,i,side):
        return px if cost_model is None else cost_model.quote(px,float(d['Close'][i-1]) if i else px,side)
    def close(t,i,px,why,day):
        nonlocal cash
        p=pos.pop(t);d=data[t];ref=px;px=quote(px,d,i,'sell')
        fee=p['q']*px*(cost_model.sell_fee if cost_model else 0);proceeds=p['q']*px-fee;cash+=proceeds
        ledger.append(dict(ticker=t,module=modules[p['m']]['name'],entry_date=p['date'],exit_date=day,entry_price=p['price'],exit_price=px,
            reference_exit_price=ref,pnl=proceeds-p['notional'],net_return=proceeds/p['notional']-1,bars=i-p['index']+1,reason=why))
    for day,obs in sorted(calendar.items()):
        exited=set();budget=equity/slots
        for t,i in obs:  # Phase 1: pending exits at the Open
            if t in pos and pos[t]['pending'] and data[t]['tradable'][i]:
                close(t,i,float(data[t]['Open'][i]),pos[t]['pending'],day);exited.add(t)
        cands=[]
        for t,i in obs:  # Phase 2: entries, module priority then score then ticker order
            if t in pos or t in exited:continue
            d=data[t]
            for m,md in enumerate(d['mods']):
                if md['entry'][i]:
                    if t not in queued or m<=queued[t]:queued[t]=m
                    break
            if t not in queued or not d['tradable'][i]:continue
            m=queued.pop(t);sc=d['mods'][m].get('score')
            cands.append((m,-(sc[i] if sc is not None and np.isfinite(sc[i]) else -np.inf) if sc is not None else 0.,t,i))
        cands.sort(key=lambda c:(c[0],c[1]))  # stable: ticker order kept within ties
        for m,_,t,i in cands:
            d=data[t]
            if sum(p['m']==m for p in pos.values())>=modules[m]['cap']:rej['cap']+=1;continue
            if len(pos)>=slots:rej['slots']+=1;continue
            amount=min(budget,cash)
            if amount<=capital*1e-12:rej['cash']+=1;continue
            o=float(d['Open'][i]);px=quote(o,d,i,'buy')
            if cost_model is not None:
                q=cost_model.quantity(amount,px)
                if q<=0:rej['cash']+=1;continue
                amount=q*px*(1+cost_model.buy_fee)
            else:q=amount/px
            cash-=amount
            pos[t]=dict(m=m,date=day,index=i,price=px,ref=o,q=q,notional=amount,entry_atr=float(d['atr'][i]),peak=o,pending=None)
        for t,i in obs:  # Phase 3: Close marks and exit signals
            d=data[t];c=float(d['Close'][i]);last[t]=c
            if cost_model is not None and cost_model.liquidation_mark:last[t]=quote(c,d,i,'sell')*(1-cost_model.sell_fee)
            if t not in pos:continue
            p=pos[t]
            if i==len(d['Close'])-1:
                close(t,i,c,'period_end' if d['tradable'][i] else 'period_end_mark',day);continue
            p['peak']=max(p['peak'],c)
            if p['pending'] is None:
                why=modules[p['m']]['exit_fn'](d['mods'][p['m']],i,p,i-p['index']+1)
                if why:p['pending']=why
        if preempt:
            seen={t:i for t,i in obs}
            need=sum(1 for t,i in obs if t not in pos and data[t]['mods'][0]['sigclose'][i])
            free=slots-sum(1 for p in pos.values() if p['pending'] is None)
            if need>free:
                movable=sorted([t for t,p in pos.items() if p['m']>0 and p['pending'] is None and t in seen
                    and (preempt!='losers' or last[t]/p['price']<=1)],key=lambda t:last[t]/pos[t]['price'])
                for t in movable[:need-free]:pos[t]['pending']='preempted'
        value=sum(p['q']*last[t] for t,p in pos.items());equity=cash+value
        assert cash>=-capital*1e-10 and len(pos)<=slots
        new=equity>peak+capital*1e-12;peak=max(peak,equity)
        daily.append(dict(date=day,cash=cash,market_value=value,equity=equity,positions=len(pos),
            positions_m0=sum(p['m']==0 for p in pos.values()),new_high=new,drawdown=equity/peak-1))
    assert not pos
    assert np.isclose(equity,math.fsum([capital]+[r['pnl'] for r in ledger]),rtol=1e-10,atol=capital*1e-12)
    return pd.DataFrame(daily).set_index('date'),pd.DataFrame(ledger),rej
