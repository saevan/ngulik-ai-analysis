"""Which causal market conditions hurt Breakout+ER (buy stop and base) versus Swinger."""
from pathlib import Path
import numpy as np
import pandas as pd
import grid_search_timehunter as engine
from analyze_portfolio_regimes import regime_proxy

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'market_condition_results'
TRAIN_END='2015-12-31'

def conditions(data):
    """All features use closes up to the PREVIOUS bar (shift 1), so they are known before the day trades."""
    p=regime_proxy(data);idx=p.proxy
    closes=data.pivot(index='Date/Time',columns='Ticker',values='Close').sort_index()
    above=(closes>closes.rolling(50,min_periods=50).mean()).where(closes.rolling(50,min_periods=50).mean().notna())
    breadth=above.sum(axis=1)/above.notna().sum(axis=1).replace(0,np.nan)
    f=pd.DataFrame(index=idx.index)
    f['trend']=np.where(idx>idx.rolling(200).mean(),'bull','bear')
    f.loc[idx.rolling(200).mean().isna(),'trend']='unknown'
    f['er']=np.where(p.er>=.3,'lurus','choppy');f.loc[p.er.isna(),'er']='unknown'
    vol=p.proxy_return.rolling(20).std()*np.sqrt(250)
    q=vol[:TRAIN_END].quantile([1/3,2/3])  # thresholds fixed from train only
    f['vol']=np.where(vol<q.iloc[0],'low',np.where(vol<q.iloc[1],'mid','high'));f.loc[vol.isna(),'vol']='unknown'
    f['breadth']=np.where(breadth>=.6,'luas',np.where(breadth>=.4,'sedang','sempit'));f.loc[breadth.isna(),'breadth']='unknown'
    dd=idx/idx.cummax()-1
    f['dd']=np.where(dd>-.1,'dekat_puncak',np.where(dd>-.25,'koreksi','bear_dalam'))
    f['state']=f.trend+'_'+f.vol
    raw=dict(vol=vol,breadth=breadth,dd=dd,er=p.er)
    return f.shift(1).fillna('unknown'),pd.DataFrame(raw).shift(1),dict(vol_low=q.iloc[0],vol_high=q.iloc[1])

def main():
    OUT.mkdir(exist_ok=True)
    data,_=engine.load_data('stocks');cond,raw,thr=conditions(data)
    # Prefix causality: features on first half unchanged when future data appended.
    cut=cond.index[len(cond)//2];c2,_,_=conditions(data[data['Date/Time']<=cut])
    pd.testing.assert_frame_equal(c2[['trend','er','breadth','dd']],cond.loc[:cut,['trend','er','breadth','dd']])
    cond.to_csv(OUT/'conditions.csv',index_label='date')
    S='swinger_gap_results/';P='prototype_swinger_benchmark_results/'
    systems={'buystop_fees':S+'diag_full_fees_gnone_buy_stop_close_llv0','buystop_spread':S+'diag_full_spread_gnone_buy_stop_close_llv0',
        'base_fees':S+'full_fees_gnone_next_open_close_llv0','base_spread':S+'full_spread_gnone_next_open_close_llv0',
        'swinger_ideal':P+'afl_ideal_net','swinger_stop':P+'stop_order_net'}
    daily=[];trades=[]
    for name,path in systems.items():
        c=pd.read_csv(path+'_equity.csv',parse_dates=['date']).set_index('date').join(cond)
        c['lr']=np.log(c.equity/c.equity.shift(1).fillna(1e9));c['days']=c.index.to_series().diff().dt.days.fillna(1)
        c['invested']=c.market_value/c.equity
        for col in ['trend','er','vol','breadth','dd','state']:
            for k,g in c.groupby(col):
                daily.append(dict(system=name,feature=col,condition=k,time_share=g.days.sum()/c.days.sum(),
                    annual=np.expm1(g.lr.sum()*365.25/g.days.sum()),contribution=np.expm1(g.lr.sum()*365.25/c.days.sum()),
                    record_days=int(g.new_high.sum()),invested=g.invested.mean()))
        t=pd.read_csv(path+'_trades.csv',parse_dates=['entry_date']).join(cond,on='entry_date')
        t['system']=name;trades.append(t)
    d=pd.DataFrame(daily);d.to_csv(OUT/'daily_by_condition.csv',index=False)
    t=pd.concat(trades,ignore_index=True)
    rows=[]
    for col in ['trend','er','vol','breadth','dd','state']:
        for (s,k),g in t.groupby(['system',col]):
            r=g.net_return;rows.append(dict(system=s,feature=col,condition=k,n=len(g),wr=(r>0).mean(),avg_win=r[r>0].mean(),
                avg_loss=-r[r<0].mean(),expectancy=r.mean(),big_loss=(r<-.1).mean(),bars=g.bars.mean()))
    tr=pd.DataFrame(rows);tr.to_csv(OUT/'trades_by_entry_condition.csv',index=False)
    pd.Series(thr).to_csv(OUT/'vol_thresholds_train.csv')
    pd.set_option('display.width',250)
    piv=d.pivot_table(index=['feature','condition'],columns='system',values='annual').round(3)
    share=d[d.system=='buystop_fees'].set_index(['feature','condition']).time_share.round(3)
    print(piv.assign(time=share).to_string())
    print(tr[tr.system.isin(['buystop_spread','swinger_ideal'])].pivot_table(index=['feature','condition'],columns='system',values=['n','wr','expectancy','avg_loss']).round(3).to_string())

if __name__=='__main__':main()
