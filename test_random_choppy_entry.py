"""Random-entry diagnostic with a fixed causal ER gate and identical exits."""
from pathlib import Path
import json
import zlib
import numpy as np
import pandas as pd
import grid_search_timehunter as engine
from backtest_breakout_er import efficiency_ratio
from backtest_breakout_er_portfolio import portfolio
from backtest_idx_costs import Costs
from analyze_portfolio_regimes import regime_proxy, attribute
from search_standalone_sideways import make_entry

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'random_choppy_entry_results'


def gate(f,allowed):
    c=f.Close
    prior=((efficiency_ratio(c,20)<.3)&(c>c.rolling(200).mean())).shift(1,fill_value=False)
    return prior.to_numpy(bool)&f['Date/Time'].isin(allowed).to_numpy()&f.tradable.to_numpy(bool)


def main():
    OUT.mkdir(exist_ok=True)
    data,_=engine.load_data('stocks')
    proxy=regime_proxy(data);allowed=set(proxy.index[proxy.regime=='sideways'])
    frames={str(k):f.reset_index(drop=True) for k,f in data.groupby('Ticker',sort=True)}
    selected=make_entry(dict(family='channel_rebound'),allowed)
    eligible_count=signal_count=0
    for f in frames.values():
        history=(f['Date/Time']>='2000-01-01')&(f['Date/Time']<='2015-12-31')
        valid=gate(f,allowed)
        eligible_count+=int((valid&history.to_numpy()).sum())
        signal_count+=int((valid&history.to_numpy()&selected(f)).sum())
    probability=signal_count/eligible_count
    (OUT/'method.json').write_text(json.dumps(dict(seed_list=list(range(10)),probability=probability,
        train_eligible=eligible_count,train_signal=signal_count,evaluation_start='2021-01-01',evaluation_end='2025-08-15',
        gate='previous-bar stock ER20<0.30, Close>SMA200, previous-bar market proxy sideways',
        exits='Close>=SMA10 or currentOpen-Low>=priorATR or age20 -> next tradable Open'),indent=2),encoding='utf-8')
    rows=[]
    for kind,seed in [('signal',-1)]+[('random',i) for i in range(10)]:
        signals={}
        for ticker,f in frames.items():
            valid=gate(f,allowed)
            if kind=='signal':signal=selected(f)&valid
            else:
                rng=np.random.default_rng(np.random.SeedSequence([seed,zlib.crc32(ticker.encode())]))
                signal=(rng.random(len(f))<probability)&valid
            signals[ticker]=signal
            # Gate relies only on prior completed bars and fixed membership days.
            cut=len(f)//2
            np.testing.assert_array_equal(gate(f.iloc[:cut],allowed),valid[:cut])
        builder=lambda f:signals[str(f.Ticker.iloc[0])]
        for scenario,cost in [('fees',Costs()),('spread',Costs(grid=True,ticks_per_side=1,round_lot=100))]:
            curve,t,counts=portfolio(frames,hold=None,fade=1,exit_builder=lambda f:(f.Close>=f.Close.rolling(10).mean()).to_numpy(bool),
                max_age_signal=20,entry_builder=builder,start='2021-01-01',cost_model=cost)
            assert t.entry_date.isin(allowed).all()
            r=t.net_return;w=r[r>0];l=r[r<0]
            stats,_=attribute(curve,proxy,'stocks',kind)
            side=stats[stats.regime=='sideways'].iloc[0]
            years=(curve.index[-1]-curve.index[0]).days/365.25
            row=dict(kind=kind,seed=seed,scenario=scenario,n=len(t),wr=(r>0).mean(),avg_win=w.mean(),avg_loss=-l.mean(),
                mean_return=r.mean(),payout=w.mean()/-l.mean(),cagr=(curve.equity.iloc[-1]/1e9)**(1/years)-1,
                mdd=curve.drawdown.min(),sideways_annual=side.conditional_annualized,
                pf=t.loc[t.pnl>0,'pnl'].sum()/-t.loc[t.pnl<0,'pnl'].sum(),**counts)
            rows.append(row)
            label=f'{kind}_{seed}_{scenario}'
            curve.to_csv(OUT/f'{label}_equity.csv');t.to_csv(OUT/f'{label}_trades.csv',index=False)
            pd.DataFrame(rows).to_csv(OUT/'comparison.csv',index=False)
            print(label,f'WR{row["wr"]:.2%}, CAGR{row["cagr"]:.2%}, N{len(t)}',flush=True)
    summaries=[]
    result=pd.DataFrame(rows)
    for scenario,g in result[result.kind=='random'].groupby('scenario'):
        summaries.append(dict(scenario=scenario,wr_min=g.wr.min(),wr_median=g.wr.median(),wr_max=g.wr.max(),
            cagr_min=g.cagr.min(),cagr_median=g.cagr.median(),cagr_max=g.cagr.max(),positive_cagr_runs=int((g.cagr>0).sum()),
            mean_return_median=g.mean_return.median(),payout_median=g.payout.median()))
    pd.DataFrame(summaries).to_csv(OUT/'random_summary.csv',index=False)
    (OUT/'REPORT.md').write_text('''# Random-entry diagnostic under choppy ER

Evaluation2021-01-01 to2025-08-15, freshRp1billion, ten slots,10%prior-close equity cash-capped/compounding. Both signal and random entries require previous stock ER20<0.30 and Close>SMA200 plus previous-bar market proxy sideways. Tradable observation required, no queued untradable setup. Exits identical: recoveryClose>=SMA10, fading1priorATR from current Open, or age20; next tradable Open. Terminal valuations retained. Random is a diagnostic control, not an adopted strategy.

Signal is support20 rejection/risingClose from previous candidate with the new explicit individual ER gate. Random uses ten deterministic independent seed streams per ticker. Constant Bernoulli probability is calibrated ONLY on2000-2015 signal-count/eligible-stock-bar-count. Expected opportunity frequency matched, not exact executed trade counts or exact portfolio exposure. No best seed selected. Gate prefix causality, accounting and return attribution checked. This is an exploratory small Monte Carlo diagnostic, not a significance test or fresh out-of-sample validation;2021-2025 has already been examined in this research.

Fees0.15%buy/0.25%sell. Spread stress uses modern grid/100share lots plus1tick per side counterfactually on historical data, not actual historical bid/ask. Dataset survivorship/adjustment/liquidity limitations unchanged. Sideways annual equivalent is attribution of disjoint days, not independently tradable regime CAGR. WR must be assessed jointly with payoff/expectancy/costs. No main strategy/AFL change or claim of profitability across regimes.
''',encoding='utf-8')
    print(pd.DataFrame(summaries).to_string(index=False))


if __name__=='__main__':main()
