"""Pre-registered search for portfolio CAGR and record-equity months (Breakout+ER family)."""
from pathlib import Path
from itertools import product
from multiprocessing import Pool
import argparse
import json
import numpy as np
import pandas as pd
import grid_search_timehunter as engine
from backtest_breakout_er import entry_signal, efficiency_ratio
from backtest_breakout_er_portfolio import portfolio
from backtest_choppy_inverted_signals import inverted_builders
from backtest_idx_costs import Costs
from analyze_portfolio_regimes import regime_proxy

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'cagr_records_results'
WINDOWS={'train':('2000-01-01','2015-12-31'),'validation':('2016-01-01','2020-12-31'),'test':('2021-01-01','2025-08-15'),'full':('2000-01-01','2025-08-15')}
# Inverse keeps the exact raw-signal relation only with fade2 (hardcoded in inverted_builders).
CONFIGS=[dict(gate=g,rank=r,fade=f,inverse=False) for g,r,f in product(['none','er','up'],['alpha','er'],[2,5])]
CONFIGS+=[dict(gate='er',rank=r,fade=2,inverse=True) for r in ['alpha','er']]
BASELINE=dict(gate='er',rank='alpha',fade=2,inverse=True)   # current research combined system
ORIGINAL=dict(gate='none',rank='alpha',fade=2,inverse=False) # Breakout+ER fade2/SMA30 without market gate
SCENARIOS={'fees':Costs(),'spread':Costs(grid=True,ticks_per_side=1,round_lot=100)}
STATE={}

def label(cfg):return f'g{cfg["gate"]}_r{cfg["rank"]}_f{cfg["fade"]}_i{int(cfg["inverse"])}'

def builders(cfg,proxy):
    trend=set(proxy.index[proxy.regime.isin(['uptrend','downtrend'])]);choppy=set(proxy.index[proxy.regime=='sideways'])
    up=set(proxy.index[proxy.regime=='uptrend'])
    allowed={'er':trend,'up':up}.get(cfg['gate'])
    entry=None if allowed is None else (lambda f:entry_signal(f,.3)&f['Date/Time'].isin(allowed).to_numpy()&f.tradable.to_numpy(bool))
    # Signal-bar stock ER20, known before the next Open where the entry fills.
    priority=None if cfg['rank']=='alpha' else (lambda f:efficiency_ratio(f.Close,20).shift(1).to_numpy(float))
    sec=None
    if cfg['inverse']:
        ie,ix=inverted_builders(('market',0),choppy)
        sec=dict(style='inverse',slots=10,reserved=False,primary_first=True,allowed_dates=choppy,entry_builder=ie,exit_builder=ix)
    return entry,priority,sec

def metrics(c,t):
    month=c.new_high.groupby(c.index.to_period('M')).any()
    r=t.net_return;win=r[r>0];loss=-r[r<0]
    return dict(cagr=(c.equity.iloc[-1]/1e9)**(365.25/(c.index[-1]-c.index[0]).days)-1,records=int(month.sum()),months=len(month),
        mdd=c.drawdown.min(),n=len(t),wr=(r>0).mean(),avg_win=win.mean(),avg_loss=loss.mean(),payout=win.mean()/loss.mean(),
        mean_bars=t.bars.mean(),invested=(c.market_value/c.equity).mean(),final_equity=c.equity.iloc[-1])

def job(args):
    cfg,window,scenario=args
    entry,priority,sec=builders(cfg,STATE['proxy'])
    frames=STATE['frames'][window]
    for f in list(frames.values())[::10]:
        cut=len(f)//2
        for b in [x for x in [entry,priority] if x is not None]:np.testing.assert_array_equal(b(f.iloc[:cut]),b(f)[:cut])
    with np.errstate(invalid='ignore'):
        c,t,counts=portfolio(frames,threshold=.3,hold=None,fade=cfg['fade'],exit_sma=30,entry_builder=entry,secondary=sec,
            cost_model=SCENARIOS[scenario],start=WINDOWS[window][0],priority_builder=priority)
    name=f'{window}_{scenario}_{label(cfg)}'
    c.to_csv(OUT/f'{name}_equity.csv');t.to_csv(OUT/f'{name}_trades.csv',index=False)
    mods={f'{m}_n':int((t.module==m).sum()) for m in ['trend','range']}
    return dict(**cfg,window=window,scenario=scenario,**metrics(c,t),**mods,**counts)

