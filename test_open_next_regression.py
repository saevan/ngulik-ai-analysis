"""Open(i+1) portfolio engine with unconstrained slots must reproduce the single-position trade simulation exactly."""
import numpy as np
import pandas as pd
import grid_search_timehunter as engine
import new_system_search as ns
import new_system_stage2 as s2
from backtest_open_next import run
from backtest_idx_costs import Costs

def main():
    st,_=engine.load_data('stocks');frames={str(k):f.reset_index(drop=True) for k,f in st.groupby('Ticker',sort=True)}
    cfg=dict(entry='brk55|none',stop=3.,time=0,act=2.,trail=2.5,maxhold=0);ref=[]
    for t,f in frames.items():
        x=ns.features(f)
        for r,b,dk in ns.simulate(x,s2.entry2(x,cfg['entry']),cfg,ns.COST['stocks'],np.datetime64('2000-01-01'),np.datetime64('2030-01-01')):ref.append((t,pd.Timestamp(dk),round(r,10)))
    with np.errstate(invalid='ignore'):_,tr=run(frames,cost_model=Costs(),slots=100000)
    got=sorted(zip(tr.ticker,pd.to_datetime(tr.entry_date),tr.net_return.round(10)));ref=sorted(ref)
    assert len(got)==len(ref),(len(got),len(ref))
    for a,b in zip(got,ref):assert a[0]==b[0] and a[1]==b[1] and abs(a[2]-b[2])<1e-9,(a,b)
    print('regression OK',len(got),'trades identical')

if __name__=='__main__':main()
