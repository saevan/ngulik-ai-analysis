"""Where does Swinger ideal's performance come from? Same signals, five fill assumptions (fee 0.15%/0.25%, 10 slots, Rp1bn):
afl_ideal (level, may be outside the bar), ideal_clamped (level clamped to [Low, High]), close_fill (signal-bar Close),
stop_order (causal stop at the prior level), next_open (causal, next bar Open)."""
import numpy as np, pandas as pd
import grid_search_timehunter as engine
from backtest_prototype_swinger import run_portfolio
from backtest_open_next import stats
from pathlib import Path
OUT=Path(__file__).resolve().parent/'swinger_like_system_results'
f,_=engine.load_data('stocks');frames={str(k):v.reset_index(drop=True) for k,v in f.groupby('Ticker',sort=True)}
rows=[]
for mode in ['afl_ideal','ideal_clamped','close_fill','stop_order','next_open']:
    c,t,cnt=run_portfolio(frames,mode)
    if mode=='afl_ideal':
        ref=pd.read_csv(Path(__file__).resolve().parent/'prototype_swinger_benchmark_results/afl_ideal_net_equity.csv',index_col=0)
        assert np.allclose(ref.equity.to_numpy(),c.equity.to_numpy(),rtol=1e-10),'afl_ideal regression'
    st=stats(c,t);r=t.net_return
    rows.append(dict(mode=mode,**cnt,**{k:st[k] for k in ['cagr','records','months','mdd','n','wr','avg_win','avg_loss','payout','mean','median','mean_bars','invested']},loss_gt10=float((r<-.1).mean())))
    print(rows[-1],flush=True)
pd.DataFrame(rows).to_csv(OUT/'swinger_fill_ladder.csv',index=False)
