"""Claim: the longer we hold, the higher the profit -> exit only on a price drop (fading from the latest Open).
Part 1 (this file): does return rise with holding time? Fixed-horizon exits T bars after a breakout entry (signal level, fees only,
no spread, overlapping signals) versus random entries as a control; plus the per-bar return (profit per unit of time).
Part 2 (hold_time_portfolio.py): portfolio test of fade-only exits."""
import numpy as np, pandas as pd
from pathlib import Path
import time_price_study as tp
from uts.data import load_stocks, frames
OUT=Path(__file__).resolve().parent/'time_price_results'
tp.H=251
fr=frames(load_stocks())
sets={'breakout_er':tp.build(fr)}
p=len(sets['breakout_er'])/sum(int(f.tradable.sum()) for f in fr.values())
sets['random']=tp.build(fr,random_p=p)
rows=[]
for name,rs in sets.items():
    pk=tp.pack(rs);yr=pd.DatetimeIndex(pk['date']).year.to_numpy()
    for per,m in {'train_2000_2015':yr<=2015,'holdout_2016_2025':yr>=2016}.items():
        for T in [5,10,20,40,60,90,120,180,250]:
            r,b=tp.simulate(pk,None,None,T)
            r=r[m];b=b[m];lg=np.log1p(r)
            rows.append(dict(entry=name,period=per,T=T,n=len(r),mean=r.mean(),median=np.median(r),wr=(r>0).mean(),mean_per_bar=lg.mean()/b[m].mean() if False else lg.mean()/T,
                p10=np.percentile(r,10),p90=np.percentile(r,90)))
d=pd.DataFrame(rows);d.to_csv(OUT/'hold_time_signal.csv',index=False)
pd.set_option('display.width',200)
print(d.round(4).to_string(index=False))
