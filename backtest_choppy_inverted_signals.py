"""Invert raw primary signals under explicit choppy entry gates."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import grid_search_timehunter as engine
from backtest_timehunter_atr import atr_previous
from backtest_breakout_er import efficiency_ratio
from backtest_breakout_er_portfolio import portfolio
from backtest_idx_costs import Costs
from search_choppy_channel_system import builders
from analyze_portfolio_regimes import regime_proxy, attribute

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'choppy_inverted_signal_results'
CONFIGS=[('market',0),('market_stock',0),('market_stock_stop',0.5)]
WINDOWS={'train':('2000-01-01','2015-12-31'),'validation':('2016-01-01','2020-12-31'),
         'test':('2021-01-01','2025-08-15'),'full':('2000-01-01','2025-08-15')}

def inverted_builders(cfg,allowed):
    def signals(f):
        a=atr_previous(f);c=f.Close
        er=efficiency_ratio(c,20)
        original_sell=(c<c.rolling(30).mean())|((f.Open-f.Low)>=2*a)
        original_buy=(c>f.High.shift(1).rolling(20).max())&(er>=.3)
        setup=original_sell&(a>0)
        if cfg[0]!='market':setup=setup&(er<.3)
        entry=setup.fillna(False).shift(1,fill_value=False).to_numpy(bool)&f['Date/Time'].isin(allowed).to_numpy()&f.tradable.to_numpy(bool)
        return entry,original_buy.fillna(False).to_numpy(bool)
    return lambda f:signals(f)[0],lambda f:signals(f)[1]

def main():
    OUT.mkdir(exist_ok=True)
    (OUT/'PLAN.json').write_text(json.dumps(dict(configs=CONFIGS,windows=WINDOWS,
        fixed_exit='Pure inversion exits on original breakout20+stockER>=.3; optional stop.5 only separately labeled variant; no original fading sell retained',
        selection='No tuning, all three predetermined interpretations tested',
        validation='Full and chronological windows, previously examined data, not independent holdout.',main_unchanged=True),indent=2),encoding='utf-8')
    data,_=engine.load_data('stocks');proxy=regime_proxy(data)
    allowed=set(proxy.index[proxy.regime=='sideways'])
    frames_by_window={name:{str(k):f.reset_index(drop=True) for k,f in data[data['Date/Time']<=end].groupby('Ticker',sort=True)} for name,(_,end) in WINDOWS.items()}
    rows=[]
    def run(cfg,window,scenario):
        frames=frames_by_window[window];entry,exit_signal=inverted_builders(cfg,allowed)
        for f in frames.values():
            cut=len(f)//2
            np.testing.assert_array_equal(entry(f.iloc[:cut]),entry(f)[:cut])
            np.testing.assert_array_equal(exit_signal(f.iloc[:cut]),exit_signal(f)[:cut])
        costs=Costs() if scenario=='fees' else Costs(grid=True,ticks_per_side=1,round_lot=100)
        curve,t,counts=portfolio(frames,hold=None,fade=float("inf"),entry_builder=entry,
            exit_builder=exit_signal,
            entry_stop_atr=.5 if cfg[0]=="market_stock_stop" else None,cost_model=costs,start=WINDOWS[window][0])
        assert t.entry_date.isin(allowed).all()
        r=t.net_return;wins=r[r>0];loss=r[r<0]
        stats,_=attribute(curve,proxy,'stocks',scenario);side=stats[stats.regime=='sideways'].iloc[0]
        monthly=curve.new_high.groupby(curve.index.to_period('M')).any()
        row=dict(lever=cfg[0],value=cfg[1],window=window,scenario=scenario,n=len(t),wr=(r>0).mean(),
            avg_win=wins.mean(),avg_loss=-loss.mean(),payout=wins.mean()/-loss.mean(),mean_return=r.mean(),
            pf=t.loc[t.pnl>0,'pnl'].sum()/-t.loc[t.pnl<0,'pnl'].sum(),
            cagr=(curve.equity.iloc[-1]/1e9)**(365.25/(curve.index[-1]-curve.index[0]).days)-1,
            mdd=curve.drawdown.min(),records=int(monthly.sum()),months=len(monthly),mean_bars=t.bars.mean(),
            sideways_annual=side.conditional_annualized,sideways_records=side.months_record,sideways_months=side.months_present,
            sideways_cash=float((curve.cash/curve.equity)[proxy.regime.reindex(curve.index)=="sideways"].mean()))
        rows.append(row);label=f'{window}_{scenario}_{cfg[0]}_{cfg[1]}'
        curve.to_csv(OUT/f'{label}_equity.csv');t.to_csv(OUT/f'{label}_trades.csv',index=False)
        pd.DataFrame(rows).to_csv(OUT/'comparison.csv',index=False)
        print(label,f'N{len(t)} WR{row["wr"]:.2%} loss{row["avg_loss"]:.2%} CAGR{row["cagr"]:.2%} side{row["sideways_annual"]:.2%}',flush=True)
        return row
    for window in ['full','validation','test']:
        for scenario in ['fees','spread']:
            for cfg in CONFIGS:run(cfg,window,scenario)
    lines=['# Inverting primary raw signals during choppy regime','',
        'Source: research Breakout20+stockER20>=.30, exits Close<SMA30 or Open-Low>=2priorATR14. Not active pullback AFL. Invert underlying signal conditions, not historical executed trades. Long only: sell becomes buy, buy becomes sell. No additional range/cost or high-stockER entry selection. Entry on next tradable Open eligible market choppy dates. Market variant uses market proxy gate only; market_stock additionally requires stockER<.30 at signal. Both pure variants have no extra stop/hold/fading sell. market_stock_stop adds separately labeled .5entryATR Close stop. Exits are NOT gated by choppy; queues survive suspensions; entry requires a tradable execution bar; no stale entry queues.', '',
        'Three interpretations fixed before results; no optimized parameters. Full2000-2025 and fresh-start2016-2020/2021-2025. Earlier data examined, not independent validation. Rp1bn/10slots/compounding/buy.15%sell.25%; spread stress modern IDX grid/100shares/1tick eachside, not actual historical bidask. Prefix entry/exit and eligibility/accounting checks. Main unchanged. Sideways annual equivalent is daily regime attribution, not standalone CAGR. Monthly records use closing all-time equity peak since window start.', '',
        '| Period | Cost | Lever | Value | Trades | WR | Avg loss | Avg win | CAGR | PF money | Records | Sideways equivalent |',
        '|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in pd.DataFrame(rows).itertuples():
        lines.append(f'|{r.window}|{r.scenario}|{r.lever}|{r.value}|{r.n}|{r.wr:.2%}|{r.avg_loss:.2%}|{r.avg_win:.2%}|{r.cagr:.2%}|{r.pf:.2f}|{r.records}/{r.months}|{r.sideways_annual:.2%}|')
    (OUT/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')

if __name__=='__main__':main()
