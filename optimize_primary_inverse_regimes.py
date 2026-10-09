"""Preserve exact primary/inverse relationship; tune and validate shared regimes."""
from pathlib import Path
from itertools import product
import argparse
import json
import numpy as np
import pandas as pd
import grid_search_timehunter as engine
from backtest_timehunter_atr import atr_previous
from backtest_breakout_er import efficiency_ratio
from backtest_breakout_er_portfolio import portfolio
from backtest_idx_costs import Costs
from analyze_portfolio_regimes import regime_proxy,attribute

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'optimized_inverse_regime_results'
CONFIGS=[dict(hhv=n,sma=m,rotate=r) for n,m,r in product([10,20],[20,30],[False,True])]
BASE=dict(hhv=20,sma=30,rotate=False)
WINDOWS={'train':('2000-01-01','2015-12-31'),'validation':('2016-01-01','2020-12-31'),'test':('2021-01-01','2025-08-15'),'full':('2000-01-01','2025-08-15')}

def builders(cfg,proxy):
    previous=proxy.er.shift(1)
    trend=set(proxy.index[previous>=.3]);choppy=set(proxy.index[previous<.3])
    assert not trend.intersection(choppy)
    def signals(f):
        a=atr_previous(f);c=f.Close
        b=(c>f.High.shift(1).rolling(cfg['hhv']).max())&(efficiency_ratio(c,20)>=.3)
        s=(c<c.rolling(cfg['sma']).mean())|(np.isfinite(a)&(a>0)&((f.Open-f.Low)>=2*a))
        buy=b.shift(1,fill_value=False).to_numpy(bool)&f['Date/Time'].isin(trend).to_numpy()&f.tradable.to_numpy(bool)
        inv_buy=(s&(a>0)).shift(1,fill_value=False).to_numpy(bool)&f['Date/Time'].isin(choppy).to_numpy()&f.tradable.to_numpy(bool)
        er=f['Date/Time'].map(proxy.er)
        sell=s|((er<.3) if cfg['rotate'] else False)
        inv_sell=b|((er>=.3) if cfg['rotate'] else False)
        return buy,inv_buy,sell.fillna(False).to_numpy(bool),inv_sell.fillna(False).to_numpy(bool)
    return signals,trend,choppy

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--resume',action='store_true');args=parser.parse_args()
    OUT.mkdir(exist_ok=True)
    plan=dict(configs=CONFIGS,baseline=BASE,windows=WINDOWS,
        invariant='StockER20>=.3 original buy; fade2 ATRprevious original sell; complementary marketER20 .3 entry gates. Inverse swaps original buy/sell. Optional rotation adds own-regime-end exit to BOTH modules, nextOpen.',
        selection='Train spread only. Require primary-alone CAGR>0 and trend annual>0, inverse-alone CAGR>0 and choppy annual>0, combined CAGR>0 and both regime annual>0. Rank passing by combined CAGR. If none, maximize minimum of standalone own-regime returns, then combined CAGR; diagnostic only.',
        caution='Already examined historical data, not independent holdout. All cash/slots shared in combined. No retuning after freezing; primary/AFL defaults unchanged.')
    (OUT/'PLAN.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
    data,_=engine.load_data('stocks');proxy=regime_proxy(data)
    frames={w:{str(k):f.reset_index(drop=True) for k,f in data[data['Date/Time']<=end].groupby('Ticker',sort=True)} for w,(_,end) in WINDOWS.items()}
    rows=pd.read_csv(OUT/'comparison.csv').to_dict('records') if args.resume and (OUT/'comparison.csv').exists() else []
    def run(cfg,mode,window,scenario):
        if args.resume:
            cached=[r for r in rows if all(r[k]==v for k,v in cfg.items()) and r['mode']==mode and r['window']==window and r['scenario']==scenario]
            if cached:return cached[0]
        signals,trend,choppy=builders(cfg,proxy)
        pe=lambda f:signals(f)[0];ie=lambda f:signals(f)[1];px=lambda f:signals(f)[2];ix=lambda f:signals(f)[3]
        for f in frames[window].values():
            a=signals(f);cut=len(f)//2;b=signals(f.iloc[:cut])
            assert not(a[0]&a[1]).any()
            for x,y in zip(a,b):np.testing.assert_array_equal(x[:cut],y)
        sec=None if mode=='primary' else dict(style='inverse',slots=10,reserved=False,primary_first=True,allowed_dates=choppy,entry_builder=ie,exit_builder=ix)
        cost=Costs() if scenario=='fees' else Costs(grid=True,ticks_per_side=1,round_lot=100)
        with np.errstate(invalid='ignore'):
            c,t,_=portfolio(frames[window],hold=None,fade=float('inf'),entry_builder=pe if mode!='inverse' else lambda f:np.zeros(len(f),bool),
                exit_builder=px,secondary=sec,cost_model=cost,start=WINDOWS[window][0])
        assert t.loc[t.module=='trend','entry_date'].isin(trend).all()
        assert t.loc[t.module=='range','entry_date'].isin(choppy).all()
        if cfg==BASE and window=='full':
            oldname={'primary':'primary_trend_only','inverse':'inverse_choppy_only','combined':'combined'}[mode]
            old=pd.read_csv(ROOT/'primary_inverse_switch_results'/f'{scenario}_{oldname}_equity.csv');np.testing.assert_allclose(c.equity,old.equity,rtol=1e-10)
        _,daily=attribute(c,proxy,'stocks',mode)
        def annual(regimes):
            g=daily[daily.regime.isin(regimes)]
            return np.expm1(g.log_return.sum()*365.25/g.elapsed_days.sum())
        month=c.new_high.groupby(c.index.to_period('M')).any()
        row=dict(**cfg,mode=mode,window=window,scenario=scenario,n=len(t),wr=(t.net_return>0).mean(),
            avg_win=t.loc[t.net_return>0,'net_return'].mean(),avg_loss=-t.loc[t.net_return<0,'net_return'].mean(),mean_bars=t.bars.mean(),
            cagr=(c.equity.iloc[-1]/1e9)**(365.25/(c.index[-1]-c.index[0]).days)-1,mdd=c.drawdown.min(),
            records=int(month.sum()),months=len(month),trend_annual=annual(['uptrend','downtrend']),choppy_annual=annual(['sideways']))
        rows.append(row);pd.DataFrame(rows).to_csv(OUT/'comparison.csv',index=False)
        label=f'{window}_{scenario}_{mode}_n{cfg["hhv"]}_m{cfg["sma"]}_r{cfg["rotate"]}'
        c.to_csv(OUT/f'{label}_equity.csv');t.to_csv(OUT/f'{label}_trades.csv',index=False)
        print(label,f'CAGR{row["cagr"]:.2%} trend{row["trend_annual"]:.2%} choppy{row["choppy_annual"]:.2%} N{len(t)}',flush=True)
        return row
    # Every candidate tested separately and together, so primary cannot mask inverse failure.
    evaluated=[]
    for cfg in CONFIGS:
        p=run(cfg,'primary','train','spread');i=run(cfg,'inverse','train','spread');c=run(cfg,'combined','train','spread')
        passed=bool(p['cagr']>0 and p['trend_annual']>0 and i['cagr']>0 and i['choppy_annual']>0 and c['cagr']>0 and min(c['trend_annual'],c['choppy_annual'])>0)
        evaluated.append(dict(config=cfg,passed=passed,own_regime_min=min(p['trend_annual'],i['choppy_annual']),combined_cagr=c['cagr']))
    passed=[x for x in evaluated if x['passed']]
    chosen=max(passed,key=lambda x:x['combined_cagr']) if passed else max(evaluated,key=lambda x:(x['own_regime_min'],x['combined_cagr']))
    cfg=chosen['config']
    (OUT/'FROZEN.json').write_text(json.dumps(dict(chosen=chosen,evaluated=evaluated),indent=2),encoding='utf-8')
    for window in ['validation','test','full']:
        for scenario in ['fees','spread']:
            run(cfg,'combined',window,scenario)
            if cfg!=BASE:run(BASE,'combined',window,scenario)
            for mode in ['primary','inverse']:run(cfg,mode,window,scenario)
    (OUT/'REPORT.md').write_text('# Optimization of primary/inverse by regime\n\nSee PLAN/FROZEN/comparison for constraints and all results. No optimization after frozen validation. Regime annual figures are disjoint-date attribution, not standalone tradable CAGR; standalone mode CAGR separately reported. Entry conditions based on prior completed bar; exits at next tradable Open. Rotate means each module exits when its own regime ends, without changing original inverse rules. Fee.15/.25%, modern grid/100shares/one tick per side stress, Rp1bn/10 shared slots. Data previously examined, no independent validation. Prefix, eligibility, accounting and full baseline regression checked. AFL unchanged.\n',encoding='utf-8')

if __name__=='__main__':main()
