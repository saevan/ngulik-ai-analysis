"""Metrics exactly as defined in the UTS brief (section 4). Inputs: daily equity (index date, column equity, plus
market_value, positions) and the closed-trade ledger from engine.run. Open positions are excluded from trade metrics."""
import numpy as np
import pandas as pd


def cagr(eq,capital):
    yrs=(eq.index[-1]-eq.index[0]).days/365.25
    return (eq.equity.iloc[-1]/capital)**(1/yrs)-1 if yrs>0 else np.nan


def record_months(eq,capital):
    """Official definition: month-end equity >= highest DAILY equity reached up to the previous month-end (and >= initial capital)."""
    e=eq.equity;me=e.resample('ME').last()
    dpeak=e.cummax().resample('ME').last()  # running daily maximum as of each month-end
    prev=dpeak.shift(1).fillna(capital).clip(lower=capital)
    flag=me>=prev
    return int(flag.sum()),len(flag),flag


def record_months_monthend(eq,capital):
    """Lenient convention for reference: compare month-end equity only with earlier month-end equities."""
    me=eq.equity.resample('ME').last()
    prev=me.cummax().shift(1).fillna(capital).clip(lower=capital)
    return int((me>=prev).sum())


def longest_without_record(eq):
    """Longest stretch (months) from an equity peak until equity first exceeds that peak again (open stretch counted to the end)."""
    e=eq.equity;peak=e.cummax();under=e<peak
    best=0.;start=None;rec=False
    for d,u in under.items():
        if u and start is None:start=d
        if not u and start is not None:
            v=(d-start).days/30.4375
            if v>best:best=v;rec=False
            start=None
    if start is not None:
        v=(e.index[-1]-start).days/30.4375
        if v>best:best=v;rec=True  # flagged open only when the open stretch is itself the longest
    return best,rec


def monthly_returns(eq,capital):
    me=eq.equity.resample('ME').last();prev=me.shift(1);prev.iloc[0]=capital
    return me/prev-1


def compute(eq,tr,capital,open_pos=None,bench=None):
    m=dict()
    yrs=(eq.index[-1]-eq.index[0]).days/365.25
    m['start']=str(eq.index[0].date());m['end']=str(eq.index[-1].date());m['years']=yrs
    m['equity_start']=capital;m['equity_end']=float(eq.equity.iloc[-1]);m['cagr']=cagr(eq,capital)
    n=len(tr);m['trades']=n
    if n:
        r=tr.net_return;pnl=tr.pnl;w=pnl>0;l=pnl<0
        m['win_ratio']=w.mean()
        m['avg_profit_pct']=r[w].mean() if w.any() else np.nan;m['avg_profit_rp']=pnl[w].mean() if w.any() else np.nan
        m['avg_loss_pct']=r[l].mean() if l.any() else np.nan;m['avg_loss_rp']=pnl[l].mean() if l.any() else np.nan
        m['profit_factor']=pnl[w].sum()/-pnl[l].sum() if l.any() else np.inf
        m['expectancy_pct']=m['win_ratio']*m['avg_profit_pct']+(1-m['win_ratio'])*m['avg_loss_pct']
        m['payoff_ratio']=m['avg_profit_pct']/abs(m['avg_loss_pct'])
        m['trades_per_year']=n/yrs;m['avg_hold_days']=tr.days.mean();m['avg_hold_bars']=tr.bars.mean()
        fees=tr.buy_fee.sum()+tr.sell_fee.sum();spread=tr.spread_cost.sum();gross=tr.gross_pnl.sum()
        m['total_fees']=fees;m['total_spread']=spread;m['gross_profit_before_cost']=gross
        m['cost_share_of_gross_profit']=(fees+spread)/gross if gross>0 else np.nan;m['cost_note']='fee+spread of closed trades / gross profit (before costs) of closed trades; open positions excluded'
        m['net_profit_closed']=pnl.sum()
        streak=best=0
        for v in tr.sort_values(['exit_date','entry_date']).pnl:
            streak=streak+1 if v<0 else 0;best=max(best,streak)
        m['longest_losing_streak']=best
        top=pnl.sort_values(ascending=False)
        m['top10_share_of_net_profit']=top.head(10).sum()/pnl.sum() if pnl.sum()>0 else np.nan
        m['small_sample']=n<100
    rec,months,_=record_months(eq,capital);m['record_months']=rec;m['record_months_monthend_only']=record_months_monthend(eq,capital);m['months']=months;m['record_month_pct']=rec/months
    m['mdd']=float(eq.drawdown.min()) if 'drawdown' in eq else float((eq.equity/eq.equity.cummax()-1).min())
    lw,openrun=longest_without_record(eq);m['longest_months_without_record']=lw;m['longest_without_record_open']=openrun
    mr=monthly_returns(eq,capital)
    m['sharpe_rf0']=mr.mean()/mr.std(ddof=1)*np.sqrt(12) if mr.std(ddof=1)>0 else np.nan
    down=np.sqrt((np.minimum(mr,0)**2).mean())
    for rf in (.03,.06):m[f'sharpe_rf{int(rf*100)}']=(mr.mean()-rf/12)/mr.std(ddof=1)*np.sqrt(12) if mr.std(ddof=1)>0 else np.nan
    m['sortino_rf0']=mr.mean()/down*np.sqrt(12) if down>0 else np.nan
    m['calmar']=m['cagr']/abs(m['mdd']) if m['mdd']<0 else np.nan
    m['exposure_days_pct']=float((eq.positions>0).mean());m['avg_capital_used']=float((eq.market_value/eq.equity).mean())
    yr=eq.equity.resample('YE').last();yp=yr.shift(1);yp.iloc[0]=capital;yret=yr/yp-1
    m['losing_years']=int((yret<0).sum());m['years_count']=len(yret)
    if open_pos is not None and len(open_pos):
        m['open_positions']=len(open_pos);m['open_unrealized_pnl']=float(open_pos.unrealized_pnl.sum())
    else:m['open_positions']=0;m['open_unrealized_pnl']=0.
    if bench is not None:
        b=bench.loc[eq.index[0]:eq.index[-1]];by=(b.index[-1]-b.index[0]).days/365.25
        m['bh_cagr']=(b.iloc[-1]/b.iloc[0])**(1/by)-1;m['bh_mdd']=float((b/b.cummax()-1).min())
    return {k:(float(v) if isinstance(v,(np.floating,np.integer)) else v) for k,v in m.items()}


