"""Frozen SMA30/HHV20/pullback2/rebound1/H200/fade30 across markets."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import grid_search_timehunter as engine
from backtest_timehunter_proportional import signal

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'timehunter_cross_market_results'


def forex_daily(frame, offset):
    frames=[]
    for ticker,f in frame.groupby('Ticker',sort=True):
        f=f.sort_values('Date/Time').copy()
        f['session']=(f['Date/Time']-pd.Timedelta(hours=offset)).dt.normalize()+pd.Timedelta(hours=offset)
        daily=f.groupby('session').agg(Open=('Open','first'),High=('High','max'),Low=('Low','min'),
            Close=('Close','last'),Volume=('Volume','sum'),hourly_bars=('Close','size')).reset_index()
        # Conservatively drop dataset-edge sessions, whose completeness is uncertain.
        daily=daily.iloc[1:-1].copy()
        daily['Date/Time']=daily['session'].dt.normalize()
        daily['Ticker']=ticker; daily['tradable']=True
        frames.append(daily)
    return pd.concat(frames,ignore_index=True)


def run():
    OUT.mkdir(exist_ok=True)
    stocks,_=engine.load_data('stocks')
    fx,_=engine.load_data('forex')
    crypto=pd.concat([pd.read_csv(f,parse_dates=['Date/Time']) for f in sorted((ROOT/'Data'/'crypto_binance_daily').glob('*.csv'))],ignore_index=True)
    px=crypto[['Open','High','Low','Close']].to_numpy(float)
    assert np.isfinite(px).all() and (px>0).all()
    assert not crypto.duplicated(['Ticker','Date/Time']).any()
    assert (crypto.High>=crypto[['Open','Close','Low']].max(axis=1)).all()
    assert (crypto.Low<=crypto[['Open','Close','High']].min(axis=1)).all()
    crypto['tradable']=crypto.Volume>0
    datasets={'stocks_daily':stocks,'forex_daily_04':forex_daily(fx,4),
              'crypto_daily_UTC':crypto,'forex_daily_00_sensitivity':forex_daily(fx,0)}
    rows=[]; ticker_rows=[]; diagnostics=[]; meta={}
    for market,frame in datasets.items():
        if market.startswith('forex'):
            frame.to_csv(OUT/f'{market}_bars.csv',index=False)
        groups=engine.prepare(frame,dips=[.3])
        frames={str(k):v.reset_index(drop=True) for k,v in frame.groupby('Ticker',sort=True)}
        meta[market]=dict(rows=len(frame),symbols=len(groups),start=str(frame['Date/Time'].min()),end=str(frame['Date/Time'].max()))
        for g in groups:
            f=frames[g.ticker]; sig=signal(f,30,20,.02); n=len(sig)
            g.next_entry['frozen']=np.minimum.accumulate(np.where(sig,np.arange(n),n)[::-1])[::-1]
            diagnostics.append(dict(market=market,ticker=g.ticker,bars=n,entry_signal_bars=int(sig.sum()),
                pullback_2pct_bars=int((1-f.Close/f.High.rolling(20).max()>=.02).sum()),
                fade_30pct_bars=int((f.Low<=f.Open*.7).sum())))
        for period,start,stop in [('full',None,None),('common','2023-07-01','2025-08-16')]:
            records=[]; chunks=[]
            for g in groups:
                r,rec=engine.simulate_group(g,200,.3,'frozen',start=start,stop=stop,detail=True)
                chunks.append(r); records.extend(rec)
                ticker_rows.append(dict(market=market,period=period,ticker=g.ticker,**engine.metrics(r,0)))
            r=np.concatenate(chunks); s=engine.metrics(r,0)
            loss=-r[r<0].sum()
            s['pf']=float(r[r>0].sum()/loss) if loss else None
            trades=pd.DataFrame(records)
            s['fading_exits']=sum(x['reason']=='fading' for x in records)
            s['end_closures']=sum(x['reason'].startswith('period_end') for x in records)
            nonterminal=np.array([x['gross_return'] for x in records if not x['reason'].startswith('period_end')])
            s['excluding_terminal_n']=len(nonterminal)
            s['excluding_terminal_mean']=float(nonterminal.mean()) if len(nonterminal) else None
            s['excluding_terminal_wr']=float((nonterminal>0).mean()) if len(nonterminal) else None
            rows.append(dict(market=market,period=period,**s))
            trades.to_csv(OUT/f'{market}_{period}_trades.csv',index=False)
    results=pd.DataFrame(rows)
    results.to_csv(OUT/'comparison.csv',index=False)
    pd.DataFrame(ticker_rows).to_csv(OUT/'per_symbol.csv',index=False)
    pd.DataFrame(diagnostics).to_csv(OUT/'signal_diagnostics.csv',index=False)
    stock=results[(results.market=='stocks_daily')&(results.period=='full')].iloc[0]
    assert stock.n==2181 and np.isclose(stock['mean'],.24068477997558366)
    (OUT/'methodology.json').write_text(json.dumps(dict(parameters=dict(sma=30,high_window=20,pullback=.02,rebound=1,hold=200,fade=.3),
        costs=0,retuning=False,datasets=meta,common_start='2023-07-01',common_stop_exclusive='2025-08-16',
        forex_volume='Zero is unavailable vendor volume, not trading halt; fills allowed.',
        forex_daily='04:00 source-clock sessions aligned to observed weekly start; unknown timezone. Midnight sensitivity included. First/last sessions removed.',
        crypto_source='https://api.binance.com/api/v3/klines',crypto_selection='Eight named surviving USDT pairs chosen before observing results; not entire crypto universe.'),indent=2),encoding='utf-8')
    lines=['# Frozen TimeHunter cross-market transfer',
        'SMA30 / High20 / pullback2% / rebound1 / hold200 / fade30%. Long-only, all costs zero, same execution engine, no optimization by market. Fading from current-bar Open; sell next tradable Open. Same bar count does not mean same calendar duration (crypto trades weekends).',
        'Forex source hourly CSV, source timezone unknown. Primary daily sessions start04:00 in source clock, based on observed Monday04:00–Saturday03:00 weekly coverage. Midnight-source-clock aggregation is included as sensitivity; do not label these UTC. Conservative first/last-session exclusion. No bars synthesized over missing sessions. Forex Volume=0 treated as unavailable metadata, not a trading halt. Crypto uses Binance spot daily UTC candles through2025-08-15.',
        'Full history differs between markets. Common comparison is2023-07-01–2025-08-15, with prior bars for indicator warmup and flat initial positions. Common-period windows were chosen before inspecting performance. Per-period end closures are reported and sensitivity excluding them is in comparison.csv.',
        'WR counts breakeven trades in denominator. Avg loss is positive magnitude. PF is sum positive returns / absolute sum negative returns, equal entry notional; mean is return per trade, not CAGR/portfolio. Universality is not established merely by implementing the same formula. Small cross-market samples, correlated assets, selected surviving crypto pairs, and unaudited stock corporate actions/survivorship limit inference.',
        '| Market | Period | N | WR | Mean | Median | Avg win | Avg loss | Payout | PF | Numeric | Fade exits | End closures |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in results.itertuples():
        lines.append(f'| {r.market} | {r.period} | {r.n} | {r.wr:.2%} | {r.mean:.2%} | {r.median:.2%} | {r.avg_win:.2%} | {r.avg_loss:.2%} | {r.payout:.2f} | {r.pf:.2f} | {r.numeric_passes}/5 | {r.fading_exits} | {r.end_closures} |')
    lines+=['\n## Data coverage',json.dumps(meta,indent=2),'\n## Official crypto data reference','https://github.com/binance/binance-spot-api-docs/blob/master/rest-api.md',
            '\nReproduce: python download_crypto_daily.py (network), then python backtest_timehunter_cross_market.py (local). Raw responses and hashes saved under Data/crypto_binance_daily.']
    (OUT/'REPORT.md').write_text('\n\n'.join(lines[:5])+'\n'+'\n'.join(lines[5:]),encoding='utf-8')
    print(results[['market','period','n','wr','mean','median','payout','pf','numeric_passes','fading_exits','end_closures']].to_string(index=False))
    print(json.dumps(meta,indent=2))


if __name__=='__main__': run()
