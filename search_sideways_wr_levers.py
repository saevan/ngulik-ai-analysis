"""One-factor-at-a-time sensitivity of sideways win rate and expectancy."""
from pathlib import Path
import numpy as np
import pandas as pd
import grid_search_timehunter as engine
from backtest_breakout_er import efficiency_ratio
from backtest_breakout_er_portfolio import portfolio
from backtest_idx_costs import Costs

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'sideways_wr_levers_results'
BASE=dict(er=.3,support=20,confirm='close_up',target=10,fade=1.,age=20)


def signal_builder(cfg,allowed):
    def signal(f):
        c=f.Close;support=f.Low.shift(1).rolling(cfg['support']).min()
        setup=(efficiency_ratio(c,20)<cfg['er'])&(c>c.rolling(200).mean())&(f.Low<=support)&(c>support)
        if cfg['confirm']=='close_up':setup &= c>c.shift(1)
        elif cfg['confirm']=='above_high':setup &= c>f.High.shift(1)
        return setup.shift(1,fill_value=False).to_numpy(bool)&f['Date/Time'].isin(allowed).to_numpy()&f.tradable.to_numpy(bool)
    return signal


def main():
    OUT.mkdir(exist_ok=True)
    data,_=engine.load_data('stocks')
    proxy=pd.read_csv(ROOT/'breakout_er_regime_results/stocks_proxy.csv',parse_dates=['date']).set_index('date')
    allowed=set(proxy.index[proxy.regime=='sideways'])
    frames={str(k):f.reset_index(drop=True) for k,f in data.groupby('Ticker',sort=True)}
    variants=[('baseline',BASE)]
    for key,values in [('er',[.1,.2,.4]),('support',[10,40]),('confirm',['none','above_high']),
                       ('target',[5,20]),('fade',[.5,2]),('age',[5,10])]:
        variants.extend((f'{key}_{v}',{**BASE,key:v}) for v in values)
    rows=[];period_rows=[]
    for label,cfg in variants:
        builder=signal_builder(cfg,allowed)
        for f in frames.values():
            cut=len(f)//2
            np.testing.assert_array_equal(builder(f.iloc[:cut]),builder(f)[:cut])
        for scenario,cost in [('fees',Costs()),('spread',Costs(grid=True,ticks_per_side=1,round_lot=100))]:
            curve,t,counts=portfolio(frames,hold=None,exit_sma=None,fade=cfg['fade'],max_age_signal=cfg['age'],
                exit_builder=lambda f:(f.Close>=f.Close.rolling(cfg['target']).mean()).to_numpy(bool),
                entry_builder=builder,cost_model=cost)
            assert t.entry_date.isin(allowed).all()
            r=t.net_return;w=r[r>0];l=r[r<0];years=(curve.index[-1]-curve.index[0]).days/365.25
            row=dict(variant=label,scenario=scenario,**cfg,n=len(t),wr=(r>0).mean(),avg_win=w.mean(),avg_loss=-l.mean(),
                payout=w.mean()/-l.mean(),mean_return=r.mean(),median_return=r.median(),mean_bars=t.bars.mean(),
                cagr=(curve.equity.iloc[-1]/1e9)**(1/years)-1,mdd=curve.drawdown.min(),
                money_pf=t.loc[t.pnl>0,'pnl'].sum()/-t.loc[t.pnl<0,'pnl'].sum(),**counts)
            rows.append(row)
            for start,end in [('2000','2015'),('2016','2020'),('2021','2025')]:
                # Lifetime returns grouped by entry date, not reset portfolio windows.
                g=t[(t.entry_date>=start+'-01-01')&(t.entry_date<=end+'-12-31')]
                period_rows.append(dict(variant=label,scenario=scenario,entry_period=f'{start}-{end}',n=len(g),wr=(g.net_return>0).mean(),mean_return=g.net_return.mean()))
            curve.to_csv(OUT/f'{scenario}_{label}_equity.csv');t.to_csv(OUT/f'{scenario}_{label}_trades.csv',index=False)
            pd.DataFrame(rows).to_csv(OUT/'comparison.csv',index=False)
            pd.DataFrame(period_rows).to_csv(OUT/'periods.csv',index=False)
            print(scenario,label,f'WR {row["wr"]:.2%}, avgwin {row["avg_win"]:.2%}, loss {row["avg_loss"]:.2%}, CAGR {row["cagr"]:.2%}, N {len(t)}',flush=True)
    result=pd.DataFrame(rows)
    for scenario in ['fees','spread']:
        base=result[(result.variant=='baseline')&(result.scenario==scenario)].iloc[0]
        mask=result.scenario==scenario
        result.loc[mask,'delta_wr']=result.loc[mask,'wr']-base.wr
        result.loc[mask,'delta_expectancy']=result.loc[mask,'mean_return']-base.mean_return
    result.to_csv(OUT/'comparison.csv',index=False)
    lines=['# Sideways WR levers: one factor at a time','',
        'User clarified acak means identify indicator levers, NOT random entry. The interrupted random-entry diagnostic is not used to select this experiment. All variants are standalone sideways systems, no main-module merge.', '',
        'Baseline: market proxy prior-bar sideways; individual stock ER20<0.30, Close>SMA200, Low touches/breaches previous20bar low and Close recovers above it, Close>previousClose. Entry next tradable Open, no stale untradable queue. Exit Close>=SMA10 recovery, currentOpen-Low>=1priorATR fading or age20, all next tradable Open. Terminal valuation retained.', '',
        'One factor changed at a time: stock ERthreshold0.1/0.2/0.4; supportlookback10/40; no extra rebound confirmation or Close>previousHigh; recovery SMA5/20; fade0.5/2ATR; age5/10. Market ER gate remains0.30 in all cases. Thresholds dimensionless or bars. Strict stock+market choppy entry, existing positions may exit after regime change.', '',
        '2000-2025Aug15 stocks, initialRp1billion, max10slots,10%prior-equity/cashcap compounding, deterministic alphabetical priority. Fee0.15%buy/0.25%sell. Spread stress counterfactual modern grid/100shares and1tick each side, not observed historical bid/ask. All results in-sample. Entry-date subgroup stats include whole trade lifespan; they are not independent reset validation. No claim of sevencriteria or performance across all regimes.', '',
        'WR changes describe the whole policy including changed trade composition and capacity; not matched-trade causal attribution. Higher WR may come with smaller wins/larger losses. Assess expectancy, payout and net CAGR jointly. Signal-prefix, market eligibility, cash/slot/PnL assertions checked. Active AFL unchanged.', '',
        '| Costs | Lever | Trades | WR | Delta WR pp | Avg win | Avg loss | Mean return | CAGR |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|']
    for r in result.itertuples():
        lines.append(f'| {r.scenario} | {r.variant} | {r.n} | {r.wr:.2%} | {100*r.delta_wr:+.2f} | {r.avg_win:.2%} | {r.avg_loss:.2%} | {r.mean_return:.2%} | {r.cagr:.2%} |')
    (OUT/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')


if __name__=='__main__':main()
