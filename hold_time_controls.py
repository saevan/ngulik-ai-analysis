"""Controls for hold_time_portfolio.py: is the gain from the fade-from-latest-Open exit, or from the long time stop / 3 ATR stop?
Time-only and stop+time exits at longer horizons (no fade), and random-entry controls for the best-looking fade combinations."""
from multiprocessing import Pool
import numpy as np, pandas as pd
import grid_search_timehunter as engine
from backtest_open_next import run, stats
import time_price_portfolio as tpp
FR=tpp.FR;WIN=tpp.WIN
EX=[(f'T{T}',dict(stop=None,max_bars=T)) for T in (60,90,120,180,250)]
EX+=[(f'SL3_T{T}',dict(stop=3,max_bars=T)) for T in (60,90,120,180,250)]+[('SL3_only',dict(stop=3))]
EX+=[('FADE8+SL3+T120',dict(stop=3,fade=.08,max_bars=120)),('FADEP8+SL3+T120',dict(stop=3,fade=.08,fade_profit_only=True,max_bars=120))]
RAND=[('SL3_T120',dict(stop=3,max_bars=120)),('FADEP8+SL3+T120',dict(stop=3,fade=.08,fade_profit_only=True,max_bars=120))]
P=None
def job(a):
    lab,kw,w,entry,seed=a
    fr={t:g for t,f in FR.items() if len(g:=f[f['Date/Time']<=WIN[w][1]])}
    sig=tpp.sig_breakout if entry=='breakout' else tpp.make_random(P,seed)
    with np.errstate(invalid='ignore',divide='ignore'):c,t=run(fr,signal=sig,act=1e9,trail=0,cost_model=tpp.COST,start=WIN[w][0],**kw)
    return dict(exit=lab,window=w,entry=entry,seed=seed,**stats(c,t))
def main():
    global P
    st,_=engine.load_data('stocks')
    for k,f in st.groupby('Ticker',sort=True):FR[str(k)]=f.reset_index(drop=True)
    P=sum(int(tpp.sig_breakout(f).sum()) for f in FR.values())/sum(int(f.tradable.sum()) for f in FR.values())
    tasks=[(l,kw,w,'breakout',0) for l,kw in EX for w in WIN]+[(l,kw,'full','random',s) for l,kw in RAND for s in range(3)]
    with Pool(4) as p:rows=p.map(job,tasks,chunksize=1)
    pd.DataFrame(rows).to_csv(tpp.OUT/'hold_time_controls.csv',index=False);print('done')
if __name__=='__main__':main()
