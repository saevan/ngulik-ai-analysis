"""Joint-capital breakout + independent choppy mean-reversion experiment."""
from pathlib import Path
import numpy as np
import pandas as pd
import grid_search_timehunter as engine
from backtest_breakout_er_portfolio import portfolio
from backtest_idx_costs import Costs
from analyze_portfolio_regimes import regime_proxy, attribute

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'dual_system_results'


def main():
    OUT.mkdir(exist_ok=True)
    data,_=engine.load_data('stocks')
    frames={str(k):f.reset_index(drop=True) for k,f in data.groupby('Ticker',sort=True)}
    proxy=regime_proxy(data)
    rows=[];attributions=[];modules=[]
    def run(scenario,config,label,reverse=False):
        cost=Costs() if scenario=='fees' else Costs(grid=True,ticks_per_side=1,round_lot=100)
        curve,trades,counts=portfolio(frames,cost_model=cost,secondary=config,reverse=reverse)
        years=(curve.index[-1]-curve.index[0]).days/365.25
        r=trades.net_return
        name=f'{scenario}_{label}_reverse{reverse}'
        row=dict(name=name,scenario=scenario,label=label,reverse=reverse,
            dip=config['dip'] if config else 0,hold=config['hold'] if config else 0,
            range_slots=config['slots'] if config else 0,
            cagr=(curve.equity.iloc[-1]/1e9)**(1/years)-1,mdd=curve.drawdown.min(),
            records=int(curve.new_high.groupby(curve.index.to_period('M')).any().sum()),
            trades=len(trades),wr=(r>0).mean(),payout=r[r>0].mean()/-r[r<0].mean(),
            mean_return=r.mean(),median_return=r.median(),
            money_pf=trades.loc[trades.pnl>0,'pnl'].sum()/-trades.loc[trades.pnl<0,'pnl'].sum(),**counts)
        stats,_=attribute(curve,proxy,'stocks',name);attributions.append(stats)
        side=stats[stats.regime=='sideways'].iloc[0]
        row['sideways_annual_equivalent']=side.conditional_annualized
        row['sideways_records']=side.months_record
        for mod,g in trades.groupby('module'):
            modules.append(dict(name=name,module=mod,trades=len(g),pnl=g.pnl.sum(),
                wr=(g.net_return>0).mean(),mean_return=g.net_return.mean(),
                sideways_entries=int((g.entry_date.map(proxy.regime)=='sideways').sum())))
        if config is None and not reverse:
            base='fees_only' if scenario=='fees' else 'fees_1tick_each_side'
            old=pd.read_csv(ROOT/'breakout_er_idx_cost_results'/f'{base}_equity.csv')
            np.testing.assert_allclose(curve.equity,old.equity,rtol=1e-10)
        rows.append(row)
        curve.to_csv(OUT/f'{name}_equity.csv');trades.to_csv(OUT/f'{name}_trades.csv',index=False)
        pd.DataFrame(rows).to_csv(OUT/'comparison.csv',index=False)
        pd.DataFrame(modules).to_csv(OUT/'modules.csv',index=False)
        pd.concat(attributions).to_csv(OUT/'regimes.csv',index=False)
        print(name,f'CAGR {row["cagr"]:.2%}, records {row["records"]}/308, trades {len(trades)}',flush=True)
    for scenario in ['fees','spread']:
        run(scenario,None,'baseline')
        for dip in [.5,1.5]:
            for hold in [5,15]:
                for slots in [3,5]:
                    run(scenario,dict(dip=dip,hold=hold,slots=slots,reserved=True),f'd{dip}_h{hold}_slots{slots}')
    best=max((r for r in rows if r['scenario']=='spread' and r['label']!='baseline'),key=lambda r:r['cagr'])
    cfg=dict(dip=best['dip'],hold=best['hold'],slots=best['range_slots'],reserved=True)
    for scenario in ['fees','spread']:
        run(scenario,{**cfg,'reserved':False},'shared_slots')
        run(scenario,{**cfg,'slots':10},'range_only')
        run(scenario,None,'baseline',True)
        run(scenario,cfg,'selected',True)
    lines=['# Two independent systems, one cash-constrained portfolio','',
        'Primary: existing High20 breakout + ER20>=0.30, entry next tradable Open, hold200 Close or fade5 previous ATR14 then next tradable Open. No profit-trail extension.', '',
        'Secondary: individual-stock ER20<0.30 and Close <= SMA20 - dip*previous ATR14, dip0.5 or1.5. Entry next tradable Open. Independent exits: Close>=current SMA20; or Close<=actual entry price -2*ATR known before entry; or age>=5/15 bars. All secondary exit signals execute next tradable Open. Terminal Close/mark is the documented exception. Stop does not guarantee its price, suspension/gaps delay execution. No rebound requirement and no shorting.', '',
        'Reserved configurations cap primary/secondary positions at7/3 or5/5. Shared variant uses all ten slots with secondary cap retained; alphabetical cross-module ticker priority. One ticker can belong to only one module at a time; no same-bar reentry. Same account, no leverage, ten total positions, initialRp1billion, each new entry10% prior-close total equity capped by cash. Slot reservation is not a fixed capital split: existing winners drift and modules share available cash. No forced liquidation when regimes switch. Range-only has primary cap0 and ten range slots.', '',
        'Stocks2000-01-04 to2025-08-15. Buy0.15%,sell0.25%. Fees scenario no spread/fractional units. Spread stress uses current grid and100-share lots plus1tick per side counterfactually across history, not reconstructed historical bid/ask. Data universe, adjustments, survivorship, liquidity and fill-capacity limitations remain. Original AFL unchanged.', '',
        'Eight reserved configurations under both cost models; best selected by full-sample spread CAGR then tested shared, standalone and reverse-priority. These are in-sample sensitivity checks, not independent validation. Market sideways attribution uses prior-bar ER of equal-weight proxy, different from individual-stock entry gate; conditional annualized return concatenates disjoint days, not a separately executable CAGR. Records preserve whole-portfolio ATH. Do not sum module CAGRs. Module PnL is realized currency contribution in the shared account, not isolated strategy performance.', '',
        'Baseline regression reproduces saved curves; portfolio cash/slots/PnL checked on every run. Tests cover reservation and independent mean exit at next Open, plus previous portfolio/fee/trailing regressions.', '',
        '| Variant | CAGR | Record months | MDD | Trades | WR | Sideways annual equivalent |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for r in pd.DataFrame(rows).itertuples():
        lines.append(f'| {r.name} | {r.cagr:.2%} | {r.records}/308 | {r.mdd:.2%} | {r.trades} | {r.wr:.2%} | {r.sideways_annual_equivalent:.2%} |')
    (OUT/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')


if __name__=='__main__':main()
