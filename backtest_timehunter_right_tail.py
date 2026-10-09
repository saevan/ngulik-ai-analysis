"""Easy entry, long scheduled hold, loss-only current-bar-open fading."""
from itertools import product
from pathlib import Path
import json
import numpy as np
import pandas as pd
import grid_search_timehunter as engine

OUT = Path(__file__).resolve().parent / 'timehunter_right_tail_results'


def simulate(g, hold, dip, entry, mode='loss_only', loss_timeout=0, detail=False):
    n = len(g.o)
    records, returns = [], []
    cursor = 0
    while cursor < n:
        start = int(g.next_entry[entry][cursor])
        start = int(g.next_tradable[start]) if start < n else n
        if start >= n:
            break
        deadline = min(start + hold - 1, n - 1)
        end, price, at_open = deadline, g.c[deadline], False
        reason = 'time' if start + hold <= n else 'period_end'
        if reason == 'time' and not g.tradable[deadline]:
            fill = int(g.next_tradable[deadline])
            if fill < n:
                end, price, at_open, reason = fill, g.o[fill], True, 'time_delayed'
            else:
                end, price, reason = n-1, g.c[-1], 'period_end_mark'
        elif reason == 'period_end' and not g.tradable[deadline]:
            reason = 'period_end_mark'
        # Completed-bar decisions only, before the scheduled Close exit.
        bar = np.arange(start, deadline)
        losing = g.c[bar] < g.o[start]
        fade = np.zeros(len(bar), dtype=bool) if dip is None else g.low[bar] <= g.o[bar]*(1-dip)
        if mode == 'loss_only':
            fade &= losing
        stale = losing & (bar-start+1 >= loss_timeout) if loss_timeout else np.zeros(len(bar), dtype=bool)
        triggers = np.flatnonzero(fade | stale)
        if len(triggers):
            ix = triggers[0]
            fill = int(g.next_tradable[bar[ix]+1])
            if fill < n and fill <= end:
                end, price, at_open = fill, g.o[fill], True
                reason = 'loss_fading' if fade[ix] and mode == 'loss_only' else 'fading' if fade[ix] else 'loss_timeout'
        ret = price/g.o[start]-1
        returns.append(ret)
        if detail:
            highs = g.h[start:end] if at_open else g.h[start:end+1]
            lows = g.low[start:end] if at_open else g.low[start:end+1]
            mfe = max(g.o[start], price, float(highs.max()))/g.o[start]-1
            mae = min(g.o[start], price, float(lows.min()))/g.o[start]-1
            records.append(dict(ticker=g.ticker, entry_index=start, exit_index=end,
                entry_date=str(g.dates[start]), exit_date=str(g.dates[end]),
                entry_price=g.o[start], exit_price=price, gross_return=ret,
                reason=reason, bars=end-start+1, mfe=mfe, mae=mae,
                giveback=mfe-ret, exit_at_open=at_open))
        cursor = end+1
    return np.asarray(returns), records


