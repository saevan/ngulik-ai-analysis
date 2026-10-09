"""Signal opportunity timing within stock x contiguous market-choppy episodes."""
from pathlib import Path
import numpy as np
import pandas as pd
import grid_search_timehunter as engine
from analyze_portfolio_regimes import regime_proxy
from test_fading_entry_ablation import entry_arrays

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'choppy_fading_entry_test_results'

def main():
    data,_=engine.load_data('stocks');p=regime_proxy(data)
    allowed=set(p.index[p.regime=='sideways'])
    episodes=p.regime.ne(p.regime.shift()).cumsum()
    rows=[];extras=[];totals=dict(sma_opportunities=0,fade_opportunities=0,both=0,fade_only=0)
    for ticker,f in data.groupby('Ticker',sort=True):
        f=f.reset_index(drop=True);sma,fade=entry_arrays(f,allowed)
        for k,v in [('sma_opportunities',sma),('fade_opportunities',fade),('both',sma&fade),('fade_only',fade&~sma)]:totals[k]+=int(v.sum())
        e=f['Date/Time'].map(episodes)
        for i in np.flatnonzero(fade&~sma):extras.append((str(ticker),f['Date/Time'].iloc[i]))
        for ep,indices in f.loc[sma|fade].groupby(e[sma|fade]).groups.items():
            idx=np.asarray(list(indices));si=idx[sma[idx]];fi=idx[fade[idx]]
            first_s=int(si[0]) if len(si) else None;first_f=int(fi[0]) if len(fi) else None
            earlier=first_s is not None and first_f is not None and first_f<first_s
            rows.append(dict(ticker=ticker,episode=int(ep),has_sma=first_s is not None,has_fade=first_f is not None,
                fade_earlier=earlier,lead_stock_bars=first_s-first_f if earlier else 0,
                same_first=first_s is not None and first_s==first_f))
    d=pd.DataFrame(rows);d.to_csv(OUT/'signal_episode_timing.csv',index=False)
    extra=set(extras)
    t=pd.read_csv(OUT/'full_fees_combined_0_trades.csv',parse_dates=['entry_date'])
    only=t.apply(lambda r:(str(r.ticker),r.entry_date) in extra,axis=1)
    t.loc[only].to_csv(OUT/'actual_fading_only_entries.csv',index=False)
    totals.update(episodes_with_any_signal=len(d),episodes_with_both=int((d.has_sma&d.has_fade).sum()),
        fade_first_earlier=int(d.fade_earlier.sum()),same_first=int(d.same_first.sum()),
        only_fade_episode=int((d.has_fade&~d.has_sma).sum()),
        median_lead_bars=d.loc[d.fade_earlier,'lead_stock_bars'].median(),
        mean_lead_bars=d.loc[d.fade_earlier,'lead_stock_bars'].mean(),
        combined_actual_trades=len(t),actual_fade_only_entries=int(only.sum()))
    pd.DataFrame([totals]).to_csv(OUT/'timing_summary.csv',index=False)
    print(totals)

if __name__=='__main__':main()
