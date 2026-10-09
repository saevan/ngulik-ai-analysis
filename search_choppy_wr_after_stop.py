"""Entry-only levers with fixed 0.5 entry-ATR Close stop for secondary module."""
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
OUT=ROOT/'choppy_wr_after_stop_results'
CONFIGS=[('baseline',0),('sma',30),('sma',100),('stock_er',.3),('stock_er',.5),
         ('close_location',.75),('close_location',.9),('extension',.5),('extension',1),('cost',16)]
WINDOWS={'train':('2000-01-01','2015-12-31'),'validation':('2016-01-01','2020-12-31'),
         'test':('2021-01-01','2025-08-15'),'full':('2000-01-01','2025-08-15')}

def entry_builder(cfg,allowed):
    lever,value=cfg
    base,_=builders(dict(family='range_escape',length=10,cost_multiple=value if lever=='cost' else 8,stock_choppy=False),allowed)
    def entry(f):
        c=f.Close
        if lever=='sma': mask=c>c.rolling(int(value)).mean()
        elif lever=='stock_er':mask=efficiency_ratio(c,20)>=value
        elif lever=='close_location':mask=(c-f.Low)/(f.High-f.Low).replace(0,np.nan)>=value
        elif lever=='extension':mask=(c-f.High.shift(1).rolling(10).max())/atr_previous(f)<=value
        else:mask=pd.Series(True,index=f.index)
        return base(f)&mask.fillna(False).shift(1,fill_value=False).to_numpy(bool)
    return entry

