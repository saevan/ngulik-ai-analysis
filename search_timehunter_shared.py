"""Research shared parameters; forex-session screen then stock/crypto transfer."""
from itertools import product
from pathlib import Path
import json
import numpy as np
import pandas as pd
import grid_search_timehunter as engine
from backtest_timehunter_atr import atr_previous
from backtest_timehunter_cross_market import forex_daily

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'timehunter_shared_search_results'
SMAS=[10,20,30,50,100]
HIGHS=[10,20,50]
HOLDS=[50,100,200,400]
PULLS=[.25,.5,1.,1.5,2.]
FADES=[1.,2.,3.,5.,8.]


def prepare(frame):
    groups=engine.prepare(frame,dips=[])
    for g,(_,f) in zip(groups,frame.groupby('Ticker',sort=True)):
        f=f.reset_index(drop=True); a=atr_previous(f,14); valid=np.isfinite(a)&(a>0)
        n=len(f);ix=np.arange(n)
        for sma,high,pull in product(SMAS,HIGHS,PULLS):
            setup=(f.Close>f.Close.rolling(sma).mean())&(f.Close>f.Close.shift(1))&valid&((f.High.rolling(high).max()-f.Close)>=pull*a)
            sig=setup.shift(1,fill_value=False).to_numpy(bool)
            g.next_entry[f'{sma}_{high}_{pull}']=np.minimum.accumulate(np.where(sig,ix,n)[::-1])[::-1]
        for fade in FADES:
            trigger=valid&((f.Open.to_numpy()-f.Low.to_numpy())>=fade*a)
            g.fade_exit[fade]=np.minimum.accumulate(np.where(trigger,ix+1,n)[::-1])[::-1]
    return groups


def evaluate(groups,cfg,start='2000-01-01',stop=None,detail=False):
    r=[];records=[]
    for g in groups:
        p,rec=engine.simulate_group(g,int(cfg['hold']),float(cfg['fade']),f"{int(cfg['sma'])}_{int(cfg['high'])}_{float(cfg['pull'])}",start=start,stop=stop,detail=detail)
        r.append(p);records.extend(rec)
    r=np.concatenate(r); s=engine.metrics(r,0)
    loss=-r[r<0].sum(); s['pf']=float(r[r>0].sum()/loss) if loss else np.nan
    return s,records


def main():
    OUT.mkdir(exist_ok=True)
    fx,_=engine.load_data('forex')
    markets={'forex04':prepare(forex_daily(fx,4)),'forex00':prepare(forex_daily(fx,0))}
    configs=[dict(sma=s,high=h,hold=t,pull=p,fade=f) for s,h,t,p,f in product(SMAS,HIGHS,HOLDS,PULLS,FADES)]
    rows=[]; survivors=[]
    for i,cfg in enumerate(configs):
        both=True
        for market in ['forex04','forex00']:
            s,_=evaluate(markets[market],cfg)
            rows.append(dict(config_id=i,market=market,**cfg,**s))
            both &= s['numeric_passes']==5
        if both: survivors.append((i,cfg))
    pd.DataFrame(rows).to_csv(OUT/'forex_screen.csv',index=False)
    print(f'{len(configs)} shared configurations; {len(survivors)} pass both forex session definitions',flush=True)
    stocks,_=engine.load_data('stocks')
    crypto=pd.concat([pd.read_csv(p,parse_dates=['Date/Time']) for p in sorted((ROOT/'Data'/'crypto_binance_daily').glob('*.csv'))],ignore_index=True)
    crypto['tradable']=crypto.Volume>0
    markets['stocks']=prepare(stocks); markets['crypto']=prepare(crypto)
    complete=[]
    for i,cfg in survivors:
        four=[]
        for market,groups in markets.items():
            s,_=evaluate(groups,cfg)
            four.append(dict(config_id=i,market=market,**cfg,**s))
        complete.extend(four)
    full=pd.DataFrame(complete)
    full.to_csv(OUT/'transfer_candidates.csv',index=False)
    if full.empty:
        print('No survivors; no candidate selected.',flush=True)
        return
    ranking=full.groupby('config_id').agg(min_passes=('numeric_passes','min'),min_n=('n','min'),min_margin=('margin','min'))
    ranking=ranking.sort_values(['min_passes','min_margin','min_n'],ascending=False)
    ranking.to_csv(OUT/'ranking.csv')
    winner_id=int(ranking.index[0]);cfg=configs[winner_id]
    summary=dict(searched=len(configs),both_forex_pass=len(survivors),all_four_pass=int((ranking.min_passes==5).sum()),selected_config_id=winner_id,selected_config=cfg,
        selection='Exploratory same-data screening, not out-of-sample. Rank minimum numeric passes, minimum WR/payout margin, minimum N. No 7/7 claim.',start='2000-01-01',costs=0)
    (OUT/'selected_research_candidate.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    results=[]
    for market,groups in markets.items():
        for label,start,stop in [('full','2000-01-01',None),('common','2023-07-01','2025-08-16')]:
            s,rec=evaluate(groups,cfg,start,stop,True)
            s['fading_exits']=sum(x['reason']=='fading' for x in rec)
            s['period_end_exits']=sum(x['reason'].startswith('period_end') for x in rec)
            results.append(dict(market=market,period=label,**s))
            pd.DataFrame(rec).to_csv(OUT/f'candidate_{market}_{label}_trades.csv',index=False)
    results=pd.DataFrame(results);results.to_csv(OUT/'candidate_comparison.csv',index=False)
    lines=['# Shared TimeHunter ATR parameter search',json.dumps(summary,indent=2),
        'Same architecture: Close>SMA, HHV-Close>=pull*previous ATR14, positive one-bar rebound; next tradable Open entry. Fading from each current Open by fade*previous ATR14; next tradable Open exit. Scheduled hold exit at Close; fees zero. All parameters identical across assets; no per-market optimization. Forex history only2023–2026, crypto2017–2025, stocks restricted2000–2025. Source-clock04:00 and00:00 forex sessions both screened.',
        'Screening and ranking use already-observed full samples. Session variants share data, not independent replications. Common-date evaluation is a diagnostic, not untouched holdout. Small trade counts, correlated instruments, surviving crypto selection, unaudited corporate actions and uncertain forex timezone limit universality. Mean per trade, not annual/portfolio return. PF uses equal entry notional.',
        results.to_string(index=False)]
    (OUT/'REPORT.md').write_text('\n\n'.join(lines),encoding='utf-8')
    print(json.dumps(summary),flush=True)
    print(results[['market','period','n','wr','pf','payout','mean','numeric_passes','fading_exits','period_end_exits']].to_string(index=False),flush=True)


if __name__=='__main__':main()