def main():
    OUT.mkdir(exist_ok=True)
    df, _ = engine.load_data('stocks')
    groups = engine.prepare(df, dips=[.02,.05,.1])
    for g, (_, f) in zip(groups, df.groupby('Ticker', sort=True)):
        sig = (f.Close > f.Close.rolling(30).mean()).shift(1,fill_value=False).to_numpy(bool)
        n=len(sig)
        g.next_entry['sma30'] = np.minimum.accumulate(np.where(sig,np.arange(n),n)[::-1])[::-1]
    configs = [dict(entry=e,hold=h,dip=d,mode=mode,loss_timeout=t)
        for e,h,d in product(['always','sma30'],[200,400,800],[.02,.05,.1])
        for mode,t in [('loss_only',0),('loss_only',20),('unconditional',0)]]
    configs += [dict(entry=e,hold=h,dip=None,mode='unconditional',loss_timeout=0)
        for e,h in product(['always','sma30'],[200,400,800])]
    rows=[]
    for ix,cfg in enumerate(configs):
        chunks, records = [], []
        for g in groups:
            r,rec = simulate(g,**cfg,detail=True)
            chunks.append(r); records.extend(rec)
            if cfg['mode']=='unconditional':
                ref,_=engine.simulate_group(g,cfg['hold'],cfg['dip'],cfg['entry'])
                assert np.array_equal(r,ref), (g.ticker,cfg)
        r=np.concatenate(chunks); trades=pd.DataFrame(records)
        s=engine.metrics(r,0)
        s['pf']=float(r[r>0].sum()/-r[r<0].sum())
        s['skew']=float(pd.Series(r).skew())
        s['p95']=float(np.quantile(r,.95)); s['p99']=float(np.quantile(r,.99))
        s['avg_win_bars']=float(trades.loc[trades.gross_return>0,'bars'].mean())
        s['avg_loss_bars']=float(trades.loc[trades.gross_return<0,'bars'].mean())
        s['winner_turned_loss']=int(((trades.mfe>=.1)&(trades.gross_return<0)).sum())
        s['mean_giveback']=float(trades.giveback.mean())
        s['mean_giveback_winners']=float(trades.loc[trades.gross_return>0,'giveback'].mean())
        s['top1_profit_share']=float(np.sort(r)[-max(1,int(np.ceil(len(r)*.01))):].sum()/r[r>0].sum())
        rows.append(dict(config_id=ix,**cfg,**s))
        if cfg['entry']=='sma30' and cfg['hold']==400 and cfg['dip']==.05:
            trades.to_csv(OUT/f"sma30_H400_fade5_{cfg['mode']}_timeout{cfg['loss_timeout']}.csv",index=False)
        print(f"{ix+1}/{len(configs)} {cfg}: n={len(r)}, WR={s['wr']:.2%}, PF={s['pf']:.2f}, payout={s['payout']:.2f}, passes={s['numeric_passes']}",flush=True)
    grid=pd.DataFrame(rows)
    grid.to_csv(OUT/'grid.csv',index=False)
    (OUT/'summary.json').write_text(json.dumps(dict(configurations=len(grid),
        passes5=int((grid.numeric_passes==5).sum()),loss_only_passes5=int(((grid['mode']=='loss_only')&(grid.numeric_passes==5)).sum()),
        costs=0,loss_definition='completed Close < entry Open',fading_reference='current bar Open',
        chosen_example='Predeclared SMA30, H400, fade5%, loss-only, no timeout; not ranked winner'),indent=2),encoding='utf-8')
    lines=['# TimeHunter right-tail experiment',
        '1994-07-12 to 2025-08-15, 100 stocks, continuous, all costs zero. Easy entry: always or previous Close > SMA30. Long scheduled hold: 200/400/800 bars, counting entry bar. No profit target. Winner exits at scheduled Close; before that, loss-only fading requires BOTH Low <= current Open*(1-dip) AND completed Close < entry price. Execute next tradable Open. Loss flag does not change fading reference. Same-bar loss recovered by Close does not trigger. Pending exit is not canceled if next Open recovers.',
        'Optional loss timeout: after >=20 bars, if completed Close < entry, queue next tradable Open exit, even without fading. Baselines: unconditional fading with identical thresholds, and no fading. Period-end forced closures/marks follow existing engine. These are descriptive in-sample results, not independent validation or seven-criteria proof. Corporate actions and survivorship are unaudited.',
        'Mean is return per trade, not annual/portfolio return. PF uses equal entry notional. Right tail is described by skewness, payout and 95th/99th return percentiles; not WR alone. Trimmed mean removes the largest ceil(1%) returns. Giveback is peak intratrade return minus realized return, excluding High after an Open exit; not an achievable selling price. Winner-turned-loss counts trades reaching >=+10% intratrade but ending negative.',
        '| ID | Entry | Hold | Fade | Gate | Loss timeout | N | WR | PF | Payout | Mean | Median | P95 | P99 | Skew | Trimmed mean | Win bars | Loss bars | Numeric |',
        '|---:|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in grid.itertuples():
        lines.append(f'| {r.config_id} | {r.entry} | {r.hold} | {r.dip} | {r.mode} | {r.loss_timeout} | {r.n} | {r.wr:.2%} | {r.pf:.2f} | {r.payout:.2f} | {r.mean:.2%} | {r.median:.2%} | {r.p95:.2%} | {r.p99:.2%} | {r.skew:.2f} | {r.trimmed_mean:.2%} | {r.avg_win_bars:.1f} | {r.avg_loss_bars:.1f} | {r.numeric_passes}/5 |')
    (OUT/'REPORT.md').write_text('\n\n'.join(lines[:4])+'\n'+'\n'.join(lines[4:]),encoding='utf-8')


if __name__=='__main__':
    main()
