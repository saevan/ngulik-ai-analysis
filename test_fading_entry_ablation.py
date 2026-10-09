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
from backtest_choppy_inverted_signals import inverted_builders
from analyze_portfolio_regimes import regime_proxy, attribute

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'choppy_fading_entry_test_results'
CONFIGS=[('combined',0),('sma_only',0),('fade_only',0)]
WINDOWS={'train':('2000-01-01','2015-12-31'),'validation':('2016-01-01','2020-12-31'),
         'test':('2021-01-01','2025-08-15'),'full':('2000-01-01','2025-08-15')}

def entry_arrays(f,allowed):
    a=atr_previous(f);c=f.Close
    mask=f['Date/Time'].isin(allowed).to_numpy()&f.tradable.to_numpy(bool)
    sma=((c<c.rolling(30).mean())&(a>0)).shift(1,fill_value=False).to_numpy(bool)&mask
    fade=(((f.Open-f.Low)>=2*a)&(a>0)).shift(1,fill_value=False).to_numpy(bool)&mask
    return sma,fade

def make_entry(f,allowed,kind):
    sma,fade=entry_arrays(f,allowed)
    return sma|fade if kind=='combined' else sma if kind=='sma_only' else fade


def main():
    OUT.mkdir(exist_ok=True)
    (OUT/'PLAN.json').write_text(json.dumps(dict(configs=CONFIGS,windows=WINDOWS,
        fixed_exit='All entries share exit current Close market ER>=.3 -> next tradable Open; no other stop.',
        selection='No tuning: combined vs SMA only vs fading only; timing and performance ablation',
        validation='Full and chronological windows, previously examined data, not independent holdout.',main_unchanged=True),indent=2),encoding='utf-8')
    data,_=engine.load_data('stocks');proxy=regime_proxy(data)
    allowed=set(proxy.index[proxy.regime=='sideways'])
    frames_by_window={name:{str(k):f.reset_index(drop=True) for k,f in data[data['Date/Time']<=end].groupby('Ticker',sort=True)} for name,(_,end) in WINDOWS.items()}
    rows=[]
    def run(cfg,window,scenario):
        frames=frames_by_window[window];entry=lambda f:make_entry(f,allowed,cfg[0])
        exit_signal=lambda f:f['Date/Time'].map(proxy.er).ge(.3).to_numpy(bool)
        for f in frames.values():
            cut=len(f)//2
            np.testing.assert_array_equal(entry(f.iloc[:cut]),entry(f)[:cut])
            np.testing.assert_array_equal(exit_signal(f.iloc[:cut]),exit_signal(f)[:cut])
        costs=Costs() if scenario=='fees' else Costs(grid=True,ticks_per_side=1,round_lot=100)
        with np.errstate(invalid='ignore'):
            curve,t,counts=portfolio(frames,hold=None,fade=float("inf"),entry_builder=entry,
            exit_builder=exit_signal,
            entry_stop_atr=None,cost_model=costs,start=WINDOWS[window][0])
        assert t.entry_date.isin(allowed).all()
        if cfg[0]=='combined' and window=='full':
            old=pd.read_csv(ROOT/f'choppy_er_exit_results/full_{scenario}_market_er_0_equity.csv')
            np.testing.assert_allclose(curve.equity,old.equity,rtol=1e-10)
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
    for window in ['full']:
        for scenario in ['fees','spread']:
            for cfg in CONFIGS:run(cfg,window,scenario)
    lines=['# Does fading accelerate entry?','',
        'Secondary inverse experimental marketER exit held fixed. Combined Close<SMA30 OR currentOpen-Low>=2previousATR14, versus each component alone. Completed signal -> next tradable Open, same marketproxy ER20<.3 eligibility. Exit current completed marketER>=.3 nextOpen; no hold/stop. Six full-period runs, no parameter selection. Rp1bn/10slots/compounding,fee.15/.25%;spread modernIDXgrid100shares1tickeachside counterfactual. Combined baseline exact regression and causal prefix checks. All historical data already examined; primary/AFL unchanged. Sideways annual equivalent is regime attribution, not standalone CAGR.', '',
        '| Period | Cost | Lever | Value | Trades | WR | Avg loss | Avg win | CAGR | PF money | Records | Sideways equivalent |',
        '|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in pd.DataFrame(rows).itertuples():
        lines.append(f'|{r.window}|{r.scenario}|{r.lever}|{r.value}|{r.n}|{r.wr:.2%}|{r.avg_loss:.2%}|{r.avg_win:.2%}|{r.cagr:.2%}|{r.pf:.2f}|{r.records}/{r.months}|{r.sideways_annual:.2%}|')
    (OUT/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')

if __name__=='__main__':main()
