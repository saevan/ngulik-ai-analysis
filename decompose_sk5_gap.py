"""Corrected regime gap decomposition (replaces the exposure x efficiency split in gap_decomposition.csv, which counted entry-day P&L
as efficiency without counting the entering position as exposure; found by an independent audit, 16 Oct 2026).

Daily P&L of each system = entry-day P&L (positions bought today: fill incl. costs -> today's liquidation-marked Close) + held P&L
(everything else: positions held from before, including their exits). Per regime (label known before the day), arithmetic annualized
(mean daily share of prior equity x 252): entry part + held part = total (exact). Also: entry notional per day (share of prior equity),
entry-day return per unit of notional, start-of-day held exposure, held efficiency = held part / exposure.
Systems: SK-5 (fee, s25), Swinger ideal, ideal clamped to the bar, causal stop order, causal next Open (fee). Regimes: er20 and ret60."""
from pathlib import Path
import numpy as np, pandas as pd
import grid_search_timehunter as engine
from backtest_stop_execution import run
from backtest_prototype_swinger import run_portfolio
from backtest_idx_costs import Costs
import search_swinger_like_system as S
from evaluate_swinger_like_finalists import PropCosts
from analyze_sk5_regimes import regimes, SK5
OUT=Path(__file__).resolve().parent/'sk5_regime_results'

def daily_split(curve,trades,closes,sell_fee,slip,qcol,ncol):
    t=trades.copy();t['entry_date']=pd.to_datetime(t.entry_date)
    cl=np.array([closes[k].get(d,np.nan) for k,d in zip(t.ticker,t.entry_date)])
    t['entry_pnl']=t[qcol]*cl*(1-slip)*(1-sell_fee)-t[ncol]
    ent=t.groupby('entry_date').agg(entry_pnl=('entry_pnl','sum'),notional=(ncol,'sum'))
    c=curve.copy();c['prev_eq']=c.equity.shift(1).fillna(1e9);c['dpnl']=c.equity-c.prev_eq
    c=c.join(ent,how='left').fillna({'entry_pnl':0.,'notional':0.})
    c['held_pnl']=c.dpnl-c.entry_pnl;c['w0']=(c.market_value.shift(1)/c.prev_eq).fillna(0.)
    return c

def main():
    st,_=engine.load_data('stocks');fr={str(k):f.reset_index(drop=True) for k,f in st.groupby('Ticker',sort=True)};R=regimes(st)
    closes={k:dict(zip(pd.DatetimeIndex(f['Date/Time']),f.Close.to_numpy(float))) for k,f in fr.items()}
    sysd={}
    for name,cost,slip in [('SK5_fee',Costs(),0.),('SK5_s25',PropCosts(slip=.0025),.0025)]:
        with np.errstate(invalid='ignore',divide='ignore'):c,t=run(fr,cost_model=cost,start='2000-01-01',**S.kwargs(SK5))
        sysd[name]=daily_split(c,t,closes,.0025,slip,'q','notional')
    for mode in ['afl_ideal','ideal_clamped','stop_order','next_open']:
        c,t,_=run_portfolio(fr,mode);sysd['SW_'+mode]=daily_split(c,t,closes,.0025,0.,'quantity','entry_cost')
    rows=[]
    for name,c in sysd.items():
        tot=(c.dpnl/c.prev_eq);assert np.allclose(tot,(c.entry_pnl+c.held_pnl)/c.prev_eq)
        for rdef,reg in R.items():
            lab=reg.regime.reindex(c.index).fillna('unknown')
            for state in ['uptrend','sideways','downtrend']:
                g=c[lab==state]
                ep=(g.entry_pnl/g.prev_eq).mean()*252;hp=(g.held_pnl/g.prev_eq).mean()*252;w0=g.w0.mean()
                rows.append(dict(system=name,regime_def=rdef,regime=state,total=(g.dpnl/g.prev_eq).mean()*252,entry_part=ep,held_part=hp,
                    entry_notional_per_day=(g.notional/g.prev_eq).mean(),entry_day_return_per_notional=g.entry_pnl.sum()/g.notional.sum() if g.notional.sum()>0 else np.nan,
                    held_exposure=w0,held_efficiency=hp/w0 if w0>0 else np.nan,flat_start_days=float((g.w0<1e-9).mean())))
    d=pd.DataFrame(rows);d.to_csv(OUT/'gap_decomposition_entryday.csv',index=False)
    gap=[]
    for rdef in R:
        for state in ['uptrend','sideways','downtrend']:
            x=d[(d.regime_def==rdef)&(d.regime==state)].set_index('system');I=x.loc['SW_afl_ideal']
            for k in ['SK5_fee','SK5_s25','SW_ideal_clamped','SW_stop_order','SW_next_open']:
                K=x.loc[k];gap.append(dict(regime_def=rdef,regime=state,system=k,gap_total=I.total-K.total,gap_entry_day=I.entry_part-K.entry_part,gap_held=I.held_part-K.held_part,
                    ideal_entry_ret=I.entry_day_return_per_notional,sys_entry_ret=K.entry_day_return_per_notional,ideal_notional=I.entry_notional_per_day,sys_notional=K.entry_notional_per_day,
                    ideal_held_exposure=I.held_exposure,sys_held_exposure=K.held_exposure,ideal_held_eff=I.held_efficiency,sys_held_eff=K.held_efficiency))
    G=pd.DataFrame(gap);G.to_csv(OUT/'gap_split_entry_vs_held.csv',index=False);pd.set_option('display.width',260)
    print(G[G.system.isin(['SK5_fee','SK5_s25','SW_ideal_clamped'])].round(3).to_string(index=False));print('done')

if __name__=='__main__':main()
