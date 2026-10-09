"""Descriptive outcome profile versus the user-selected ideal benchmark."""
from pathlib import Path
import numpy as np
import pandas as pd
from analyze_portfolio_regimes import attribute

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'swinger_character_results'


def longest_run(values):
    best=current=0
    for v in values:
        current=current+1 if v else 0
        best=max(best,current)
    return best


def main():
    OUT.mkdir(exist_ok=True)
    proxy=pd.read_csv(ROOT/'breakout_er_regime_results/stocks_proxy.csv',parse_dates=['date']).set_index('date')
    cases={'ours':(ROOT/'fading_sma30_results','breakout_ER_fees_fade2'),
           'swinger':(ROOT/'prototype_swinger_benchmark_results','afl_ideal_net')}
    trade_rows=[];daily_rows=[];all_rows=[]
    for label,(base,name) in cases.items():
        t=pd.read_csv(base/f'{name}_trades.csv',parse_dates=['entry_date','exit_date'])
        c=pd.read_csv(base/f'{name}_equity.csv',parse_dates=['date']).set_index('date')
        t['entry_regime']=t.entry_date.map(proxy.regime)
        for group,g in [('all',t),('sideways_entry',t[t.entry_regime=='sideways'])]:
            r=g.net_return;w=g[r>0];l=g[r<0]
            positive=r[r>0].sum();top=max(1,int(np.ceil(len(w)*.1)))
            row=dict(system=label,group=group,n=len(g),wr=(r>0).mean(),avg_win=w.net_return.mean(),
                avg_loss=-l.net_return.mean(),payout=w.net_return.mean()/-l.net_return.mean(),
                return_pf=positive/-r[r<0].sum(),mean_return=r.mean(),median_return=r.median(),
                p10_return=r.quantile(.1),p90_return=r.quantile(.9),p99_return=r.quantile(.99),
                mean_bars=g.bars.mean(),median_bars=g.bars.median(),p90_bars=g.bars.quantile(.9),
                winner_bars=w.bars.mean(),loser_bars=l.bars.mean(),win_gt20_fraction=(r>.2).mean(),
                loss_gt10_fraction=(r<-.1).mean(),top10pct_winners_share=w.net_return.nlargest(top).sum()/positive,
                longest_loss_run=longest_run(g.sort_values(['exit_date','ticker']).net_return<=0))
            assert np.isclose(row['mean_return'],len(w)/len(g)*row['avg_win']-len(l)/len(g)*row['avg_loss'])
            trade_rows.append(row)
        stats,table=attribute(c,proxy,'stocks',label)
        for group,g in [('all',table),('sideways',table[table.regime=='sideways'])]:
            r=g.equity_return
            daily_rows.append(dict(system=label,group=group,days=len(g),positive_fraction=(r>0).mean(),
                average_positive=r[r>0].mean(),average_negative=-r[r<0].mean(),
                mean_daily=r.mean(),daily_std=r.std(),p01_daily=r.quantile(.01),p99_daily=r.quantile(.99),
                mean_cash=(g.cash/g.equity).mean(),mean_positions=g.positions.mean(),
                record_days=int(g.new_high.sum())))
        monthly=c.new_high.groupby(c.index.to_period('M')).any()
        s=stats[stats.regime=='sideways'].iloc[0]
        years=(c.index[-1]-c.index[0]).days/365.25
        all_rows.append(dict(system=label,cagr=(c.equity.iloc[-1]/1e9)**(1/years)-1,mdd=c.drawdown.min(),
            record_months=int(monthly.sum()),months=len(monthly),longest_no_record_months=longest_run(~monthly),
            underwater_days=longest_run(c.drawdown<0),sideways_annual_equivalent=s.conditional_annualized,
            sideways_record_months=s.months_record,sideways_months=s.months_present))
    for name,rows in [('trades',trade_rows),('daily',daily_rows),('portfolio',all_rows)]:
        result=pd.DataFrame(rows);result.to_csv(OUT/f'{name}.csv',index=False)
        print(name);print(result.to_string(index=False))
    (OUT/'METHODOLOGY.md').write_text('''# Outcome characteristics

User-selected Swinger ideal is the reference target. Our candidate is Breakout+ER, SMA30 exit, fade2 ATR, no time cap, NOT the active pullback AFL. Existing 2000-2025 simulations, identical initialRp1billion/10slot compounding, buy0.15%sell0.25%, no spread. No retuning or new strategy in this comparison.

Trade return stats use fee-inclusive percentage return per completed trade; win/loss averages and return PF use equal trade weighting. Portfolio money PF is different because notional changes with compounding. Zero-return trades count in denominator but neither win nor loss average. Expectancy identity reconciled. Sideways-entry subset groups trades by market proxy regime known at entry and uses FULL lifetime return, including subsequent other regimes; do not confuse it with daily sideways attribution. Mean holding differs from median; win/lose durations conditional on realized outcome are descriptive, not future-known exit signals.

Daily sideways profile instead uses actual marked portfolio return only on days tagged sideways by previous-completed-bar proxy ER. Positions from other regimes remain included. Existing attribution reconciles to whole-history CAGR. Conditional annual equivalent is not independently tradable regime CAGR. Record month at least one all-time daily equity high, partial edge months included, peak never reset. Longest underwater duration counts observed daily bars, not calendar days. Loss streak sorted by exitdate/ticker is an ordering convention for concurrent positions.

Top10% winner share uses the largest ceil(10% of winning trades) fee-inclusive percentage gains, not contribution to portfolio CAGR. Profile differences describe outcomes, not causal attribution to a particular entry or exit. Matching one or all summary statistics does not guarantee equal CAGR because sizing, timing, correlation and sequences matter. Same in-sample universe/data limitations apply. Ideal benchmark retains documented fill assumptions; this report accepts it as an aspirational target rather than rearguing benchmark choice.
''',encoding='utf-8')


if __name__=='__main__':main()
