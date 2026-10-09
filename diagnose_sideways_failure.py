"""Describe losing standalone candidate without assigning untested causality."""
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'standalone_sideways_recovery_results'
rows=[];exits=[]
for period in ['train','validation','test']:
    t=pd.read_csv(OUT/f'{period}_fees_channel_rebound_s10_f1_revFalse_trades.csv')
    r=t.net_return;w=r[r>0];l=r[r<0]
    rows.append(dict(period=period,n=len(t),wr=(r>0).mean(),avg_win=w.mean(),avg_loss=-l.mean(),
        mean_net=r.mean(),mean_gross=t.gross_return.mean(),median_net=r.median(),
        break_even_wr=(-l.mean())/(w.mean()-l.mean()),payout=w.mean()/-l.mean(),
        mean_win_bars=t.loc[r>0,'bars'].mean(),mean_loss_bars=t.loc[r<0,'bars'].mean(),
        loss_gt10=(r<-.1).mean(),terminal_count=t.reason.str.startswith('period_end').sum()))
    for reason,g in t.groupby('reason'):
        exits.append(dict(period=period,reason=reason,n=len(g),fraction=len(g)/len(t),wr=(g.net_return>0).mean(),
            mean_net=g.net_return.mean(),mean_gross=g.gross_return.mean(),mean_bars=g.bars.mean(),
            pnl=g.pnl.sum()))
for name,items in [('failure_profile',rows),('failure_exits',exits)]:
    result=pd.DataFrame(items);result.to_csv(OUT/f'{name}.csv',index=False)
    print(name);print(result.to_string(index=False))
