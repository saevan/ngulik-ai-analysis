"""Joint entry/exit search against a predeclared aspirational outcome profile."""
from pathlib import Path
from itertools import product
import json
import numpy as np
import pandas as pd
import grid_search_timehunter as engine
from backtest_timehunter_atr import atr_previous
from backtest_breakout_er_portfolio import portfolio
from backtest_idx_costs import Costs
from analyze_portfolio_regimes import regime_proxy,attribute

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'choppy_swinger_profile_cost_results'
WINDOWS={'train':('2000-01-01','2015-12-31'),'validation':('2016-01-01','2020-12-31'),'test':('2021-01-01','2025-08-15'),'full':('2000-01-01','2025-08-15')}
CONFIGS=[dict(entry=e,exit=x,stop=s,age=h) for e,x,s,h in product(['range_rebound','pullback'],['sma20','hhv5'],[1,2],[None,20])]

def builders(cfg,allowed):
    def entry(f):
        c=f.Close;a=atr_previous(f)
        if cfg['entry']=='inverse':setup=(c<c.rolling(30).mean())|((f.Open-f.Low)>=2*a)
        elif cfg['entry']=='range_rebound':
            low=f.Low.shift(1).rolling(20).min();high=f.High.shift(1).rolling(20).max()
            setup=(f.Low<=low+.3*(high-low))&(c>c.shift(1))&(c>f.Open)
        else:setup=(c>c.rolling(20).mean())&(f.Low<=c.rolling(5).mean())&(c>c.shift(1))&(c>f.Open)
        tick=np.select([c<200,c<500,c<2000,c<5000],[1.,2.,5.,10.],default=25.)
        cost=np.ceil(c/tick+1)*tick*1.0015-np.maximum(tick,np.floor(c/tick-1)*tick)*.9975
        width=f.High.rolling(20).max()-f.Low.rolling(20).min()
        setup=setup&(width>=8*cost)
        return (setup&(a>0)).fillna(False).shift(1,fill_value=False).to_numpy(bool)&f['Date/Time'].isin(allowed).to_numpy()&f.tradable.to_numpy(bool)
    def exit_signal(f):
        signal=f.Close>=f.Close.rolling(20).mean() if cfg['exit']=='sma20' else f.Close>f.High.shift(1).rolling(5).max()
        return signal.fillna(False).to_numpy(bool)
    return entry,exit_signal

