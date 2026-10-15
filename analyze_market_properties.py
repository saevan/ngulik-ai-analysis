"""Empirical properties of the Kompas100 data, measured per period (train/validation/test)."""
from pathlib import Path
import numpy as np
import pandas as pd
import grid_search_timehunter as engine
from backtest_breakout_er import efficiency_ratio

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'market_property_results'
PERIODS={'train':('2000-01-01','2015-12-31'),'validation':('2016-01-01','2020-12-31'),'test':('2021-01-01','2025-08-15')}

def per(series_or_frame,fn):
    return {k:fn(series_or_frame.loc[a:b]) for k,(a,b) in PERIODS.items()}

def main():
    OUT.mkdir(exist_ok=True)
    df,_=engine.load_data('stocks')
    piv=lambda c:df.pivot(index='Date/Time',columns='Ticker',values=c).sort_index()
    O,H,L,C,V=[piv(c) for c in ['Open','High','Low','Close','Volume']]
    T=piv('tradable').fillna(False).astype(bool)
    C=C.where(T);O=O.where(T)
    prevC=C.ffill().shift(1)
    ret=C/prevC-1;night=O/prevC-1;day=C/O-1
    ret=ret.where(ret.abs()<.5);night=night.where(night.abs()<.5);day=day.where(day.abs()<.5)
    rows=[]
    def add(name,fn):
        for k,v in fn.items():rows.append(dict(property=name,period=k,value=v))
    ew=ret.mean(axis=1)
    # 1 overnight vs intraday (equal-weight, mean daily, bps)
    add('overnight_mean_bps',per(night.mean(axis=1),lambda s:s.mean()*1e4))
    add('intraday_mean_bps',per(day.mean(axis=1),lambda s:s.mean()*1e4))
    add('close_close_mean_bps',per(ew,lambda s:s.mean()*1e4))
    # 2 autocorrelation
    add('index_ac1',per(ew,lambda s:s.autocorr(1)))
    add('index_ac5w',per(ew.rolling(5).sum()[::5],lambda s:s.autocorr(1)))
    add('stock_ac1_median',per(ret,lambda f:f.apply(lambda s:s.autocorr(1)).median()))
    # 3 cross-sectional momentum/reversal: quintile spread of next-H return (non-overlapping H)
    logp=np.log(C.ffill())
    for L_,skip,Hh in [(5,0,5),(20,0,20),(60,0,20),(120,20,20),(250,20,20)]:
        past=(logp.shift(skip)-logp.shift(skip+L_));fut=(logp.shift(-Hh)-logp)
        def spread(idx):
            vals=[]
            for d in idx[::Hh]:
                p=past.loc[d];f=fut.loc[d];m=p.notna()&f.notna()
                if m.sum()<30:continue
                q=p[m].rank(pct=True);vals.append(f[m][q>.8].mean()-f[m][q<=.2].mean())
            return np.mean(vals)*1e2 if vals else np.nan
        add(f'xs_mom_L{L_}_skip{skip}_H{Hh}_top_minus_bottom_pct',{k:spread(past.loc[a:b].index) for k,(a,b) in PERIODS.items()})
    # 4 breakout follow-through (HHV20 + ER>=.3), forward return from next Open
    hh=H.shift(1).rolling(20).max();er=C.ffill().apply(lambda s:efficiency_ratio(s,20))
    sig=(C>hh)&(er>=.3);entry=O.shift(-1)
    for Hh in [5,20]:
        fwd=C.ffill().shift(-Hh-1)/entry-1;allf=fwd.where(C.notna())
        add(f'breakout_fwd{Hh}_pct',per(fwd.where(sig).stack(),lambda s:s.mean()*1e2))
        add(f'all_fwd{Hh}_pct',per(allf.stack(),lambda s:s.mean()*1e2))
    # 5 gap behavior: after gap up >2%, intraday same day; and next-day close-close
    gapup=night>.02;gapdn=night<-.02
    add('intraday_after_gapup_bps',per(day.where(gapup).stack(),lambda s:s.mean()*1e4))
    add('intraday_after_gapdown_bps',per(day.where(gapdn).stack(),lambda s:s.mean()*1e4))
    # 6 calendar: day-of-week & turn-of-month (last trading day + first 3)
    dow=ew.groupby(ew.index.dayofweek)
    for d in range(5):add(f'dow{d}_bps',per(ew[ew.index.dayofweek==d],lambda s:s.mean()*1e4))
    m=pd.Series(ew.index.to_period('M'),index=ew.index);rank_fwd=m.groupby(m).cumcount();rank_back=m.groupby(m).cumcount(ascending=False)
    tom=(rank_fwd<3)|(rank_back==0)
    add('turn_of_month_bps',per(ew[tom],lambda s:s.mean()*1e4));add('rest_of_month_bps',per(ew[~tom],lambda s:s.mean()*1e4))
    # 7 low-vol vs high-vol stocks (60d vol quintile, next 20d)
    vol=ret.rolling(60).std();fut20=logp.shift(-20)-logp
    def volspread(idx):
        v=[]
        for d in idx[::20]:
            a=vol.loc[d];f=fut20.loc[d];mm=a.notna()&f.notna()
            if mm.sum()<30:continue
            q=a[mm].rank(pct=True);v.append(f[mm][q<=.2].mean()-f[mm][q>.8].mean())
        return np.mean(v)*1e2
    add('lowvol_minus_highvol_next20_pct',{k:volspread(vol.loc[a:b].index) for k,(a,b) in PERIODS.items()})
    # 8 breakout with volume surge vs without
    vs=V/V.shift(1).rolling(20).mean()
    fwd20=C.ffill().shift(-21)/entry-1
    add('breakout_volsurge2_fwd20_pct',per(fwd20.where(sig&(vs>=2)).stack(),lambda s:s.mean()*1e2))
    add('breakout_novolsurge_fwd20_pct',per(fwd20.where(sig&(vs<2)).stack(),lambda s:s.mean()*1e2))
    # 9 breakout strength: momentum 120d of breakout stocks top vs bottom half
    mom=logp.shift(20)-logp.shift(140)
    q=mom.rank(axis=1,pct=True)
    add('breakout_highmom_fwd20_pct',per(fwd20.where(sig&(q>.5)).stack(),lambda s:s.mean()*1e2))
    add('breakout_lowmom_fwd20_pct',per(fwd20.where(sig&(q<=.5)).stack(),lambda s:s.mean()*1e2))
    r=pd.DataFrame(rows).pivot(index='property',columns='period',values='value')[list(PERIODS)]
    r.to_csv(OUT/'properties.csv');pd.set_option('display.width',200);print(r.round(3).to_string())

if __name__=='__main__':main()
