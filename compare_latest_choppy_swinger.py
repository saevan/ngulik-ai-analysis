"""Read-only diagnosis of saved latest secondary and aspirational Swinger fills."""
from pathlib import Path
import pandas as pd
from analyze_portfolio_regimes import attribute

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'choppy_wr_after_stop_results'

def main():
    proxy=pd.read_csv(ROOT/'breakout_er_regime_results/stocks_proxy.csv',parse_dates=['date']).set_index('date')
    cases={'secondary_latest':('choppy_wr_after_stop_results','full_fees_stock_er_0.5'),
           'secondary_stop_only':('choppy_wr_after_stop_results','full_fees_baseline_0'),
           'secondary_original':('choppy_channel_market_only_results','full_fees_range_escape_n10_c8_revFalse'),
           'swinger_ideal':('prototype_swinger_benchmark_results','afl_ideal_net')}
    rows=[]
    for name,(folder,label) in cases.items():
        t=pd.read_csv(ROOT/folder/f'{label}_trades.csv',parse_dates=['entry_date','exit_date'])
        c=pd.read_csv(ROOT/folder/f'{label}_equity.csv',parse_dates=['date']).set_index('date')
        g=t[t.entry_date.map(proxy.regime)=='sideways'];r=g.net_return
        stats,daily=attribute(c,proxy,'stocks',name)
        side=stats[stats.regime=='sideways'].iloc[0];d=daily[daily.regime=='sideways']
        w=r[r>0];l=r[r<0]
        rows.append(dict(system=name,n=len(g),wr=(r>0).mean(),avg_win=w.mean(),avg_loss=-l.mean(),
            mean_return=r.mean(),payout=w.mean()/-l.mean(),mean_bars=g.bars.mean(),
            winner_bars=g.loc[r>0,'bars'].mean(),loser_bars=g.loc[r<0,'bars'].mean(),
            loss_gt10=(r<-.1).mean(),cash=(d.cash/d.equity).mean(),positions=d.positions.mean(),
            positive_days=(d.equity_return>0).mean(),sideways_annual=side.conditional_annualized,
            record_months=side.months_record,months=side.months_present))
    result=pd.DataFrame(rows)
    result.to_csv(OUT/'latest_vs_swinger_choppy.csv',index=False)
    print(result.to_string(index=False))

if __name__=='__main__':main()
