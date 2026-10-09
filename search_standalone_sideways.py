"""Chronological selection of independent sideways systems, not merged."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import grid_search_timehunter as engine
from backtest_breakout_er_portfolio import portfolio
from backtest_idx_costs import Costs
from analyze_portfolio_regimes import regime_proxy, attribute

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'standalone_sideways_recovery_results'


def make_entry(config,allowed):
    def signal(f):
        c=f.Close
        if config['family'].startswith('rsi'):
            delta=c.diff();up=delta.clip(lower=0).ewm(alpha=.5,adjust=False,min_periods=2).mean()
            down=(-delta.clip(upper=0)).ewm(alpha=.5,adjust=False,min_periods=2).mean()
            rsi=100*up/(up+down).replace(0,np.nan)
            setup=(rsi<float(config['family'][3:]))&(c>c.rolling(200).mean())
        elif config['family']=='channel_rebound':
            low=f.Low.shift(1).rolling(20).min()
            setup=(f.Low<=low)&(c>low)&(c>c.shift(1))&(c>c.rolling(200).mean())
        else:
            setup=(c>f.High.shift(1).rolling(5).max())&(c>c.rolling(50).mean())
        return setup.shift(1,fill_value=False).to_numpy(bool)&f['Date/Time'].isin(allowed).to_numpy()&f.tradable.to_numpy(bool)
    return signal


def main():
    OUT.mkdir(exist_ok=True)
    data,_=engine.load_data('stocks')
    proxy=regime_proxy(data)
    allowed=set(proxy.index[proxy.regime=='sideways'])
    periods={'train':('2000-01-01','2015-12-31'),'validation':('2016-01-01','2020-12-31'),'test':('2021-01-01','2025-08-15')}
    rows=[]
    configs=[dict(family=f,sma=s,fade=a) for f in ['rsi5','rsi15','channel_rebound','breakout5'] for s in [5,10] for a in [1,2]]
    def run(config,period,scenario='spread',reverse=False):
        start,end=periods[period]
        frames={str(k):f.reset_index(drop=True) for k,f in data[data['Date/Time']<=end].groupby('Ticker',sort=True)}
        builder=make_entry(config,allowed)
        costs=Costs(grid=True,ticks_per_side=1,round_lot=100) if scenario=='spread' else Costs()
        is_breakout=config['family']=='breakout5'
        recovery=lambda f:(f.Close>=f.Close.rolling(config['sma']).mean()).to_numpy(bool)
        curve,t,counts=portfolio(frames,hold=None,exit_sma=config['sma'] if is_breakout else None,
            exit_builder=None if is_breakout else recovery,max_age_signal=None if is_breakout else 20,
            fade=config['fade'],entry_builder=builder,cost_model=costs,reverse=reverse,start=start)
        # No suspension queues may admit an entry after market eligibility has ended.
        # Entries on zero-volume bars are suppressed in the builder below via a next-tradable gate.
        assert t.entry_date.isin(allowed).all()
        years=(curve.index[-1]-curve.index[0]).days/365.25
        stat,_=attribute(curve,proxy,'stocks',period)
        side=stat[stat.regime=='sideways'].iloc[0]
        r=t.net_return;loss=-t.loc[t.pnl<0,'pnl'].sum()
        row=dict(**config,period=period,scenario=scenario,reverse=reverse,n=len(t),cagr=(curve.equity.iloc[-1]/1e9)**(1/years)-1,
            mdd=curve.drawdown.min(),pf=t.loc[t.pnl>0,'pnl'].sum()/loss if loss else np.nan,wr=(r>0).mean(),mean_return=r.mean(),
            sideways_annual=side.conditional_annualized,records=int(curve.new_high.groupby(curve.index.to_period('M')).any().sum()),
            months=curve.index.to_period('M').nunique(),cash=(curve.cash/curve.equity).mean(),**counts)
        label=f'{period}_{scenario}_{config["family"]}_s{config["sma"]}_f{config["fade"]}_rev{reverse}'
        curve.to_csv(OUT/f'{label}_equity.csv');t.to_csv(OUT/f'{label}_trades.csv',index=False)
        rows.append(row);pd.DataFrame(rows).to_csv(OUT/'comparison.csv',index=False)
        print(label,f'CAGR {row["cagr"]:.2%}, PF {row["pf"]:.2f}, N {len(t)}, sideways {row["sideways_annual"]:.2%}',flush=True)
        return row
    # Entry signals require tradable current bar to avoid carrying stale market-regime orders.
    for cfg in configs:run(cfg,'train')
    eligible=[r for r in rows if r['n']>=40 and r['cagr']>0 and r['pf']>1.1 and r['sideways_annual']>0]
    chosen=max(eligible if eligible else rows,key=lambda r:r['cagr'])
    config={k:chosen[k] for k in ['family','sma','fade']}
    (OUT/'frozen_selection.json').write_text(json.dumps(dict(config=config,train_pass=bool(eligible),selection='highest training spread CAGR among n>=40,PF>1.1,CAGR>0,sideways>0; otherwise highest CAGR diagnostic only',periods=periods),indent=2),encoding='utf-8')
    for period in ['validation','test']:run(config,period)
    for period in periods:run(config,period,'fees')
    run(config,'test','spread',True)
    lines=['# Standalone sideways research','',
        '16 predefined training combinations: RSI2<5/15 aboveSMA200; 20bar support rejection with risingClose aboveSMA200; or5bar breakout aboveSMA50. All require prior-completed-bar equal-weight market proxy sideways. Individual stocks need not themselves be choppy: breakout family searches relative strength within a sideways market. Independent entry, no main strategy positions.', '',
        'For RSI/support-rebound, exit Close>=SMA5/10 (recovery) or age20 signals nextOpen. For breakout, exit Close<SMA5/10 without age cap. All retain currentOpen-Low>=1/2priorATR fading next tradable Open. No hold200. Initial control experiment with below-SMA exits on all families is archived in standalone_sideways_results; this recovery version corrects exit direction for mean-reversion families after observing that control. Thus this entire research is adaptive, despite freezing this version before its validation/test. RSI uses explicitly implemented ewm(alpha0.5,adjustFalse) with2observations; no claim of exact AmiBroker RSI initialization. Entry only on tradable bars, expired setup not queued. Terminal closures for each separate period remain.', '',
        'Train2000-2015, validation2016-2020, finaltest2021-2025Aug15. Frozen single candidate chosen only from train, no retuning on validation/test. Entire historical dataset was already examined in earlier research: these are chronological non-selection periods for this run, NOT genuinely untouched external data. Same survivorship/corporateaction/universe and capacity limitations.', '',
        'InitialRp1billion for each period, max10positions/10%previous-equity sizing, cash-constrained compounding. Feesbuy0.15%sell0.25%. Selection uses modern-grid/100share-lot plus1tick each side stress, not historical observed bid/ask; fee-only sensitivity also shown. SMA/fade nextOpen executions; signal built with full earlier warmup. No merging or active AFL changes.', '',
        'Success requires positive CAGR,PF>1.1,positive sideways attribution and>=40trades in train and both later windows; reverse test must remain positive. This is a research gate, not seven universal criteria. Sideways annual equivalent concatenates disjoint marked-equity days, not standalone CAGR. All actual entries checked against causal regime eligibility; accounting and return attribution reconciled.', '',
        '| Period | Costs | Family | SMA | Fade | Reverse | CAGR | PF | Trades | Sideways equivalent |',
        '|---|---|---|---:|---:|---|---:|---:|---:|---:|']
    for r in pd.DataFrame(rows).itertuples():
        lines.append(f'| {r.period} | {r.scenario} | {r.family} | {r.sma} | {r.fade} | {r.reverse} | {r.cagr:.2%} | {r.pf:.2f} | {r.n} | {r.sideways_annual:.2%} |')
    (OUT/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')


if __name__=='__main__':main()
