"""Open(i+1) portfolio engine for the fresh-system family (new_system_search / new_system_stage2).

Every decision is taken at a completed Close i and filled at the next tradable Open:
- entry: signal at Close i (default Close > HHV55 of the previous 55 Highs, ATR14 valid) -> buy next tradable Open.
- exits evaluated at each Close j: stop Close <= entry - stop*ATR(signal bar); trailing armed once the peak Close
  reaches entry + act*ATR, then exit when Close <= peak - trail*ATR; optional early exit at bar age n when the Close
  is still <= entry*(1+thr). Exit fills at the next tradable Open.
Portfolio: Rp1bn, `slots` equal slots, each buy = equity(prior Close)/slots capped by cash, compounding, long only,
one position per ticker, rejected signals are dropped (a still-valid breakout re-signals next Close).
Rule thresholds use the raw Open as entry reference; PnL uses the cost-model fill price.
"""
import math
import numpy as np
import pandas as pd


def atr14(f):
    c=f.Close
    tr=pd.concat([f.High-f.Low,(f.High-c.shift()).abs(),(f.Low-c.shift()).abs()],axis=1).max(axis=1)
    return tr.rolling(14).mean().to_numpy(float)  # same definition as new_system_search.features


def hhv_signal(n=55):
    def f(fr):return (fr.Close>fr.High.shift(1).rolling(n).max()).to_numpy(bool)
    return f


def run(frames,signal=hhv_signal(55),stop=3.,act=2.,trail=2.5,cost_model=None,start='2000-01-01',capital=1e9,slots=10,
        priority=None,filt=None,early=None,gap_skip=None,size_fn=None):
    """priority(f)->score at the signal bar (higher first; ties alphabetical). filt(f)->bool mask ANDed with the signal.
    early=(n,thr). gap_skip=g: skip a queued buy whose Open is more than g above the signal Close.
    size_fn(f)->multiplier at the signal bar for the slot budget (1 = equity/slots)."""
    data={};calendar={}
    for t,f in frames.items():
        f=f.reset_index(drop=True);a=atr14(f)
        d={k:f[k].to_numpy() for k in ['Open','High','Low','Close','tradable','Date/Time']}
        s=np.asarray(signal(f),bool)&np.isfinite(a)&(a>0)
        if filt is not None:s=s&np.asarray(filt(f),bool)
        d['sig']=s;d['atr']=a
        d['score']=None if priority is None else np.nan_to_num(np.asarray(priority(f),float),nan=-np.inf)
        d['size']=None if size_fn is None else np.nan_to_num(np.asarray(size_fn(f),float),nan=1.)
        data[t]=d
        for i,day in enumerate(d['Date/Time']):
            if day>=np.datetime64(start):calendar.setdefault(pd.Timestamp(day),[]).append((t,i))
    cash=equity=peak_eq=float(capital);pos={};queued={};last={};ledger=[];daily=[]
    def quote(px,d,i,side):
        return px if cost_model is None else cost_model.quote(px,float(d['Close'][i-1]) if i else px,side)
    def close(t,i,px,why,day):
        nonlocal cash
        p=pos.pop(t);d=data[t];fill=quote(px,d,i,'sell')
        fee=p['q']*fill*(cost_model.sell_fee if cost_model else 0);proceeds=p['q']*fill-fee;cash+=proceeds
        ledger.append(dict(ticker=t,signal_date=d['Date/Time'][p['sig_i']],entry_date=p['date'],exit_date=day,entry_price=p['price'],
            exit_price=fill,pnl=proceeds-p['notional'],net_return=proceeds/p['notional']-1,bars=i-p['index'],reason=why,sig_i=p['sig_i'],entry_i=p['index'],exit_i=i))
    for day,obs in sorted(calendar.items()):
        exited=set();budget=equity/slots
        for t,i in obs:  # pending exits at the Open
            if t in pos and pos[t]['pending'] and data[t]['tradable'][i]:
                close(t,i,float(data[t]['Open'][i]),pos[t]['pending'],day);exited.add(t)
        cands=[]
        for t,i in obs:  # signals from the previous Close (or older, waiting for a tradable bar)
            d=data[t]
            if t in pos or t in exited:queued.pop(t,None);continue
            if i and d['sig'][i-1] and t not in queued:queued[t]=i-1
            if t in queued and d['tradable'][i]:cands.append((t,i,queued.pop(t)))
        if priority is not None:cands.sort(key=lambda c:-data[c[0]]['score'][c[2]])
        for t,i,si in cands:
            d=data[t];o=float(d['Open'][i])
            if gap_skip is not None and o>d['Close'][si]*(1+gap_skip):continue
            if len(pos)>=slots:continue
            amount=min(budget*(1. if d['size'] is None else d['size'][si]),cash)
            if amount<=capital*1e-12:continue
            px=quote(o,d,i,'buy')
            if cost_model is not None:
                q=cost_model.quantity(amount,px)
                if q<=0:continue
                amount=q*px*(1+cost_model.buy_fee)
            else:q=amount/px
            cash-=amount
            pos[t]=dict(date=day,index=i,ref=o,price=px,q=q,notional=amount,a0=float(d['atr'][si]),peak=-np.inf,armed=False,pending=None,sig_i=si)
        for t,i in obs:  # Close: marks and exit signals for the next Open
            d=data[t];c=float(d['Close'][i]);last[t]=c
            if cost_model is not None and cost_model.liquidation_mark:last[t]=quote(c,d,i,'sell')*(1-cost_model.sell_fee)
            if t not in pos:continue
            p=pos[t]
            if i==len(d['Close'])-1:close(t,i,c,'period_end',day);continue
            if p['pending']:continue
            p['peak']=max(p['peak'],c)
            if p['peak']>=p['ref']+act*p['a0']:p['armed']=True
            age=i-p['index']+1
            if stop and c<=p['ref']-stop*p['a0']:p['pending']='stop'
            elif p['armed'] and c<=p['peak']-trail*p['a0']:p['pending']='trail'
            elif early is not None and age==early[0] and c<=p['ref']*(1+early[1]):p['pending']='early'
        value=sum(p['q']*last[t] for t,p in pos.items());equity=cash+value
        assert cash>=-capital*1e-9 and len(pos)<=slots
        new=equity>peak_eq+capital*1e-12;peak_eq=max(peak_eq,equity)
        daily.append(dict(date=day,cash=cash,market_value=value,equity=equity,positions=len(pos),new_high=new,drawdown=equity/peak_eq-1))
    assert not pos
    assert np.isclose(equity,math.fsum([capital]+[r['pnl'] for r in ledger]),rtol=1e-9,atol=capital*1e-9)
    return pd.DataFrame(daily).set_index('date'),pd.DataFrame(ledger)


def stats(c,t):
    m=c.new_high.groupby(c.index.to_period('M')).any();r=t.net_return;w=r>0
    return dict(cagr=(c.equity.iloc[-1]/1e9)**(365.25/(c.index[-1]-c.index[0]).days)-1,records=int(m.sum()),months=len(m),mdd=c.drawdown.min(),
        n=len(t),wr=w.mean(),avg_win=r[w].mean(),avg_loss=-r[~w].mean(),payout=r[w].mean()/-r[~w].mean(),mean=r.mean(),median=r.median(),
        win_bars=t.bars[w].mean(),loss_bars=t.bars[~w].mean(),mean_bars=t.bars.mean(),invested=(c.market_value/c.equity).mean(),
        full_slots=(c.positions>=10).mean())
