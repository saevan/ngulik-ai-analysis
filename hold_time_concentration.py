"""SL3_T250 (3 ATR close stop + 250-bar time exit, no fade) looked extreme (CAGR 44.5% full, 85% holdout). Concentration + random-entry control."""
import numpy as np, pandas as pd
import grid_search_timehunter as engine
from backtest_open_next import run, stats
import time_price_portfolio as tpp
st,_=engine.load_data('stocks')
for k,f in st.groupby('Ticker',sort=True):tpp.FR[str(k)]=f.reset_index(drop=True)
FR=tpp.FR;P=sum(int(tpp.sig_breakout(f).sum()) for f in FR.values())/sum(int(f.tradable.sum()) for f in FR.values())
out=[]
for w in ['full','holdout']:
    fr={t:g for t,f in FR.items() if len(g:=f[f['Date/Time']<=tpp.WIN[w][1]])}
    for entry,seed in [('breakout',0),('random',0),('random',1),('random',2)]:
        sig=tpp.sig_breakout if entry=='breakout' else tpp.make_random(P,seed)
        with np.errstate(invalid='ignore',divide='ignore'):c,t=run(fr,signal=sig,stop=3,act=1e9,trail=0,max_bars=250,cost_model=tpp.COST,start=tpp.WIN[w][0])
        s=stats(c,t);pnl=t.pnl.sort_values(ascending=False)
        top=t.loc[pnl.index[:5]]
        out.append(dict(window=w,entry=entry,seed=seed,cagr=s['cagr'],mdd=s['mdd'],n=s['n'],wr=s['wr'],top5_share=float(pnl.head(5).sum()/pnl.sum()),top10_share=float(pnl.head(10).sum()/pnl.sum()),
            cagr_without_top5=float(((c.equity.iloc[-1]-pnl.head(5).sum())/1e9)**(365.25/(c.index[-1]-c.index[0]).days)-1),top_tickers=','.join(top.ticker)))
        print(out[-1],flush=True)
pd.DataFrame(out).to_csv(tpp.OUT/'hold_time_concentration.csv',index=False)