def main():
    OUT.mkdir(exist_ok=True)
    (OUT/'PLAN.json').write_text(json.dumps(dict(configs=CONFIGS,windows=WINDOWS,
        fixed_exit='0.5 prior entry ATR Close stop, LLV10, fade2; all next tradable Open',
        selection='Train fees only: higher WR than baseline, avg loss <=110% baseline, >=100 trades, positive mean return/CAGR/sideways annual, PF>1.1. Highest WR, CAGR tie break. If none pass, highest WR with loss/count guard is diagnostic only.',
        validation='Frozen config vs same-stop baseline validation/test/full, fees and spread. Previously examined data, not pristine holdout.',main_unchanged=True),indent=2),encoding='utf-8')
    data,_=engine.load_data('stocks');proxy=regime_proxy(data)
    allowed=set(proxy.index[proxy.regime=='sideways'])
    frames_by_window={name:{str(k):f.reset_index(drop=True) for k,f in data[data['Date/Time']<=end].groupby('Ticker',sort=True)} for name,(_,end) in WINDOWS.items()}
    rows=[]
    def run(cfg,window,scenario):
        frames=frames_by_window[window];entry=entry_builder(cfg,allowed)
        for f in frames.values():
            cut=len(f)//2
            np.testing.assert_array_equal(entry(f.iloc[:cut]),entry(f)[:cut])
        costs=Costs() if scenario=='fees' else Costs(grid=True,ticks_per_side=1,round_lot=100)
        curve,t,counts=portfolio(frames,hold=None,fade=2,entry_builder=entry,
            exit_builder=lambda f:(f.Close<f.Low.shift(1).rolling(10).min()).to_numpy(bool),
            entry_stop_atr=.5,cost_model=costs,start=WINDOWS[window][0])
        assert t.entry_date.isin(allowed).all()
        if cfg[0]=='baseline' and window=='full':
            old=pd.read_csv(ROOT/'choppy_loss_mitigation_results'/f'{scenario}_low10_stop0.5_revFalse_equity.csv')
            np.testing.assert_allclose(curve.equity,old.equity,rtol=1e-10)
        r=t.net_return;wins=r[r>0];loss=r[r<0]
        stats,_=attribute(curve,proxy,'stocks',scenario);side=stats[stats.regime=='sideways'].iloc[0]
        monthly=curve.new_high.groupby(curve.index.to_period('M')).any()
        row=dict(lever=cfg[0],value=cfg[1],window=window,scenario=scenario,n=len(t),wr=(r>0).mean(),
            avg_win=wins.mean(),avg_loss=-loss.mean(),payout=wins.mean()/-loss.mean(),mean_return=r.mean(),
            pf=t.loc[t.pnl>0,'pnl'].sum()/-t.loc[t.pnl<0,'pnl'].sum(),
            cagr=(curve.equity.iloc[-1]/1e9)**(365.25/(curve.index[-1]-curve.index[0]).days)-1,
            mdd=curve.drawdown.min(),records=int(monthly.sum()),months=len(monthly),mean_bars=t.bars.mean(),
            sideways_annual=side.conditional_annualized,sideways_records=side.months_record,sideways_months=side.months_present)
        rows.append(row);label=f'{window}_{scenario}_{cfg[0]}_{cfg[1]}'
        curve.to_csv(OUT/f'{label}_equity.csv');t.to_csv(OUT/f'{label}_trades.csv',index=False)
        pd.DataFrame(rows).to_csv(OUT/'comparison.csv',index=False)
        print(label,f'N{len(t)} WR{row["wr"]:.2%} loss{row["avg_loss"]:.2%} CAGR{row["cagr"]:.2%} side{row["sideways_annual"]:.2%}',flush=True)
        return row
    for cfg in CONFIGS:run(cfg,'train','fees')
    base=rows[0]
    guarded=[r for r in rows[1:] if r['n']>=100 and r['avg_loss']<=1.1*base['avg_loss']]
    passed=[r for r in guarded if r['wr']>base['wr'] and r['cagr']>0 and r['mean_return']>0 and r['pf']>1.1 and r['sideways_annual']>0]
    chosen=max(passed or guarded or rows[1:],key=lambda r:(r['wr'],r['cagr']))
    frozen=(chosen['lever'],chosen['value'])
    (OUT/'FROZEN.json').write_text(json.dumps(dict(config=frozen,training_pass=bool(passed)),indent=2),encoding='utf-8')
    for window in ['validation','test','full']:
        for scenario in ['fees','spread']:
            for cfg in [CONFIGS[0],frozen]:run(cfg,window,scenario)
    lines=['# WR entry levers after fixed 0.5 ATR stop','',
        'Secondary Choppy Range Escape10 only; market proxy ER20<0.30. Primary/AFL unchanged. One entry lever at a time; original LLV10/fade2 exits plus fixed entry0.5ATR Close stop, next tradable Open. Stock ER minimum does not change market choppy eligibility. Filters use completed signal bar, one bar lag. Prefix checks and original full baseline equity regression passed.', '',
        'Rp1bn, ten slots,10%prior closing equity per new position cash capped, compounding. Buy0.15%/sell0.25%. Spread stress1tick eachside with modern IDX grid and100share lots; counterfactual, not historical quotes. Same selected universe/data limitations as original research.', '',
        'Ten training configurations2000-2015; frozen selection and baseline tested2016-2020,2021-2025 and full. Selection and pass status in PLAN/FROZEN.json. Adaptive research on previously seen history, not independent validation. Monthly record = any day with closing equity above all previous history/initial capital within each fresh-start test window. Sideways equivalent annualizes attributed returns on disjoint sideways dates; not a standalone portfolio CAGR.', '',
        '| Period | Cost | Lever | Value | Trades | WR | Avg loss | Avg win | CAGR | PF money | Records | Sideways equivalent |',
        '|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in pd.DataFrame(rows).itertuples():
        lines.append(f'|{r.window}|{r.scenario}|{r.lever}|{r.value}|{r.n}|{r.wr:.2%}|{r.avg_loss:.2%}|{r.avg_win:.2%}|{r.cagr:.2%}|{r.pf:.2f}|{r.records}/{r.months}|{r.sideways_annual:.2%}|')
    (OUT/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')

if __name__=='__main__':main()
