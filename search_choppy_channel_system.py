"""New independent choppy module: preserve winners, cost-aware entry selection."""
from pathlib import Path
import argparse
import json
import numpy as np
import pandas as pd
import grid_search_timehunter as engine
from backtest_timehunter_atr import atr_previous
from backtest_breakout_er import efficiency_ratio
from backtest_prototype_swinger import signals as swing_signals
from backtest_breakout_er_portfolio import portfolio
from backtest_idx_costs import Costs
from analyze_portfolio_regimes import regime_proxy, attribute

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'choppy_channel_system_results'


def builders(cfg,allowed):
    def arrays(f):
        c=f.Close;a=atr_previous(f);n=cfg['length']
        if cfg['family']=='channel_flip':
            s=swing_signals(f,n);setup=s.buy;exit_signal=s.sell
        elif cfg['family']=='range_escape':
            setup=c>f.High.shift(1).rolling(n).max()
            exit_signal=c<f.Low.shift(1).rolling(n).min()
        else:
            support=f.Low.shift(1).rolling(n).min()
            setup=(f.Low<support)&(c>support+.5*a)&(c>c.shift(1))
            exit_signal=c<f.Low.shift(1).rolling(n).min()
        # Estimate trading friction from completed signal Close, not future entry Open.
        tick=np.select([c<200,c<500,c<2000,c<5000],[1.,2.,5.,10.],default=25.)
        ask=np.ceil(c/tick+1)*tick;bid=np.maximum(tick,np.floor(c/tick-1)*tick)
        cost=ask*1.0015-bid*.9975
        width=f.High.rolling(20).max()-f.Low.rolling(20).min()
        eligible=(a>0)&(width>=cfg['cost_multiple']*cost)
        if cfg.get('stock_choppy',True):eligible=eligible&(efficiency_ratio(c,20)<.3)
        # Stock choppy plus market choppy; no forced entry merely to use cash.
        entry=(setup&eligible).shift(1,fill_value=False).to_numpy(bool)
        entry = entry & f['Date/Time'].isin(allowed).to_numpy() & f.tradable.to_numpy(bool)
        return entry,exit_signal.fillna(False).to_numpy(bool)
    return lambda f:arrays(f)[0],lambda f:arrays(f)[1]