def yearly_returns(eq,capital):
    yr=eq.equity.resample('YE').last();yp=yr.shift(1);yp.iloc[0]=capital
    return yr/yp-1


def without_top_trades(eq,tr,capital,k=5):
    """Approximate equity path if the k best trades (by Rp) had returned 0: final equity scaled by prod(1 - pnl_i / E_i),
    E_i = equity on the exit date of trade i. Also PF / expectancy recomputed without them."""
    top=tr.sort_values('pnl',ascending=False).head(k)
    scale=1.
    for r in top.itertuples():
        e=float(eq.equity.loc[:pd.Timestamp(r.exit_date)].iloc[-1]);scale*=(1-r.pnl/e)
    rest=tr.drop(top.index);pnl=rest.pnl;w=pnl>0;l=pnl<0;wr=w.mean()
    yrs=(eq.index[-1]-eq.index[0]).days/365.25
    return dict(k=k,removed_pnl=float(top.pnl.sum()),cagr=float((eq.equity.iloc[-1]*scale/capital)**(1/yrs)-1),
        profit_factor=float(pnl[w].sum()/-pnl[l].sum()),expectancy_pct=float(wr*rest.net_return[w].mean()+(1-wr)*rest.net_return[l].mean()),
        tickers=top.ticker.tolist())


def bootstrap(tr,eq,capital,n=2000,seed=7):
    """Resample closed trades with replacement; each trade's effect on equity = pnl / equity at its entry date
    (sequential compounding, overlap ignored). Returns 5th/50th/95th percentile CAGR and MDD over the same span."""
    rng=np.random.default_rng(seed)
    eqe=[float(eq.equity.loc[:pd.Timestamp(d)].iloc[-1]) for d in tr.entry_date]
    rets=np.asarray(tr.pnl.to_numpy()/np.asarray(eqe),float)
    yrs=(eq.index[-1]-eq.index[0]).days/365.25;cg=[];dd=[]
    for _ in range(n):
        s=rng.choice(rets,len(rets),replace=True);path=np.cumprod(1+s)
        cg.append(path[-1]**(1/yrs)-1);dd.append((path/np.maximum.accumulate(np.r_[1,path])[1:]-1).min())
    q=lambda a,p:float(np.percentile(a,p))
    return dict(n=n,cagr_p5=q(cg,5),cagr_p50=q(cg,50),cagr_p95=q(cg,95),mdd_p5=q(dd,5),mdd_p50=q(dd,50))


def slice_metrics(eq,tr,start,end=None,open_pos=None):
    """Metrics of a sub-period of ONE continuous run (capital = equity at the slice start; no restart, no capacity reset).
    Trades are those that exit inside the slice."""
    a=pd.Timestamp(start);b=pd.Timestamp(end) if end else eq.index[-1]
    prev=eq.equity[eq.index<a]
    cap=float(prev.iloc[-1]) if len(prev) else float(eq.equity.iloc[0])
    e=eq.loc[a:b].drop(columns=['drawdown'],errors='ignore')
    t=tr[(pd.to_datetime(tr.exit_date)>=a)&(pd.to_datetime(tr.exit_date)<=b)]
    return compute(e,t,cap,None)
