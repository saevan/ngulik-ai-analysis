"""SK-5 vs Swinger by market regime: where is the gap, and which characteristics explain it.

Regimes (label known before the day: computed at the previous Close), on the equal-weight 100-stock proxy (not IHSG):
  A 'er20' (same as earlier research, analyze_portfolio_regimes.regime_proxy): ER20 >= 0.3 and 20-day change > 0 -> uptrend,
    ER20 >= 0.3 and change < 0 -> downtrend, otherwise sideways.
  B 'ret60' (robustness, slower): proxy 60-day return > +5% -> uptrend, < -5% -> downtrend, otherwise sideways.
Systems (full 2000-2025, fee 0.15/0.25%, no liquidity cap, Rp1bn): SK-5 (v2 pre-Open book; also with 0.25%/side slippage), base
(strict HHV20 buy stop, v2 book), Swinger ideal / ideal clamped to the bar range / filled at the confirming Close / causal stop order /
causal next Open.
Outputs: daily attribution by regime (conditional annualized return, contribution, record days/months, exposure, regime-only drawdown),
exposure x efficiency decomposition of the daily return, trade characteristics by entry regime, by period, and Swinger fill advantage."""
from pathlib import Path
import numpy as np, pandas as pd
import grid_search_timehunter as engine
from analyze_portfolio_regimes import regime_proxy, attribute
from backtest_stop_execution import run
from backtest_prototype_swinger import run_portfolio
from backtest_idx_costs import Costs
import search_swinger_like_system as S
from evaluate_swinger_like_finalists import PropCosts

ROOT=Path(__file__).resolve().parent;OUT=ROOT/'sk5_regime_results'
SK5=dict(channel=5,er_min=.3,exit='cand',failed=0.,size_div=5)
PERIODS={'2000-15':('2000-01-01','2015-12-31'),'2016-20':('2016-01-01','2020-12-31'),'2021-25':('2021-01-01','2025-08-15')}

def regimes(st):
    p=regime_proxy(st)
    b=p.copy();r60=p.proxy/p.proxy.shift(60)-1
    lab=pd.Series('sideways',index=p.index);lab[r60>.05]='uptrend';lab[r60<-.05]='downtrend';lab[r60.isna()]='unknown'
    b['regime']=lab.shift(1).fillna('unknown')
    return {'er20':p,'ret60':b}

def systems(fr):
    out={}
    for name,cost in [('SK5_fee',Costs()),('SK5_s25',PropCosts(slip=.0025))]:
        with np.errstate(invalid='ignore',divide='ignore'):out[name]=run(fr,cost_model=cost,start='2000-01-01',**S.kwargs(SK5))
    with np.errstate(invalid='ignore',divide='ignore'):out['BASE_fee']=run(fr,cost_model=Costs(),start='2000-01-01',**S.kwargs(S.BASE))
    for mode in ['afl_ideal','ideal_clamped','close_fill','stop_order','next_open']:
        c,t,_=run_portfolio(fr,mode);out['SW_'+mode]=(c,t)
    return out

def chain_mdd(r):
    e=(1+r).cumprod();return float((e/e.cummax()-1).min()) if len(e) else np.nan

def daily_tables(curve,reg,name,rdef):
    res,table=attribute(curve,reg,'stocks',name)
    table['w']=(table.market_value/table.equity).shift(1).fillna(0.)  # exposure at the start of the day
    rows=[]
    for state,g in table.groupby('regime'):
        mdd=chain_mdd(g.equity_return)
        rows.append(dict(regime=state,mean_daily=g.equity_return.mean(),mean_w=g.w.mean(),eff=g.equity_return.sum()/g.w.sum() if g.w.sum()>0 else np.nan,
            regime_chain_mdd=mdd,days=len(g)))
    dec=pd.DataFrame(rows)
    res=res.merge(dec,on='regime');res['system']=name;res['regime_def']=rdef
    # per period
    per=[]
    for pn,(a,b) in PERIODS.items():
        g0=table.loc[a:b]
        for state,g in g0.groupby('regime'):
            dur=g.elapsed_days.sum()
            per.append(dict(system=name,regime_def=rdef,period=pn,regime=state,time_fraction=dur/g0.elapsed_days.sum(),
                conditional_annualized=float(np.expm1(g.log_return.sum()*365.25/dur)) if dur>0 else np.nan,mean_w=g.w.mean()))
    return res,pd.DataFrame(per),table

