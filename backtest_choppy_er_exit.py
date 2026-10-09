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
OUT=ROOT/'choppy_er_exit_results'
CONFIGS=[('baseline',0),('market_er',0),('stock_er',0),('market_or_original',0)]
WINDOWS={'train':('2000-01-01','2015-12-31'),'validation':('2016-01-01','2020-12-31'),
         'test':('2021-01-01','2025-08-15'),'full':('2000-01-01','2025-08-15')}

def er_exit_builder(f,proxy,kind,original_exit):
    market=f['Date/Time'].map(proxy.er).ge(.3).to_numpy(bool)
    stock=efficiency_ratio(f.Close,20).ge(.3).to_numpy(bool)
    if kind=='market_er':return market
    if kind=='stock_er':return stock
    if kind=='market_or_original':return market|original_exit(f)
    return original_exit(f)


def main():
    OUT.mkdir(exist_ok=True)
    (OUT/'PLAN.json').write_text(json.dumps(dict(configs=CONFIGS,windows=WINDOWS,
        fixed_exit='Entry unchanged market-only choppy inverse. Replace exit with completed-bar market or stock ER>=.3; third option original OR marketER. All next tradable Open; no other stop.',
        selection='No tuning, four predetermined exit rules; identical entry conditions',
        validation='Full and chronological windows, previously examined data, not independent holdout.',main_unchanged=True),indent=2),encoding='utf-8')
    data,_=engine.load_data('stocks');proxy=regime_proxy(data)
    allowed=set(proxy.index[proxy.regime=='sideways'])
    frames_by_window={name:{str(k):f.reset_index(drop=True) for k,f in data[data['Date/Time']<=end].groupby('Ticker',sort=True)} for name,(_,end) in WINDOWS.items()}
    rows=[]
    def run(cfg,window,scenario):
        frames=frames_by_window[window];entry,old_exit=inverted_builders(('market',0),allowed)
        exit_signal=lambda f:er_exit_builder(f,proxy,cfg[0],old_exit)
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
        if cfg[0]=='baseline' and window=='full':
            old=pd.read_csv(ROOT/f'choppy_inverted_signal_results/full_{scenario}_market_0_equity.csv')
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
    for window in ['full','validation','test']:
        for scenario in ['fees','spread']:
            for cfg in CONFIGS:run(cfg,window,scenario)
    lines=['# Exit when ER no longer choppy','',
        'Entry identical to inverse market-only: previous completed original sell(Close<SMA30 OR fade2ATR), marketproxy laggedER20<.30, tradable nextOpen. No stop/time cap. Baseline exit breakout20+stockER>=.30; market_er replaces it with current completed MARKET ER>=.30; stock_er uses current completed STOCK ER>=.30; market_or_original retains old exit plus market exit. Exit signals at Close fill next tradable Open. ER is unsigned, so either up or down directional movement can trigger. State condition >=.30, not one-day cross; pending exits survive suspensions.', '',
        'Four fixed exit interpretations x two costs x three windows, no optimization. Full2000-2025 and fresh-start2016-2020/2021-2025. Same Rp1bn/10slots/compounding, buy.15%sell.25%. Spread stress modern IDX grid/100shares/1tick per side. Primary/AFL unchanged. Prefix causal entry/exit and original baseline equity regression checked. Market ER at signal Close is not lagged a second time; market regime entry label already lagged. Available stock observations determine when engine evaluates exits. Sideways equivalent is daily-regime attribution not standalone CAGR. Historical research, not independent validation.', '',
        '| Period | Cost | Lever | Value | Trades | WR | Avg loss | Avg win | CAGR | PF money | Records | Sideways equivalent |',
        '|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in pd.DataFrame(rows).itertuples():
        lines.append(f'|{r.window}|{r.scenario}|{r.lever}|{r.value}|{r.n}|{r.wr:.2%}|{r.avg_loss:.2%}|{r.avg_win:.2%}|{r.cagr:.2%}|{r.pf:.2f}|{r.records}/{r.months}|{r.sideways_annual:.2%}|')
    (OUT/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')

if __name__=='__main__':main()
