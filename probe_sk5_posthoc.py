"""Post-hoc probes after the independent audit of the SK-5 regime study (labelled post-hoc: designed after seeing all windows).
Configs: SK-5 (HHV5, ER .3, fade2+SMA30, failed exit, 20%), SK-5 + entry only if the previous Close >= SMA30 (entry_sma), ER .2 + LLV5 trail
after +2 ATR (the combination that added record months in 18/18 cells), the same + entry_sma, and the WR>50% example
ch5_er0.4_sma30_trail2_fNone_s5. Each: train/validation/test/full x fee/s25; full fee with a <=25% ADV20 buy cap; full fee without the
20 tickers first listed in 2018 or later (survivorship sensitivity); ER20 regime attribution of the full fee run."""
from multiprocessing import Pool
from pathlib import Path
import numpy as np, pandas as pd
import grid_search_timehunter as engine
from backtest_stop_execution import run
from backtest_open_next import stats
from backtest_idx_costs import Costs
import search_swinger_like_system as S
from evaluate_swinger_like_finalists import PropCosts
from analyze_sk5_regimes import regimes
OUT=Path(__file__).resolve().parent/'sk5_regime_results'
COST={'fee':Costs(),'s25':PropCosts(slip=.0025)}
W={'train':('2000-01-01','2015-12-31'),'validation':('2016-01-01','2020-12-31'),'test':('2021-01-01','2025-08-15'),'full':('2000-01-01','2025-08-15')}
B=dict(entry_mode='buy_stop',strict_orders=True,presize=True,book_preopen=True,min_order_frac=1e-3,gap_skip=.02,gapdown_close=.02,priority=S.mom120,channel=5)
CF={'SK5':dict(er_min=.3,fade=2.,sma_len=30,failed_exit=0.,size_div=5),
    'SK5+entrySMA30':dict(er_min=.3,fade=2.,sma_len=30,failed_exit=0.,size_div=5,entry_sma=30),
    'ER.2+trail2':dict(er_min=.2,fade=2.,sma_len=30,trail_after=2.,failed_exit=0.,size_div=5),
    'ER.2+trail2+entrySMA30':dict(er_min=.2,fade=2.,sma_len=30,trail_after=2.,failed_exit=0.,size_div=5,entry_sma=30),
    'WR50_example(ER.4,SMA30+trail2,no failed)':dict(er_min=.4,fade=None,sma_len=30,trail_after=2.,failed_exit=None,size_div=5)}
G={}
def job(a):
    name,variant,w,cost=a;fr=G['fr']
    if variant=='no_post2018':fr={t:f for t,f in fr.items() if f['Date/Time'].min()<pd.Timestamp('2018-01-01')}
    fr={t:g for t,f in fr.items() if len(g:=f[f['Date/Time']<=W[w][1]])}
    kw=dict(B,**CF[name]);
    if variant=='adv25':kw['liq_cap']=.25
    with np.errstate(invalid='ignore',divide='ignore'):eq,tr=run(fr,cost_model=COST[cost],start=W[w][0],**kw)
    st=stats(eq,tr);row=dict(system=name,variant=variant,window=w,cost=cost,**st)
    if variant=='base' and w=='full' and cost=='fee':
        reg=G['reg']['er20'];r=eq.equity.pct_change().fillna(eq.equity.iloc[0]/1e9-1);lab=reg.regime.reindex(eq.index)
        days=eq.index.to_series().diff().dt.days.fillna(0)
        for s_ in ['uptrend','sideways','downtrend']:
            m=(lab==s_).to_numpy();row[f'cond_{s_}']=float(np.expm1(np.log1p(r[m]).sum()*365.25/days[m].sum()))
    return row
def main():
    st,_=engine.load_data('stocks');G['fr']={str(k):f.reset_index(drop=True) for k,f in st.groupby('Ticker',sort=True)};G['reg']=regimes(st)
    tasks=[(n,'base',w,c) for n in CF for w in W for c in COST]+[(n,v,'full','fee') for n in CF for v in ['adv25','no_post2018']]+[(n,'no_post2018','test','fee') for n in CF]
    with Pool(4) as p:rows=p.map(job,tasks,chunksize=1)
    d=pd.DataFrame(rows);d.to_csv(OUT/'posthoc_probes.csv',index=False)
    d['v']=d.apply(lambda r:f"{r.cagr*100:.1f}/{int(r.records)}/{r.mdd*100:.0f}",axis=1)
    pd.set_option('display.width',260,'display.max_columns',30)
    print(d.pivot_table(index='system',columns=['variant','cost','window'],values='v',aggfunc='first').to_string())
    f=d[(d.variant=='base')&(d.window=='full')&(d.cost=='fee')].set_index('system')
    print(f[['wr','payout','avg_loss','mean_bars','invested','n','cond_uptrend','cond_sideways','cond_downtrend']].round(3).to_string());print('done')
if __name__=='__main__':main()
