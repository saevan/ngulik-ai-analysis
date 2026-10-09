"""Loss timing audit for market-choppy pure signal inversion."""
from pathlib import Path
import numpy as np
import pandas as pd
import grid_search_timehunter as engine
from backtest_breakout_er import efficiency_ratio

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'choppy_head_to_head_results'

def main():
    data,_=engine.load_data('stocks');frames={}
    for ticker,f in data.groupby('Ticker',sort=True):
        f=f.reset_index(drop=True)
        f['breakout']=f.Close>f.High.shift(1).rolling(20).max()
        f['exit_signal']=f.breakout&(efficiency_ratio(f.Close,20)>=.3)
        frames[str(ticker)]=f
    t=pd.read_csv(OUT/'inverse_market_choppy_trades.csv',parse_dates=['entry_date','exit_date'])
    rows=[]
    for r in t.itertuples():
        f=frames[r.ticker];dates=pd.DatetimeIndex(f['Date/Time'])
        a=dates.get_loc(r.entry_date);b=dates.get_loc(r.exit_date)
        ix=np.flatnonzero(f.exit_signal.to_numpy()[a:b])
        if r.reason=='custom_exit':
            assert len(ix);s=a+ix[0]
            nxt=np.flatnonzero(f.tradable.to_numpy()[s+1:])
            assert s+1+nxt[0]==b
        else:s=b
        sg=f.Close.iloc[s]/r.entry_price-1
        post=(r.exit_price-f.Close.iloc[s])/r.entry_price
        fee=r.net_return-r.gross_return
        assert np.isclose(sg+post+fee,r.net_return,atol=1e-10)
        rows.append(dict(ticker=r.ticker,entry_date=r.entry_date,exit_date=r.exit_date,reason=r.reason,
            net_return=r.net_return,bars=r.bars,signal_return=sg,post_signal=post,fee=fee,
            signal_to_fill=b-s,earlier_breakout_blocked_by_er=bool(f.breakout.iloc[a:s].any()),
            minimum_close_return=f.Close.iloc[a:b+1].min()/r.entry_price-1,
            maximum_close_return=f.Close.iloc[a:b+1].max()/r.entry_price-1))
    detail=pd.DataFrame(rows);detail.to_csv(OUT/'inverse_loss_audit.csv',index=False)
    l=detail[detail.net_return<0]
    summary=dict(trades=len(detail),losers=len(l),avg_loss=-l.net_return.mean(),mean_loser_bars=l.bars.mean(),
        loss_at_signal=-l.signal_return.mean(),after_signal_increment=l.post_signal.mean(),fee_increment=l.fee.mean(),
        delayed_fills=int((l.signal_to_fill>1).sum()),terminal_losers=int(l.reason.str.startswith('period_end').sum()),
        losers_with_earlier_breakout_blocked_by_er=int(l.earlier_breakout_blocked_by_er.sum()),
        loss_gt20=int((l.net_return<-.2).sum()),loss_gt50=int((l.net_return<-.5).sum()),
        worst=l.net_return.min())
    pd.DataFrame([summary]).to_csv(OUT/'inverse_loss_summary.csv',index=False)
    print(summary)
    print(l.nsmallest(5,'net_return')[['ticker','entry_date','exit_date','net_return','bars','signal_return','post_signal']].to_string(index=False))

if __name__=='__main__':main()
