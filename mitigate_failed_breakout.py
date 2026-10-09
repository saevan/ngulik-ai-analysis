"""Selective exit for early failure; original second-system entries unchanged."""
from pathlib import Path
import numpy as np
import pandas as pd
import grid_search_timehunter as engine
from backtest_breakout_er_portfolio import portfolio
from backtest_idx_costs import Costs
from search_choppy_channel_system import builders
from analyze_portfolio_regimes import regime_proxy,attribute

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'choppy_early_failure_results'


def main():
    OUT.mkdir(exist_ok=True)
    data,_=engine.load_data('stocks');proxy=regime_proxy(data)
    frames={str(k):f.reset_index(drop=True) for k,f in data.groupby('Ticker',sort=True)}
    allowed=set(proxy.index[proxy.regime=='sideways'])
    entry,exit_signal=builders(dict(family='range_escape',length=10,cost_multiple=8,stock_choppy=False),allowed)
    rows=[];matches=[]
    for window,confirm in [(0,0)]+[(w,c) for w in [3,5,10] for c in [1,2]]:
        for scenario,cost in [('fees',Costs()),('spread',Costs(grid=True,ticks_per_side=1,round_lot=100))]:
            curve,t,counts=portfolio(frames,hold=None,fade=2,entry_builder=entry,exit_builder=exit_signal,cost_model=cost,
                early_failure=(10,window,confirm) if window else None)
            if not window:
                old=pd.read_csv(ROOT/'choppy_channel_market_only_results'/f'full_{scenario}_range_escape_n10_c8_revFalse_equity.csv')
                np.testing.assert_allclose(curve.equity,old.equity,rtol=1e-10)
            base=pd.read_csv(ROOT/'choppy_channel_market_only_results'/f'full_{scenario}_range_escape_n10_c8_revFalse_trades.csv',parse_dates=['entry_date','exit_date'])
            m=base.merge(t,on=['ticker','entry_date'],suffixes=('_base','_new'))
            matches.append(dict(scenario=scenario,window=window,confirm=confirm,matched=len(m),
                original_winners=int((m.net_return_base>0).sum()),
                winners_to_losses=int(((m.net_return_base>0)&(m.net_return_new<0)).sum()),
                original_losers=int((m.net_return_base<0).sum()),
                losers_improved=int(((m.net_return_base<0)&(m.net_return_new>m.net_return_base)).sum())))
            assert t.entry_date.isin(allowed).all()
            r=t.net_return;w=r[r>0];l=r[r<0];years=(curve.index[-1]-curve.index[0]).days/365.25
            stats,_=attribute(curve,proxy,'stocks',scenario);side=stats[stats.regime=='sideways'].iloc[0]
            row=dict(scenario=scenario,window=window,confirm=confirm,n=len(t),wr=(r>0).mean(),avg_win=w.mean(),avg_loss=-l.mean(),
                cagr=(curve.equity.iloc[-1]/1e9)**(1/years)-1,mdd=curve.drawdown.min(),mean_return=r.mean(),
                records=int(curve.new_high.groupby(curve.index.to_period('M')).any().sum()),mean_bars=t.bars.mean(),
                sideways_annual=side.conditional_annualized,early_exits=int((t.reason=='early_breakout_failure').sum()),**counts)
            rows.append(row);label=f'{scenario}_w{window}_c{confirm}'
            curve.to_csv(OUT/f'{label}_equity.csv');t.to_csv(OUT/f'{label}_trades.csv',index=False)
            pd.DataFrame(rows).to_csv(OUT/'comparison.csv',index=False)
            pd.DataFrame(matches).to_csv(OUT/'matched_entries.csv',index=False)
            print(label,f'loss {row["avg_loss"]:.2%}, WR {row["wr"]:.2%}, CAGR {row["cagr"]:.2%}, side {row["sideways_annual"]:.2%}',flush=True)
    lines=['# Selective early-breakout-failure exit','',
        'Second system only: ChoppyRangeEscape10/cost8/marketER<0.30, no time cap, fade2ATR and original priorLLV10 exit retained. Additional exit: during first3/5/10holdingbars, Close below both actual entry price and ORIGINAL breakout level for1/2consecutivebars -> next tradable Open. Original level = HHV10 before entry signal bar, fixed at entry. Recovery resets consecutive count. Window expiry disables new early-failure signals but preserves already queued exits. No forced exit at window end. Long winners untouched by this additional rule unless they retrace below entry during probation.', '',
        'Same2000-2025 stocks, Rp1billion/10slots/prior-equity10%cashcap compounding. Fees0.15%buy/0.25%sell. Spread stress modern grid/100shares/1tick eachside counterfactual, not observed bidask. Active AFL and primary unchanged. Entries are unchanged setups but cash/slot path can alter realized trades. Market-onlychoppy gate, stock ER unrestricted as existing secondary.', '',
        '14runs baseline plus6variants under2costs. In-sample exploratory exit-only test, not independent validation. Same-entry diagnostics use ticker/date matches and final returns, for retrospective audit only; not a rule using future outcome. Do not equate matched-trade return differences to whole-portfolio CAGR attribution. Sideways annual equivalent is disjoint-day attribution, not standalone CAGR. No guarantee of loss ceiling at nextOpen. Baseline exact regression, eligibility, accounting and attribution checked.', '',
        '| Costs | Window | Consecutive closes | Avg loss | WR | CAGR | MDD | Records /308 | Sideways equivalent |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in pd.DataFrame(rows).itertuples():
        lines.append(f'| {r.scenario} | {r.window} | {r.confirm} | {r.avg_loss:.2%} | {r.wr:.2%} | {r.cagr:.2%} | {r.mdd:.2%} | {r.records} | {r.sideways_annual:.2%} |')
    (OUT/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')


if __name__=='__main__':main()