def main():
    global OUT
    parser=argparse.ArgumentParser();parser.add_argument('--market-only',action='store_true')
    args=parser.parse_args()
    if args.market_only:OUT=ROOT/'choppy_channel_market_only_results'
    OUT.mkdir(exist_ok=True)
    data,_=engine.load_data('stocks');proxy=regime_proxy(data)
    allowed=set(proxy.index[proxy.regime=='sideways'])
    windows={'train':('2000-01-01','2015-12-31'),'validation':('2016-01-01','2020-12-31'),'test':('2021-01-01','2025-08-15'),'full':('2000-01-01','2025-08-15')}
    families=['channel_flip','range_escape'] if args.market_only else ['channel_flip','range_escape','failed_breakdown']
    configs=[dict(family=f,length=n,cost_multiple=k,stock_choppy=not args.market_only) for f in families for n in [5,10] for k in [8,16]]
    (OUT/'PLAN.json').write_text(json.dumps(dict(configs=configs,windows=windows,selection='Highest training spread CAGR among N>=50,PF>1.1,meanReturn>0,positiveCAGR and positive sideways attribution; otherwise best diagnostic only',target='Swinger ideal outcome profile, no need identical trades',main_unchanged=True),indent=2),encoding='utf-8')
    rows=[]
    def run(cfg,window,scenario='spread',reverse=False):
        start,end=windows[window]
        frames={str(k):f.reset_index(drop=True) for k,f in data[data['Date/Time']<=end].groupby('Ticker',sort=True)}
        entry,exit_signal=builders(cfg,allowed)
        for f in frames.values():
            cut=len(f)//2
            np.testing.assert_array_equal(entry(f.iloc[:cut]),entry(f)[:cut])
            np.testing.assert_array_equal(exit_signal(f.iloc[:cut]),exit_signal(f)[:cut])
        cost=Costs(grid=True,ticks_per_side=1,round_lot=100) if scenario=='spread' else Costs()
        curve,t,counts=portfolio(frames,hold=None,fade=2,entry_builder=entry,exit_builder=exit_signal,
            cost_model=cost,start=start,reverse=reverse)
        assert t.entry_date.isin(allowed).all()
        stats,_=attribute(curve,proxy,'stocks',window);side=stats[stats.regime=='sideways'].iloc[0]
        r=t.net_return;w=r[r>0];l=r[r<0];years=(curve.index[-1]-curve.index[0]).days/365.25
        monthly=curve.new_high.groupby(curve.index.to_period('M')).any()
        row=dict(**cfg,window=window,scenario=scenario,reverse=reverse,n=len(t),wr=(r>0).mean(),
            avg_win=w.mean(),avg_loss=-l.mean(),payout=w.mean()/-l.mean(),mean_return=r.mean(),
            pf=t.loc[t.pnl>0,'pnl'].sum()/-t.loc[t.pnl<0,'pnl'].sum(),
            cagr=(curve.equity.iloc[-1]/1e9)**(1/years)-1,mdd=curve.drawdown.min(),records=int(monthly.sum()),months=len(monthly),
            mean_bars=t.bars.mean(),sideways_annual=side.conditional_annualized,sideways_records=side.months_record,sideways_months=side.months_present,
            cash=(curve.cash/curve.equity).mean(),**counts)
        label=f'{window}_{scenario}_{cfg["family"]}_n{cfg["length"]}_c{cfg["cost_multiple"]}_rev{reverse}'
        curve.to_csv(OUT/f'{label}_equity.csv');t.to_csv(OUT/f'{label}_trades.csv',index=False)
        rows.append(row);pd.DataFrame(rows).to_csv(OUT/'comparison.csv',index=False)
        print(label,f'CAGR {row["cagr"]:.2%}, PF {row["pf"]:.2f}, WR {row["wr"]:.2%}, N{len(t)}, side {row["sideways_annual"]:.2%}',flush=True)
        return row
    for cfg in configs:run(cfg,'train')
    passed=[r for r in rows if r['n']>=50 and r['cagr']>0 and r['pf']>1.1 and r['mean_return']>0 and r['sideways_annual']>0]
    chosen=max(passed or rows,key=lambda r:r['cagr'])
    cfg={k:chosen[k] for k in ['family','length','cost_multiple','stock_choppy']}
    (OUT/'FROZEN.json').write_text(json.dumps(dict(config=cfg,training_pass=bool(passed)),indent=2),encoding='utf-8')
    for window in ['validation','test']:run(cfg,window)
    for window in ['train','validation','test','full']:run(cfg,window,'fees')
    run(cfg,'test','spread',True);run(cfg,'full','spread')
    lines=['# Independent choppy channel system','',
        f'Market-only control={args.market_only}. When True, ONLY market proxy must be choppy; individual-stock ER gate removed. This control asks whether stocks need to be individually choppy during a choppy market. Definitions below that mention stock ER apply only to strict mode. Candidate count={len(configs)}. This extra control is adaptive research after inspecting earlier strict-mode failures; not a pristine holdout.', '',
        'Purpose: imitate outcome characteristics of the user-selected Swinger ideal benchmark, not identical transactions. Three new candidate entries with ER stock20<0.30 AND prior-completed-bar equal-weight market proxy ER<0.30: channel state flip (same completed-close Cross definition as Swinger, nextOpen fill); range escape above priorHigh5/10; or failed breakdown below priorLow5/10 with Close recovery at least0.5priorATR and risingClose. No main-system merge.', '',
        'New cost-aware selection: preceding completed20bar High-Low width must exceed8/16times estimated roundtrip fee+1tick each side at signalClose. Estimate uses modern IDX grid/0.15%buy/0.25%sell; dimensionless range/cost multiple, no future entry quote. This filter is explicitly based on a synthetic modern-grid cost assumption, not universally valid historical prices. Units in bars and ratios, but cross-market applicability untested.', '',
        'Exit: channel-flip opposite Close crossing for that family; other families Close below previousLow5/10. All retain currentOpen-Low>=2previousATR fade. Completed signals execute next tradable Open; no time cap, no early fixed take-profit. Entry only on positive-volume observations, no stale entry queue. Existing positions can persist after regime changes. Terminal closures/marks remain. No lookahead clamps or ideal signal-bar fills.', '',
        'Independent portfolio initialRp1billion, ten slots,10%prior-equity sizing/cashcap/compounding, one ticker position. Fees0.15%buy/0.25%sell. Spread stress modern grid/100shares plus1tick each side applied counterfactually across history, not observed bid/ask. Selected universe, adjusted-looking quotes, actions, survivorship and liquidity/capacity limits remain.', '',
        'Twelve parameter sets selected using2000-2015 only, frozen candidate then2016-2020 and2021-2025; fee-only/full-period/reverse-order checks. Earlier projects already examined these historical years, so this is chronological validation within adaptive research, not pristine independent holdout. PLAN.json and FROZEN.json define selection; if no training pass, subsequent runs diagnostic only. No claim of seven-criteria/benchmark success merely from positive CAGR.', '',
        'Prefix causality for entries/exits, market eligibility, cash/slot/PnL and attribution reconciliation checked. Sideways annual equivalent is daily attribution over disjoint dates, not standalone CAGR. Report both equity metrics and trade win/loss shape. Main AFL unchanged.', '',
        '| Window | Costs | Family | Length | Cost multiple | Reverse | CAGR | PF money | WR | Avg win | Avg loss | Mean bars | Record months | Sideways equivalent |',
        '|---|---|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in pd.DataFrame(rows).itertuples():
        lines.append(f'| {r.window} | {r.scenario} | {r.family} | {r.length} | {r.cost_multiple} | {r.reverse} | {r.cagr:.2%} | {r.pf:.2f} | {r.wr:.2%} | {r.avg_win:.2%} | {r.avg_loss:.2%} | {r.mean_bars:.1f} | {r.records}/{r.months} | {r.sideways_annual:.2%} |')
    (OUT/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')


if __name__=='__main__':main()
