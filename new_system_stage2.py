"""Stage 2: refine breakout + ATR stop + activated trailing family (stocks 2000-2015 only), then hold-out."""
from itertools import product
from multiprocessing import Pool
import json
import numpy as np
import pandas as pd
import new_system_search as ns

def entry2(x,name):
    c=pd.Series(x['C']);base,flt=name.split('|')
    sig=c>x['hhv55'] if base=='brk55' else c>x['hhv20']
    if 'er' in flt:sig=sig&(x['er']>=.3)
    if 'sma200' in flt:sig=sig&(c>x['sma200'])
    return sig.fillna(False).to_numpy(bool)

ENTRIES=['brk55|none','brk55|er','brk55|sma200','brk55|er+sma200','brk20|er','brk20|er+sma200']
CONFIGS=[dict(entry=e,stop=s,time=0,act=a,trail=m,maxhold=0) for e,s,a,m in product(ENTRIES,[1.5,2.,2.5,3.],[1.,1.5,2.,3.],[1.5,2.,2.5])]

def run_cfg(args):
    cfg,market,start,end=args;tr=[]
    for x in ns.MK[market]:tr+=ns.simulate(x,entry2(x,cfg['entry']),cfg,ns.COST[market],np.datetime64(start),np.datetime64(end))
    return tr

def main():
    for m,df in ns.load().items():ns.MK[m]=[ns.features(f.reset_index(drop=True)) for _,f in df.groupby('Ticker',sort=True)]
    with Pool(4) as p:train=p.map(run_cfg,[(c,'stocks','2000-01-01','2015-12-31') for c in CONFIGS],chunksize=4)
    rows=[dict(**c,**s) for c,t in zip(CONFIGS,train) if (s:=ns.score(t))]
    tr=pd.DataFrame(rows).sort_values(['passes','wr','mean'],ascending=False);tr.to_csv(ns.OUT/'stage2_train_stocks.csv',index=False)
    cols=['entry','stop','act','trail','n','mean','median','wr','payout','win_bars','loss_bars','pf','passes']
    print(tr.passes.value_counts().sort_index().to_string());print(tr[cols].head(12).round(4).to_string())
    top=tr.head(5)[['entry','stop','time','act','trail','maxhold']].to_dict('records')
    (ns.OUT/'STAGE2_FROZEN.json').write_text(json.dumps(dict(selection='stocks 2000-2015: max passes, then WR, then mean',top5=top),indent=2,default=float),encoding='utf-8')
    tests=[('stocks','2016-01-01','2025-12-31'),('forex','2000-01-01','2030-01-01'),('crypto','2000-01-01','2030-01-01')]
    pairs=[(c,t) for c in top for t in tests]
    with Pool(4) as p:res=p.map(run_cfg,[(c,m,a,b) for c,(m,a,b) in pairs])
    ev=pd.DataFrame([dict(**c,market=m,**(ns.score(t) or {})) for (c,(m,a,b)),t in zip(pairs,res)]);ev.to_csv(ns.OUT/'stage2_holdout.csv',index=False)
    print(ev[['entry','stop','act','trail','market','n','mean','median','wr','payout','win_bars','loss_bars','pf','passes']].round(4).to_string())

if __name__=='__main__':main()
