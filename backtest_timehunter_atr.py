"""ATR-normalized price thresholds; original execution and time rules."""
from pathlib import Path
from itertools import product
import argparse
import json
import numpy as np
import pandas as pd
import grid_search_timehunter as engine
from backtest_timehunter_cross_market import forex_daily

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'timehunter_atr_results'
DEFAULT_PULLBACK=1.0
DEFAULT_FADE=2.0


def atr_previous(frame, length=14):
    h,l,c=(frame[x].to_numpy(float) for x in ['High','Low','Close'])
    tr=h-l
    if len(c)>1:
        tr[1:]=np.maximum(tr[1:],np.maximum(abs(h[1:]-c[:-1]),abs(l[1:]-c[:-1])))
    atr=np.full(len(c),np.nan)
    if len(c)>=length:
        atr[length-1]=tr[:length].mean()
        for i in range(length,len(c)):
            atr[i]=(atr[i-1]*(length-1)+tr[i])/length
    return np.r_[np.nan,atr[:-1]] if len(c) else atr


def signals(frame, pullback, fade, length=14):
    a=atr_previous(frame,length)
    valid=np.isfinite(a)&(a>0)
    setup=(frame.Close>frame.Close.rolling(30).mean()) & (frame.Close>frame.Close.shift(1))
    setup &= valid & ((frame.High.rolling(20).max()-frame.Close)>=pullback*a)
    entry=setup.shift(1,fill_value=False).to_numpy(bool)
    fading=valid & ((frame.Open.to_numpy()-frame.Low.to_numpy())>=fade*a)
    return entry,fading


