"""Where Breakout+ER loses to Prototype Swinger, and causal stop-order mitigations."""
from pathlib import Path
from itertools import product
import json
import numpy as np
import pandas as pd
import grid_search_timehunter as engine
from backtest_stop_execution import run, prepare
from backtest_idx_costs import Costs
from analyze_portfolio_regimes import regime_proxy

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'swinger_gap_results'
WINDOWS={'train':('2000-01-01','2015-12-31'),'validation':('2016-01-01','2020-12-31'),'test':('2021-01-01','2025-08-15'),'full':('2000-01-01','2025-08-15')}
SCEN={'fees':Costs(),'spread':Costs(grid=True,ticks_per_side=1,round_lot=100)}
CONFIGS=[dict(gate=g,entry=e,exit=x,llv=n) for g,e,x,n in product(['none','er'],['next_open','buy_stop'],['close','fade_intraday'],[0,5,10,20])]
BASE=dict(gate='none',entry='next_open',exit='close',llv=0)

def label(c):return f'g{c["gate"]}_{c["entry"]}_{c["exit"]}_llv{c["llv"]}'

def stats(c,t):
    m=c.new_high.groupby(c.index.to_period('M')).any();r=t.net_return;w=r[r>0];l=-r[r<0]
    return dict(cagr=(c.equity.iloc[-1]/1e9)**(365.25/(c.index[-1]-c.index[0]).days)-1,records=int(m.sum()),months=len(m),mdd=c.drawdown.min(),
        n=len(t),wr=(r>0).mean(),avg_win=w.mean(),avg_loss=l.mean(),payout=w.mean()/l.mean(),big_loss=(r<-.1).mean(),mean_bars=t.bars.mean(),
        outside_fills=int(t.exit_outside_bar.sum()+t.entry_outside_bar.sum()))

def main():
    OUT.mkdir(exist_ok=True)
    plan=dict(configs=CONFIGS,base=BASE,windows=WINDOWS,
        selection='Train 2000-2015, spread scenario. Eligible: CAGR > base AND record months >= base. Pick max CAGR (tie: records). Frozen before validation/test/full.',
        fixed='Rp1bn, 10 shared slots, 10% prior-close equity, compounding, long only, fade2 ATR from current Open, SMA30 close exit, fee .15/.25, spread stress 1 tick/side + lot100.',
        caution='Data previously examined; 32 configs, multiple-testing risk. Swinger ideal fill is aspirational; mitigations use only causal stop levels.')
    (OUT/'PLAN.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
    data,_=engine.load_data('stocks');proxy=regime_proxy(data)
    gate=set(proxy.index[proxy.regime.isin(['uptrend','downtrend'])])
    frames={w:{str(k):f.reset_index(drop=True) for k,f in data[data['Date/Time']<=end].groupby('Ticker',sort=True)} for w,(_,end) in WINDOWS.items()}
    # Prefix causality of every precomputed signal/level.
    for c in CONFIGS[:16:3]+CONFIGS[16::5]:
        for f in list(frames['full'].values())[::7]:
            g=None if c['gate']=='none' else gate;cut=len(f)//2
            a=prepare(f,2.,c['llv'],c['entry'],g);b=prepare(f.iloc[:cut],2.,c['llv'],c['entry'],g)
            for k,v in b.items():
                if v is not None and k!='Date/Time':np.testing.assert_array_equal(np.asarray(a[k])[:cut],np.asarray(v))
    rows=[]
    def go(c,w,s):
        with np.errstate(invalid='ignore'):
            cur,t=run(frames[w],fade=2.,exit_mode=c['exit'],llv=c['llv'] or None,entry_mode=c['entry'],cost_model=SCEN[s],start=WINDOWS[w][0],gate_dates=None if c['gate']=='none' else gate)
        row=dict(**c,window=w,scenario=s,**stats(cur,t));rows.append(row)
        name=f'{w}_{s}_{label(c)}';cur.to_csv(OUT/f'{name}_equity.csv');t.to_csv(OUT/f'{name}_trades.csv',index=False)
        print(name,f"CAGR{row['cagr']:.2%} rec{row['records']} WR{row['wr']:.2%} loss{row['avg_loss']:.2%}",flush=True);return row
    train=pd.DataFrame([go(c,'train','spread') for c in CONFIGS])
    base=train[np.logical_and.reduce([train[k]==v for k,v in BASE.items()])].iloc[0]
    ok=train[(train.cagr>base.cagr)&(train.records>=base.records)].sort_values(['cagr','records'],ascending=False)
    chosen=None if ok.empty else dict(gate=ok.iloc[0].gate,entry=ok.iloc[0].entry,exit=ok.iloc[0]['exit'],llv=int(ok.iloc[0].llv))
    (OUT/'FROZEN.json').write_text(json.dumps(dict(chosen=chosen,base_train=dict(cagr=base.cagr,records=int(base.records))),indent=2),encoding='utf-8')
    print('FROZEN',chosen,flush=True)
    for c in [x for x in [chosen,BASE] if x is not None]:
        for w in ['validation','test','full']:
            for s in SCEN:go(c,w,s)
    pd.DataFrame(rows).to_csv(OUT/'comparison.csv',index=False)
    old=pd.read_csv(ROOT/'fading_sma30_results'/'breakout_ER_fees_fade2_equity.csv')
    np.testing.assert_allclose(pd.read_csv(OUT/f'full_fees_{label(BASE)}_equity.csv').equity,old.equity,rtol=1e-10);print('regression OK')

if __name__=='__main__':main()