def main():
    OUT.mkdir(exist_ok=True)
    plan=dict(configs=CONFIGS,target='Swinger market-choppy ideal WR51.53%, avg loss3.14%, avg win14.69%, hold19.20bars; full2575trades',
        train_gates='WR45-60%, avg loss<=5%, avg win>=10%, holding10-30bars, N>=900, CAGR>0, sideways annual>0, moneyPF>1.1',
        selection='If pass rank distance to target. If none pass, nearest profile diagnostic only with >=100 trades. Freeze before subsequent windows.',
        scope='Adaptive cost8 follow-up, two recovery entry families only; signal Close cost estimate, no future fill quote. Only secondary; all nextOpen, fees.15/.25; stop entry ATR Close/nextOpen, age nextOpen; marketER<.3 entry. No forced exit on regime change.',
        windows=WINDOWS,validation='Previously examined history, not independent holdout. No adoption if failures.')
    (OUT/'PLAN.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
    data,_=engine.load_data('stocks');proxy=regime_proxy(data);allowed=set(proxy.index[proxy.regime=='sideways'])
    frames={w:{str(k):f.reset_index(drop=True) for k,f in data[data['Date/Time']<=end].groupby('Ticker',sort=True)} for w,(_,end) in WINDOWS.items()}
    rows=[]
    def run(cfg,window,scenario,reverse=False):
        entry,exit_signal=builders(cfg,allowed)
        for f in frames[window].values():
            i=len(f)//2
            np.testing.assert_array_equal(entry(f.iloc[:i]),entry(f)[:i]);np.testing.assert_array_equal(exit_signal(f.iloc[:i]),exit_signal(f)[:i])
        cost=Costs() if scenario=='fees' else Costs(grid=True,ticks_per_side=1,round_lot=100)
        with np.errstate(invalid='ignore'):
            c,t,_=portfolio(frames[window],hold=None,fade=float('inf'),entry_builder=entry,exit_builder=exit_signal,
                entry_stop_atr=cfg['stop'],max_age_signal=cfg['age'],cost_model=cost,start=WINDOWS[window][0],reverse=reverse)
        assert t.entry_date.isin(allowed).all()
        r=t.net_return;w=r[r>0];l=r[r<0];stats,d=attribute(c,proxy,'stocks',scenario);side=stats[stats.regime=='sideways'].iloc[0]
        month=c.new_high.groupby(c.index.to_period('M')).any()
        row=dict(**cfg,window=window,scenario=scenario,reverse=reverse,n=len(t),wr=(r>0).mean(),avg_win=w.mean(),avg_loss=-l.mean(),
            mean_return=r.mean(),pf=t.loc[t.pnl>0,'pnl'].sum()/-t.loc[t.pnl<0,'pnl'].sum(),mean_bars=t.bars.mean(),
            cagr=(c.equity.iloc[-1]/1e9)**(365.25/(c.index[-1]-c.index[0]).days)-1,mdd=c.drawdown.min(),records=int(month.sum()),months=len(month),
            sideways_annual=side.conditional_annualized,sideways_records=side.months_record,sideways_months=side.months_present,
            cash=(d.loc[d.regime=='sideways','cash']/d.loc[d.regime=='sideways','equity']).mean())
        row['distance']=abs(row['wr']-.51534)/.1+abs(row['avg_loss']-.03142)/.03+abs(row['avg_win']-.14694)/.1+abs(row['mean_bars']-19.2)/19.2
        rows.append(row);pd.DataFrame(rows).to_csv(OUT/'comparison.csv',index=False)
        label=f'{window}_{scenario}_{cfg["entry"]}_{cfg["exit"]}_s{cfg["stop"]}_h{cfg["age"]}_r{reverse}'
        c.to_csv(OUT/f'{label}_equity.csv');t.to_csv(OUT/f'{label}_trades.csv',index=False)
        print(label,f'N{len(t)} WR{row["wr"]:.2%} loss{row["avg_loss"]:.2%} hold{row["mean_bars"]:.1f} CAGR{row["cagr"]:.2%} side{row["sideways_annual"]:.2%}',flush=True)
        return row
    for cfg in CONFIGS:run(cfg,'train','spread')
    passed=[r for r in rows if .45<=r['wr']<=.60 and r['avg_loss']<=.05 and r['avg_win']>=.1 and 10<=r['mean_bars']<=30 and r['n']>=900 and r['cagr']>0 and r['sideways_annual']>0 and r['pf']>1.1]
    chosen=min(passed or [r for r in rows if r['n']>=100],key=lambda r:r['distance'])
    cfg={k:chosen[k] for k in ['entry','exit','stop','age']}
    (OUT/'FROZEN.json').write_text(json.dumps(dict(config=cfg,training_pass=bool(passed),passed_count=len(passed)),indent=2),encoding='utf-8')
    for window in ['validation','test','full']:
        for scenario in ['fees','spread']:run(cfg,window,scenario)
    run(cfg,'test','spread',True)
    (OUT/'REPORT.md').write_text('# Profile search\n\n23 simulations with range20 >=8times estimated roundtrip fee+spread cost at signal Close. Adaptive follow-up after unfiltered search; no independent holdout. See PLAN/FROZEN for prior selection rules. No candidate automatically adopted. Sideways annual equivalent is disjoint-day attribution, not a standalone CAGR. All data previously examined; not independent validation. Spread modern IDX grid counterfactual, not observed bidask. Primary/AFL unchanged. Prefix and eligibility/accounting checks passed.\n\n'+pd.DataFrame(rows).to_string(index=False),encoding='utf-8')

if __name__=='__main__':main()