def main():
    global OUT
    parser=argparse.ArgumentParser()
    parser.add_argument('--start', help='Inclusive entry start YYYY-MM-DD; retain earlier indicator warmup')
    parser.add_argument('--default-only', action='store_true')
    parser.add_argument('--expanded-grid', action='store_true', help='Explore shared ATR coefficients without changing structure')
    args=parser.parse_args()
    if args.start:
        args.start=pd.Timestamp(args.start).strftime('%Y-%m-%d')
        OUT=ROOT/('timehunter_atr_since_'+args.start.replace('-','')+'_results')
    if args.expanded_grid:
        OUT=ROOT/('timehunter_atr_expanded_'+(args.start or 'full').replace('-','')+'_results')
    periods=[('since_start',args.start,None)] if args.start else [('full',None,None),('common','2023-07-01','2025-08-16')]
    settings=[(DEFAULT_PULLBACK,DEFAULT_FADE)] if args.default_only else list(product([.5,1.,2.],[1.,2.,3.,5.]))
    if args.expanded_grid:
        if args.default_only:
            parser.error('--expanded-grid and --default-only are incompatible')
        settings=list(product([.125,.25,.5,.75,1.,1.5,2.,3.,4.],[.5,.75,1.,1.5,2.,3.,4.,5.,8.,12.]))
    OUT.mkdir(exist_ok=True)
    stocks,_=engine.load_data('stocks'); fx,_=engine.load_data('forex')
    crypto=pd.concat([pd.read_csv(p,parse_dates=['Date/Time']) for p in sorted((ROOT/'Data'/'crypto_binance_daily').glob('*.csv'))],ignore_index=True)
    crypto['tradable']=crypto.Volume>0
    datasets={'stocks':stocks,'forex04':forex_daily(fx,4),'crypto':crypto,'forex00_sensitivity':forex_daily(fx,0)}
    rows=[]; coverage={}
    # Defaults declared before observing results; grid is sensitivity, no retuning.
    for market,frame in datasets.items():
        in_range=frame if not args.start else frame[frame['Date/Time']>=pd.Timestamp(args.start)]
        coverage[market]=dict(data_start=str(in_range['Date/Time'].min()),data_end=str(in_range['Date/Time'].max()),symbols=int(in_range.Ticker.nunique()))
        groups=engine.prepare(frame,dips=[])
        frames={str(k):f.reset_index(drop=True) for k,f in frame.groupby('Ticker',sort=True)}
        for pull,fade in settings:
            for g in groups:
                entry,trigger=signals(frames[g.ticker],pull,fade)
                n=len(entry); ix=np.arange(n)
                g.next_entry['atr']=np.minimum.accumulate(np.where(entry,ix,n)[::-1])[::-1]
                g.fade_exit[fade]=np.minimum.accumulate(np.where(trigger,ix+1,n)[::-1])[::-1]
            for period,start,stop in periods:
                records=[]; chunks=[]
                default=pull==DEFAULT_PULLBACK and fade==DEFAULT_FADE
                for g in groups:
                    r,rec=engine.simulate_group(g,200,fade,'atr',start=start,stop=stop,detail=default)
                    chunks.append(r); records.extend(rec)
                r=np.concatenate(chunks); s=engine.metrics(r,0)
                loss=-r[r<0].sum()
                s['pf']=float(r[r>0].sum()/loss) if loss else np.nan
                rows.append(dict(market=market,period=period,pullback_atr=pull,fade_atr=fade,**s))
                if default:
                    if args.start:
                        assert all(pd.Timestamp(x['entry_date'])>=pd.Timestamp(args.start) for x in records)
                    assert len(records)==len(r)
                    pd.DataFrame(records).to_csv(OUT/f'{market}_{period}_trades.csv',index=False)
            if args.expanded_grid and fade==settings[-1][1]:
                print(f'{market}: pullback {pull} complete',flush=True)
        print('Finished '+market,flush=True)
    grid=pd.DataFrame(rows); grid.to_csv(OUT/'sensitivity.csv',index=False)
    selected=grid[(grid.pullback_atr==DEFAULT_PULLBACK)&(grid.fade_atr==DEFAULT_FADE)]
    selected.to_csv(OUT/'default_comparison.csv',index=False)
    (OUT/'run_metadata.json').write_text(json.dumps(dict(requested_start=args.start,default_only=args.default_only,coverage=coverage,warmup='All available earlier bars; no carried positions at requested start',costs=0),indent=2),encoding='utf-8')
    lines=['# TimeHunter ATR normalization',
        'Defaults declared before testing: ATR14 Wilder, pullback1 ATR, fading2 ATR; SMA30, High20, rebound1, hold200 and all execution rules unchanged. All costs zero. These defaults are not optimized winners. Grid is sensitivity only.',
        'ATR seeding: TR[0]=High[0]-Low[0]; first ATR at index13 is mean of first14 TRs; subsequent Wilder recurrence. Both pullback and fading use ATR from previous completed bar. Entry condition evaluated at completed Close, entry next tradable Open. Fading anchor is each current Open, exit next tradable Open, regardless of position PnL. Invalid/zero ATR blocks both price-threshold signals.',
        'Same selected surviving crypto samples and forex-session limitations as timehunter_cross_market_results. Full histories differ; common period2023-07-01 through2025-08-15. No fee, leverage or portfolio sizing in return metrics. Mean is per trade. Normalization does not prove universal performance or seven criteria.',
        '| Market | Period | N | WR | PF | Payout | Mean | Median | Numerical |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|']
    for r in selected.itertuples():
        lines.append(f'| {r.market} | {r.period} | {r.n} | {r.wr:.2%} | {r.pf:.2f} | {r.payout:.2f} | {r.mean:.2%} | {r.median:.2%} | {r.numeric_passes}/5 |')
    if args.start:
        lines += ['\nRequested entry start: '+args.start+'. Positions start flat. Prior data only warms indicators. Missing historical data are not fabricated. No common-period run in this invocation.',json.dumps(coverage,indent=2)]
    (OUT/'REPORT.md').write_text('\n\n'.join(lines[:4])+'\n'+'\n'.join(lines[4:]),encoding='utf-8')
    print(selected[['market','period','n','wr','pf','payout','mean','numeric_passes']].to_string(index=False))


if __name__=='__main__': main()
