"""Controlled exit mitigation for second system only, not the main strategy."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import grid_search_timehunter as engine
from backtest_breakout_er_portfolio import portfolio
from backtest_idx_costs import Costs
from search_choppy_channel_system import builders
from analyze_portfolio_regimes import regime_proxy,attribute

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'choppy_loss_mitigation_results'


def main():
    OUT.mkdir(exist_ok=True)
    data,_=engine.load_data('stocks');proxy=regime_proxy(data)
    frames={str(k):f.reset_index(drop=True) for k,f in data.groupby('Ticker',sort=True)}
    allowed=set(proxy.index[proxy.regime=='sideways'])
    entry,_=builders(dict(family='range_escape',length=10,cost_multiple=8,stock_choppy=False),allowed)
    configs=[(10,None),(10,.5),(10,1),(10,1.5),(10,2),(5,None),(3,None),(5,1)]
    (OUT/'PLAN.json').write_text(json.dumps(dict(configs=configs,entry='unchanged Choppy RangeEscape10 cost8 marketER<0.3',stop='Close <= actual entry fill - k*ATR14 known before entry; next tradable Open; no guaranteed loss cap'),indent=2),encoding='utf-8')
    rows=[];period_rows=[]
    def run(channel,stop,scenario,reverse=False):
        costs=Costs() if scenario=='fees' else Costs(grid=True,ticks_per_side=1,round_lot=100)
        exit_signal=lambda f:(f.Close<f.Low.shift(1).rolling(channel).min()).to_numpy(bool)
        curve,t,counts=portfolio(frames,hold=None,fade=2,entry_builder=entry,exit_builder=exit_signal,
            cost_model=costs,entry_stop_atr=stop,reverse=reverse)
        if channel==10 and stop is None and not reverse:
            old=pd.read_csv(ROOT/'choppy_channel_market_only_results'/f'full_{scenario}_range_escape_n10_c8_revFalse_equity.csv')
            np.testing.assert_allclose(curve.equity,old.equity,rtol=1e-10)
        assert t.entry_date.isin(allowed).all()
        r=t.net_return;w=r[r>0];l=r[r<0];years=(curve.index[-1]-curve.index[0]).days/365.25
        stats,_=attribute(curve,proxy,'stocks',str(channel));s=stats[stats.regime=='sideways'].iloc[0]
        months=curve.new_high.groupby(curve.index.to_period('M')).any()
        row=dict(channel=channel,stop=stop,scenario=scenario,reverse=reverse,n=len(t),wr=(r>0).mean(),avg_win=w.mean(),avg_loss=-l.mean(),
            mean_return=r.mean(),payout=w.mean()/-l.mean(),loss_gt10=(r<-.1).mean(),cagr=(curve.equity.iloc[-1]/1e9)**(1/years)-1,
            mdd=curve.drawdown.min(),records=int(months.sum()),months=len(months),mean_bars=t.bars.mean(),
            sideways_annual=s.conditional_annualized,sideways_records=s.months_record,
            stop_exits=int((t.reason=='entry_atr_stop').sum()),**counts)
        rows.append(row)
        label=f'{scenario}_low{channel}_stop{stop}_rev{reverse}'
        curve.to_csv(OUT/f'{label}_equity.csv');t.to_csv(OUT/f'{label}_trades.csv',index=False)
        for start,end in [('2000','2015'),('2016','2020'),('2021','2025')]:
            g=curve.loc[start:end];initial=curve.equity.shift(1).fillna(1e9).loc[g.index[0]]
            period_rows.append(dict(variant=label,period=f'{start}-{end}',total_return=g.equity.iloc[-1]/initial-1))
        pd.DataFrame(rows).to_csv(OUT/'comparison.csv',index=False)
        pd.DataFrame(period_rows).to_csv(OUT/'periods.csv',index=False)
        print(label,f'avg loss {row["avg_loss"]:.2%}, WR {row["wr"]:.2%}, CAGR {row["cagr"]:.2%}, side {row["sideways_annual"]:.2%}',flush=True)
    for channel,stop in configs:
        for scenario in ['fees','spread']:run(channel,stop,scenario)
    # Stress-CAGR selection only among variants that actually reduce mean loss.
    base=next(r for r in rows if r['scenario']=='spread' and r['channel']==10 and r['stop'] is None)
    eligible=[r for r in rows if r['scenario']=='spread' and r['avg_loss']<base['avg_loss']]
    selected=max(eligible,key=lambda r:r['cagr']) if eligible else base
    for scenario in ['fees','spread']:
        run(10,None,scenario,True)
        if selected is not base:run(selected['channel'],selected['stop'],scenario,True)
    lines=['# Second-system loss mitigation','',
        'Entry unchanged: Choppy RangeEscape10, completed marketER<0.3, cost/range filter8, next tradable Open, only positive-volume entry bars. No changes to primary system or active AFL. Exit baseline priorLLV10 or fading2 priorATR, no hold200. Compare fixed-entry-ATR Close stop0.5/1/1.5/2; channelLLV5/3; and channel5+stop1.', '',
        'Stop uses ATR14 from immediately before entry, fixed for trade lifetime, actual entry fill price. Close<=entry-k*ATR triggers next tradable Open, including suspension delay. This is a completed-bar stop SIGNAL, not an intraday resting stop or guaranteed maximum percentage loss; gaps/fees can exceed threshold. It does not use future High/Low to assign an ideal fill. First pending exit preserved; stop gets reason priority on simultaneous new signals. Existing fading still referenced to each current bar Open.', '',
        'Stocks2000-2025Aug15, initialRp1billion, ten slots,10%prior-equity sizing/cashcap compounding. Buy0.15%sell0.25%. Spread stress currentgrid/100shares and1tick each side counterfactually across history, not observed historicalbidask. Earlier dataset/action/liquidity/survivorship limits unchanged. Main entry same but realized trades may differ because exits free cash/slots.', '',
        '8configurations x2costs plus reversed-priority baseline/selected sensitivity. Selection highest full-sample spreadCAGR among avg-loss-improving variants, so exploratory in-sample, not independent validation or seven-criteria pass. Time slices are continuous-portfolio descriptive returns, not reset holdouts. Sideways equivalent attributes disjoint dailyreturns, not standalone CAGR. No automatic adoption.', '',
        'Baseline curves exact regression; cash/slot/PnL, marketeligibility and regime attribution checked. Unit tests cover fixedentryATR, gap nextOpen, intradaytouch not Close signal, and suspended exit surviving recovery.', '',
        '| Costs | LLV | Stop ATR | Reverse | Avg loss | Avg win | WR | CAGR | MDD | Records /308 | Sideways equivalent |',
        '|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|']
    for r in pd.DataFrame(rows).itertuples():
        lines.append(f'| {r.scenario} | {r.channel} | {r.stop} | {r.reverse} | {r.avg_loss:.2%} | {r.avg_win:.2%} | {r.wr:.2%} | {r.cagr:.2%} | {r.mdd:.2%} | {r.records} | {r.sideways_annual:.2%} |')
    (OUT/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')


if __name__=='__main__':main()
