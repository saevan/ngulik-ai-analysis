"""Standalone long breakout module with ER filter and unchanged candidate exits."""
from pathlib import Path
import numpy as np
import pandas as pd
import grid_search_timehunter as engine
from backtest_timehunter_atr import atr_previous
from backtest_timehunter_cross_market import forex_daily
from analyze_candidate_equity import equity_curve, CAPITAL, NOTIONAL

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'breakout_er_results'


def efficiency_ratio(close, length=20):
    travel=close.diff().abs().rolling(length).sum()
    er=close.diff(length).abs()/travel.replace(0,np.nan)
    return er.mask(travel==0,0)


def entry_signal(frame, threshold=None):
    breakout=frame.Close>frame.High.shift(1).rolling(20).max()
    er=efficiency_ratio(frame.Close,20)
    setup=breakout if threshold is None else breakout & (er>=threshold)
    return setup.shift(1,fill_value=False).to_numpy(bool)


def main():
    OUT.mkdir(exist_ok=True)
    stocks,_=engine.load_data('stocks');fx,_=engine.load_data('forex')
    crypto=pd.concat([pd.read_csv(p,parse_dates=['Date/Time']) for p in sorted((ROOT/'Data'/'crypto_binance_daily').glob('*.csv'))],ignore_index=True)
    crypto['tradable']=crypto.Volume>0
    rows=[]
    for market,frame in {'stocks':stocks,'forex04':forex_daily(fx,4),'forex00':forex_daily(fx,0),'crypto':crypto}.items():
        groups=engine.prepare(frame,dips=[])
        frames={str(k):v.reset_index(drop=True) for k,v in frame.groupby('Ticker',sort=True)}
        for g in groups:
            f=frames[g.ticker];atr=atr_previous(f)
            trigger=np.isfinite(atr)&(atr>0)&((f.Open-f.Low).to_numpy()>=5*atr)
            n=len(f);ix=np.arange(n)
            g.fade_exit[5.]=np.minimum.accumulate(np.where(trigger,ix+1,n)[::-1])[::-1]
        for threshold in [None,.2,.3,.4,.5]:
            label='no_filter' if threshold is None else f'er_{threshold:.1f}'
            chunks=[];records=[];signal_count=0
            for g in groups:
                f=frames[g.ticker];entry=entry_signal(f,threshold);n=len(entry);ix=np.arange(n)
                signal_count+=int(entry[(f['Date/Time']>=pd.Timestamp('2000-01-01')).to_numpy()].sum())
                g.next_entry['breakout_er']=np.minimum.accumulate(np.where(entry,ix,n)[::-1])[::-1]
                r,rec=engine.simulate_group(g,200,5.,'breakout_er',start='2000-01-01',detail=True)
                chunks.append(r);records.extend(rec)
            r=np.concatenate(chunks);trades=pd.DataFrame(records)
            s=engine.metrics(r,0);loss=-r[r<0].sum()
            s['pf']=float(r[r>0].sum()/loss) if loss else np.nan
            curve=equity_curve(frame,trades)
            monthly=curve.groupby(curve.index.to_period('M')).agg(end_equity=('equity','last'),
                any_record=('new_high','any'),end_record=('new_high','last'))
            years=(curve.index[-1]-curve.index[0]).days/365.25
            s.update(cagr=(curve.equity.iloc[-1]/CAPITAL)**(1/years)-1,
                total_return=curve.equity.iloc[-1]/CAPITAL-1,max_drawdown=curve.drawdown.min(),
                months=len(monthly),record_months=int(monthly.any_record.sum()),record_month_fraction=monthly.any_record.mean(),
                end_record_month_fraction=monthly.end_record.mean(),interior_record_month_fraction=monthly.iloc[1:-1].any_record.mean(),
                initial_capital=CAPITAL,fixed_entry_notional=NOTIONAL,start=str(curve.index[0].date()),end=str(curve.index[-1].date()),
                signal_bars=signal_count,fade_exits=int((trades.reason=='fading').sum()),
                terminal_exits=int(trades.reason.str.startswith('period_end').sum()))
            rows.append(dict(market=market,variant=label,**s))
            trades.to_csv(OUT/f'{market}_{label}_trades.csv',index=False)
            curve.to_csv(OUT/f'{market}_{label}_equity.csv',index_label='date')
            monthly.to_csv(OUT/f'{market}_{label}_months.csv',index_label='month')
        print('Finished '+market,flush=True)
    result=pd.DataFrame(rows);result.to_csv(OUT/'comparison.csv',index=False)
    lines=['# Breakout + Kaufman ER module',
        'Long-only module tested separately: completed Close > highest High of the preceding20 bars (exclude signal bar), and ER20>=threshold. Default0.30 declared before results; no-filter control and0.20/0.40/0.50 sensitivities. ER=abs(Close-Close20barsAgo)/sum(abs(one-bar Close changes),20). Flat denominator =>0, warmup unavailable =>no filtered signal. ER measured per instrument, not an aggregate market index. No SMA/pullback entry filter added to this breakout module.',
        'Entry next tradable Open; original exit machinery unchanged: scheduled200th Close or Low<=current Open-5*previous ATR14, next tradable Open. No ER-based exit. Same hold/ATR/execution across variants. Prior history warms indicators; initial flat positions, entries>=2000 where data available. Gap/volume handling and period-end forced closure follow existing engine.',
        'Equity: initial1billion, fixed100thousand each buy, fractional units, no fees/slippage/leverage/cash yield. Most funds idle; this is previous AFL test-harness sizing, not a fully allocated portfolio. Daily marked-to-market equity; missing asset close carried forward. CAGR uses actual first-last data dates. Monthly record fraction means at least one daily closing equity record during the month; includes partial first/last months. End-record fraction also saved.',
        'Sample histories differ: stocks2000–2025, forex2023–2026, crypto2017–2025. Forex source timezone unknown;04:00 primary/00:00 sensitivity. Selected surviving crypto and unaudited stock corporate actions/survivorship remain limitations. This retrospective module test does not prove future chop avoidance or seven-criteria universality.',
        '| Market | Variant | N | WR | PF | CAGR | Record months | MDD |',
        '|---|---|---:|---:|---:|---:|---:|---:|']
    for r in result.itertuples():
        lines.append(f'| {r.market} | {r.variant} | {r.n} | {r.wr:.2%} | {r.pf:.2f} | {r.cagr:.6%} | {r.record_months}/{r.months} ({r.record_month_fraction:.2%}) | {r.max_drawdown:.4%} |')
    lines+=['\nER reference: https://doc.stocksharp.com/en/topics/api/indicators/list_of_indicators/kaufman_efficiency_ratio',
             '\nReproduce: python backtest_breakout_er.py. No main AFL modifications.']
    (OUT/'REPORT.md').write_text('\n\n'.join(lines[:5])+'\n'+'\n'.join(lines[5:]),encoding='utf-8')
    print(result[['market','variant','n','wr','pf','cagr','record_month_fraction','record_months','months','max_drawdown','signal_bars']].to_string(index=False))


if __name__=='__main__': main()
