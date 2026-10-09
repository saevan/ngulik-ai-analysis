"""Audit loss formation from entry, first exit signal and actual execution."""
from pathlib import Path
import numpy as np
import pandas as pd
import grid_search_timehunter as engine
from backtest_timehunter_atr import atr_previous

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'choppy_channel_market_only_results'


def main():
    data,_=engine.load_data('stocks')
    frames={}
    for ticker,f in data.groupby('Ticker'):
        f=f.sort_values('Date/Time').reset_index(drop=True)
        f['atr_prior']=atr_previous(f)
        f['exit_level']=f.Low.shift(1).rolling(10).min()
        f['channel_exit']=f.Close<f.exit_level
        f['fade_exit']=(f.Open-f.Low)>=2*f.atr_prior
        frames[str(ticker)]=f
    trades=pd.read_csv(OUT/'full_fees_range_escape_n10_c8_revFalse_trades.csv',parse_dates=['entry_date','exit_date'])
    rows=[]
    for t in trades.itertuples():
        f=frames[t.ticker];dates=pd.DatetimeIndex(f['Date/Time'])
        a=dates.get_loc(t.entry_date);b=dates.get_loc(t.exit_date)
        signal=None
        for i in range(a,b):
            if f.fade_exit.iloc[i] or f.channel_exit.iloc[i]:signal=i;break
        if t.reason in ['fading','custom_exit']:
            assert signal is not None
            expected='fading' if f.fade_exit.iloc[signal] else 'custom_exit'
            assert t.reason==expected
            tradable=np.flatnonzero(f.tradable.to_numpy()[signal+1:])
            assert len(tradable) and signal+1+tradable[0]==b
        else:signal=b
        s=f.iloc[signal];entry=f.iloc[a]
        signal_gross=s.Close/t.entry_price-1
        after_signal=(t.exit_price-s.Close)/t.entry_price
        fees=t.net_return-t.gross_return
        assert np.isclose(signal_gross+after_signal+fees,t.net_return,atol=1e-10)
        rows.append(dict(ticker=t.ticker,entry_date=t.entry_date,exit_date=t.exit_date,reason=t.reason,
            net_return=t.net_return,gross_return=t.gross_return,bars=t.bars,
            signal_gross_return=signal_gross,post_signal_increment=after_signal,fee_increment=fees,
            entry_to_channel_distance=(t.entry_price-entry.exit_level)/t.entry_price,
            entry_atr_fraction=entry.atr_prior/t.entry_price,
            initial_2atr_fraction=2*entry.atr_prior/t.entry_price,
            signal_2atr_fraction=2*s.atr_prior/t.entry_price,
            entry_gap_vs_signal_close=t.entry_price/f.Close.iloc[a-1]-1 if a else np.nan,
            signal_to_exit_bars=b-signal,
            maximum_close_gain=f.Close.iloc[a:b].max()/t.entry_price-1 if b>a else 0,
            both_exit_signals=bool(s.channel_exit and s.fade_exit)))
    detail=pd.DataFrame(rows);detail.to_csv(OUT/'loss_diagnosis_trades.csv',index=False)
    losing=detail[detail.net_return<0];summary=[]
    for name,g in [('all_losses',losing)]+[(str(k),v) for k,v in losing.groupby('reason')]:
        summary.append(dict(group=name,n=len(g),fraction_of_losses=len(g)/len(losing),avg_loss=-g.net_return.mean(),
            signal_gross_return=g.signal_gross_return.mean(),post_signal_increment=g.post_signal_increment.mean(),
            fee_increment=g.fee_increment.mean(),mean_bars=g.bars.mean(),
            entry_to_channel_distance=g.entry_to_channel_distance.mean(),median_channel_distance=g.entry_to_channel_distance.median(),
            initial_2atr_fraction=g.initial_2atr_fraction.mean(),signal_2atr_fraction=g.signal_2atr_fraction.mean(),
            mean_entry_gap=g.entry_gap_vs_signal_close.mean(),delayed_exits=int((g.signal_to_exit_bars>1).sum()),
            once_up5_fraction=(g.maximum_close_gain>.05).mean(),both_signal_count=int(g.both_exit_signals.sum())))
    s=pd.DataFrame(summary);s.to_csv(OUT/'loss_diagnosis_summary.csv',index=False)
    tail=losing[losing.net_return<-.1]
    info=dict(total_trades=len(detail),losses=len(losing),loss_gt10=len(tail),fraction_losers_gt10=len(tail)/len(losing),
        share_sum_percentage_losses_gt10=tail.net_return.sum()/losing.net_return.sum(),
        mean_loss_without_tail=-losing.loc[losing.net_return>=-.1,'net_return'].mean())
    pd.DataFrame([info]).to_csv(OUT/'loss_tail_summary.csv',index=False)
    print(s.to_string(index=False));print(info)


if __name__=='__main__':main()