def trade_tables(trades,reg,name,rdef,curve):
    t=trades.copy();t['entry_date']=pd.to_datetime(t.entry_date)
    t['regime']=reg.regime.reindex(t.entry_date).fillna('unknown').to_numpy()
    eq=curve.equity
    t['eq_entry']=[float(eq.loc[:d].iloc[-1]) if (eq.index<=d).any() else 1e9 for d in t.entry_date]
    t['money_ret']=t.pnl/t.eq_entry  # effect of the trade on portfolio equity
    yrs=(curve.index[-1]-curve.index[0]).days/365.25;rows=[]
    for state,g in t.groupby('regime'):
        r=g.net_return;w=r>0
        rows.append(dict(system=name,regime_def=rdef,regime=state,n=len(g),trades_per_year=len(g)/yrs,wr=w.mean(),avg_win=r[w].mean(),avg_loss=-r[~w].mean(),
            payout=r[w].mean()/-r[~w].mean() if (~w).any() else np.nan,expectancy=r.mean(),median=r.median(),loss_gt10=(r<-.10).mean(),
            hold=g.bars.mean(),hold_win=g.bars[w].mean(),hold_loss=g.bars[~w].mean(),sum_money_ret=g.money_ret.sum(),mean_money_ret=g.money_ret.mean()))
    return pd.DataFrame(rows),t

def main():
    OUT.mkdir(exist_ok=True)
    st,_=engine.load_data('stocks');fr={str(k):f.reset_index(drop=True) for k,f in st.groupby('Ticker',sort=True)}
    R=regimes(st);sy=systems(fr)
    D=[];P=[];T=[];tt={}
    for rdef,reg in R.items():
        for name,(c,t) in sy.items():
            d,p,_=daily_tables(c,reg,name,rdef);D.append(d);P.append(p)
            tr,tl=trade_tables(t,reg,name,rdef,c);T.append(tr);tt[(rdef,name)]=tl
    D=pd.concat(D);P=pd.concat(P);T=pd.concat(T)
    D.to_csv(OUT/'daily_by_regime.csv',index=False);P.to_csv(OUT/'daily_by_regime_period.csv',index=False);T.to_csv(OUT/'trades_by_regime.csv',index=False)
    # Swinger ideal fill advantage by entry regime (row-aligned with afl_ideal_net_trades.csv, verified on prices)
    dec=pd.read_csv(ROOT/'swinger_gap_results/swinger_fill_decomposition.csv');it=pd.read_csv(ROOT/'prototype_swinger_benchmark_results/afl_ideal_net_trades.csv',parse_dates=['entry_date'])
    assert np.allclose(dec.entry_ideal.to_numpy(),it.entry_price.to_numpy()) and np.allclose(dec.exit_ideal.to_numpy(),it.exit_price.to_numpy())
    rows=[]
    for rdef,reg in R.items():
        dec['regime']=reg.regime.reindex(it.entry_date).fillna('unknown').to_numpy()
        for state,g in dec.groupby('regime'):
            rows.append(dict(regime_def=rdef,regime=state,n=len(g),ideal_gross=g.ideal.mean(),next_open_gross=g.realistic.mean(),
                entry_gain_vs_next_open=g.entry_gain_vs_open.mean(),exit_gain_vs_next_open=g.exit_gain_vs_open.mean(),
                entry_below_low=g.entry_below_low.mean(),exit_above_high=g.exit_above_high.mean()))
    pd.DataFrame(rows).to_csv(OUT/'swinger_fill_by_regime.csv',index=False)
    # regime time shares
    pd.concat([reg.regime.loc['2000-01-01':].value_counts(normalize=True).rename(rdef) for rdef,reg in R.items()],axis=1).to_csv(OUT/'regime_shares.csv')
    for (rdef,name),tl in tt.items():
        if name in('SK5_fee','SW_afl_ideal'):tl.to_csv(OUT/f'trades_{rdef}_{name}.csv',index=False)
    for name,(c,t) in sy.items():c.to_csv(OUT/f'equity_{name}.csv')
    print('done')

if __name__=='__main__':main()