def regression(rows):
    """Exact reproduction of earlier published curves (full window)."""
    checks=[(ORIGINAL,'fees','fading_sma30_results/breakout_ER_fees_fade2_equity.csv'),(ORIGINAL,'spread','fading_sma30_results/breakout_ER_spread_fade2_equity.csv'),
        (BASELINE,'fees','primary_inverse_switch_results/fees_combined_equity.csv'),(BASELINE,'spread','primary_inverse_switch_results/spread_combined_equity.csv')]
    for cfg,scenario,path in checks:
        new=pd.read_csv(OUT/f'full_{scenario}_{label(cfg)}_equity.csv');old=pd.read_csv(ROOT/path)
        np.testing.assert_allclose(new.equity,old.equity,rtol=1e-10)

def main():
    p=argparse.ArgumentParser();p.add_argument('--workers',type=int,default=4);args=p.parse_args()
    OUT.mkdir(exist_ok=True)
    plan=dict(objective='Portfolio CAGR and number of months with a new all-time daily equity high (record months).',
        configs=CONFIGS,baseline=BASELINE,original=ORIGINAL,windows=WINDOWS,
        levers='gate: none / market ER20>=.3 (up+down) / market uptrend only (lagged proxy regime). rank: alphabetical / higher signal-bar stock ER20 first when slots or cash bind. fade: 2 or 5 ATR from CURRENT bar Open. inverse: choppy raw-signal inverse module on/off (fade2 only).',
        fixed='Entry Close>HHV20 prior bars and stock ER20>=.3; exit Close<SMA30 or fade; signal at Close, fill next tradable Open; no hold cap; Rp1bn, 10 shared slots, 10% prior-close equity per entry capped by cash, compounding, long only. Fee buy .15% sell .25%; spread stress modern tick grid 1 tick each side + 100-share lot.',
        selection='Train window 2000-2015, spread scenario only. Eligible: CAGR > baseline CAGR AND records >= baseline records. Choose max CAGR among eligible; tie -> more records. Frozen before validation/test/full. No retuning afterwards.',
        caution='All windows were examined in earlier research; validation/test are chronological, not independent holdouts. 14 configs = multiple-testing risk.')
    (OUT/'PLAN.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
    data,_=engine.load_data('stocks');STATE['proxy']=regime_proxy(data)
    STATE['frames']={w:{str(k):f.reset_index(drop=True) for k,f in data[data['Date/Time']<=end].groupby('Ticker',sort=True)} for w,(_,end) in WINDOWS.items()}
    rows=[]
    with Pool(args.workers) as pool:
        for row in pool.imap_unordered(job,[(cfg,'train','spread') for cfg in CONFIGS]):
            rows.append(row);print('train',label(row),f"CAGR{row['cagr']:.2%} rec{row['records']}",flush=True)
        train=pd.DataFrame(rows);base=train[np.logical_and.reduce([train[k]==v for k,v in BASELINE.items()])].iloc[0]
        train['eligible']=(train.cagr>base.cagr)&(train.records>=base.records)
        pick=train[train.eligible].sort_values(['cagr','records'],ascending=False)
        chosen=None if pick.empty else {k:(bool(pick.iloc[0][k]) if k=='inverse' else pick.iloc[0][k]) for k in ['gate','rank','fade','inverse']}
        if chosen is not None:chosen['fade']=int(chosen['fade'])
        (OUT/'FROZEN.json').write_text(json.dumps(dict(chosen=chosen,baseline_train=dict(cagr=base.cagr,records=int(base.records))),indent=2,default=str),encoding='utf-8')
        print('FROZEN',chosen,flush=True)
        evals=[c for c in [chosen,BASELINE,ORIGINAL] if c is not None]
        evals=[c for i,c in enumerate(evals) if c not in evals[:i]]
        tasks=[(c,w,s) for c in evals for w in ['validation','test','full'] for s in SCENARIOS]
        for row in pool.imap_unordered(job,tasks):
            rows.append(row);print(row['window'],row['scenario'],label(row),f"CAGR{row['cagr']:.2%} rec{row['records']}",flush=True)
    result=pd.DataFrame(rows);result.to_csv(OUT/'comparison.csv',index=False)
    regression(rows);print('regression OK',flush=True)

if __name__=='__main__':main()
