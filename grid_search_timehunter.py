"""Reproducible exploratory TimeHunter grid with chronological selection.

Entries use only the preceding completed bar. Fading resets at every new bar:
Low[t] <= Open[t]*(1-dip), regardless of the position's entry price or PnL.
The signal executes at next Open (gaps are not capped). The time
exit is pre-scheduled at the Hth Close. Reentry is earliest next bar after
execution, not on the same open. One position per ticker, long only.

Stock train <=2014; validation 2015-2019; locked test >=2020. These dates
were explored in earlier work, so the test is not genuinely unseen research.
Search train only; shortlist 20; choose one on validation before reading test
results. Final positions are liquidated on each period's last observed close.
Warmup indicators may use earlier periods, never later periods.

Five measured criteria: mean>median, avg win>avg loss, payout>2, WR>50%,
positive mean. Breakeven trades are not losses. Price-only applicability and
execution checks are reported separately, never hardcoded as two passes.
Active research mode: gross returns; all fees and modeled costs are zero.
Statistics pool trades; they are NOT compounded portfolio returns.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from itertools import product
import json
from pathlib import Path
import time

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'grid_timehunter_gross_results'
FADING_REFERENCE = 'current_bar_open'
HOLDS = [10, 20, 30, 50, 75, 100, 150, 200]
DIPS = [None, .02, .03, .05, .075, .10, .15, .20, .30]
SHORTLIST = 20
STOCK_COST = 0.0
FOREX_COST = 0.0


@dataclass
class Bars:
    ticker: str
    dates: np.ndarray
    o: np.ndarray
    h: np.ndarray
    low: np.ndarray
    c: np.ndarray
    signals: dict
    next_entry: dict
    fade_exit: dict
    tradable: np.ndarray
    next_tradable: np.ndarray


def load_data(kind):
    filename = 'Data kompas 100.csv' if kind == 'stocks' else 'Data Forex.csv'
    df = pd.read_csv(ROOT / 'Data' / filename)
    df.columns = df.columns.str.strip()
    required = ['Ticker', 'Date/Time', 'Open', 'High', 'Low', 'Close']
    if not set(required).issubset(df.columns):
        raise ValueError('Missing OHLC columns')
    df['Date/Time'] = pd.to_datetime(df['Date/Time'], format='mixed', dayfirst=kind == 'stocks')
    df = df.sort_values(['Ticker', 'Date/Time']).reset_index(drop=True)
    if kind == 'stocks':
        incomplete = df['Date/Time'] != df['Date/Time'].dt.normalize()
        print(f'Exclude {int(incomplete.sum())} stock bar(s) with non-daily timestamp.',flush=True)
        df = df.loc[~incomplete].reset_index(drop=True)
    px = df[['Open', 'High', 'Low', 'Close']].to_numpy(float)
    if not np.isfinite(px).all() or (px <= 0).any() or df['Date/Time'].isna().any():
        raise ValueError('Nonfinite/nonpositive data')
    if df.duplicated(['Ticker', 'Date/Time']).any():
        raise ValueError('Duplicate ticker timestamps')
    bad_high = df.High < df[['Open', 'Close']].max(axis=1)
    bad_low = df.Low > df[['Open', 'Close']].min(axis=1)
    # Match prior backtests, document corrections, and preserve source files.
    anomalies = df.loc[bad_high | bad_low, required].copy()
    df['High'] = px.max(axis=1)
    df['Low'] = px.min(axis=1)
    df['tradable'] = (df.Volume > 0) if kind == 'stocks' else True
    return df, anomalies


def entry_signals(df):
    c, h = df.Close, df.High
    conditions = {'always': pd.Series(True, index=df.index)}
    for length in [20, 50, 100, 200]:
        conditions[f'trend_{length}'] = c > c.rolling(length).mean()
    for length in [20, 50]:
        drawdown = 1 - c / h.rolling(length).max()
        for depth in [.02, .05, .10, .15]:
            conditions[f'dip_{length}_{int(depth*100)}'] = drawdown >= depth
    drawdown = 1 - c / h.rolling(20).max()
    for length in [100, 200]:
        trend = c > c.rolling(length).mean()
        for depth in [.02, .05, .10]:
            conditions[f'trend_{length}_dip_{int(depth*100)}'] = trend & (drawdown >= depth)
        for depth in [.02, .05]:
            conditions[f'trend_{length}_rebound_{int(depth*100)}'] = (
                trend & (drawdown >= depth) & (c > c.shift(1)))
    for length in [20, 50]:
        conditions[f'breakout_{length}'] = c > h.shift(1).rolling(length).max()
    # All information for an entry at Open[t] comes from bars <= t-1.
    signals = {name: condition.shift(1, fill_value=False).to_numpy(bool)
               for name, condition in conditions.items()}
    signals['always'] = np.ones(len(df),dtype=bool)
    return signals


def prepare(df, dips=DIPS):
    groups = []
    for ticker, frame in df.groupby('Ticker', sort=True):
        frame = frame.reset_index(drop=True)
        o, h, low, c = (frame[k].to_numpy(float) for k in ['Open', 'High', 'Low', 'Close'])
        n = len(frame)
        signals = entry_signals(frame)
        tradable = frame['tradable'].to_numpy(bool) if 'tradable' in frame else np.ones(n,dtype=bool)
        next_tradable = np.minimum.accumulate(np.where(tradable,np.arange(n),n)[::-1])[::-1]
        next_entry = {name: np.minimum.accumulate(np.where(sig, np.arange(n), n)[::-1])[::-1]
                      for name, sig in signals.items()}
        exits = {}
        # The trigger belongs to a bar, not a position: its reference resets
        # to that bar's Open even when the position is profitable. Find the
        # first following signal for each entry; deadline is applied later.
        for dip in dips:
            if dip is None:
                continue
            triggered = low <= o * (1 - dip)
            first_exit = np.where(triggered, np.arange(n) + 1, n)
            exits[dip] = np.minimum.accumulate(first_exit[::-1])[::-1]
        groups.append(Bars(str(ticker), frame['Date/Time'].to_numpy(), o, h, low, c,
                           signals, next_entry, exits,tradable,next_tradable))
    return groups


def simulate_group(g, hold, dip, entry_name, start=None, stop=None, detail=False):
    left = 0 if start is None else int(np.searchsorted(g.dates, np.datetime64(start)))
    right = len(g.o) if stop is None else int(np.searchsorted(g.dates, np.datetime64(stop)))
    pnl, records = [], []
    if left >= right:
        return np.array(pnl), records
    next_valid = g.next_entry[entry_name]
    fade = None if dip is None else g.fade_exit[dip]
    entry = int(next_valid[left])
    entry = int(g.next_tradable[entry]) if entry < right else right
    while entry < right:
        deadline = min(entry + hold - 1, right - 1)
        end = deadline
        price = g.c[end]
        reason = 'time' if entry + hold <= right else 'period_end'
        exit_at_open = False
        if reason == 'time' and not g.tradable[deadline]:
            fill = int(g.next_tradable[deadline])
            if fill < right:
                end,price,reason,exit_at_open = fill,g.o[fill],'time_delayed',True
            else:
                end,price,reason = right-1,g.c[right-1],'period_end_mark'
        elif reason == 'period_end' and not g.tradable[deadline]:
            reason = 'period_end_mark'
        if fade is not None and fade[entry] <= deadline:
            fill = int(g.next_tradable[fade[entry]])
            if fill < right and fill <= end:
                end,price,reason,exit_at_open = fill,g.o[fill],'fading',True
        ret = price / g.o[entry] - 1
        pnl.append(ret)
        if detail:
            past_lows = g.low[entry:end] if exit_at_open else g.low[entry:end+1]
            adverse = min(g.o[entry], price, float(past_lows.min())) / g.o[entry] - 1
            records.append(dict(ticker=g.ticker, entry_index=entry, exit_index=end,
                                entry_date=str(g.dates[entry]), exit_date=str(g.dates[end]),
                                entry_price=g.o[entry], exit_price=price,
                                reason=reason, gross_return=ret,
                                exit_at_open=exit_at_open,
                                bars=end-entry+1, adverse_excursion=adverse))
        entry = int(next_valid[end+1]) if end+1 < right else right
        entry = int(g.next_tradable[entry]) if entry < right else right
    return np.asarray(pnl), records


def metrics(gross, cost):
    # Keep zero-cost scoring exactly equal to raw returns, including zeros.
    pnl = np.asarray(gross, dtype=float).copy() if cost == 0 else (1 + gross) * (1 - cost) / (1 + cost) - 1
    if not len(pnl):
        return dict(n=0, wr=0., avg_win=0., avg_loss=0., payout=0., mean=0., median=0.,
                    numeric_passes=0, margin=-1., worst=0., p05=0., trimmed_mean=0.)
    wins, losses = pnl[pnl > 0], pnl[pnl < 0]
    avg_win = float(wins.mean()) if len(wins) else 0.
    avg_loss = float(-losses.mean()) if len(losses) else 0.
    payout = avg_win / avg_loss if avg_loss else (float('inf') if len(wins) else 0.)
    mean, median, wr = float(pnl.mean()), float(np.median(pnl)), float((pnl > 0).mean())
    checks = [mean > median, avg_win > avg_loss, payout > 2, wr > .5, mean > 0]
    margin = min(wr / .5 - 1, payout / 2 - 1)
    # Outlier diagnostic only, not an additional user criterion.
    trimmed = np.sort(pnl)[:max(1, len(pnl)-int(np.ceil(.01*len(pnl))))]
    return dict(n=len(pnl), wr=wr, avg_win=avg_win, avg_loss=avg_loss,
                payout=payout, mean=mean, median=median, numeric_passes=sum(checks),
                margin=margin, worst=float(pnl.min()), p05=float(np.quantile(pnl,.05)),
                trimmed_mean=float(trimmed.mean()))


def evaluate(groups, config, start=None, stop=None, cost=STOCK_COST, detail=False):
    chunks, records = [], []
    tickers = 0
    for g in groups:
        p, rec = simulate_group(g, **config, start=start, stop=stop, detail=detail)
        if len(p):
            chunks.append(p)
            tickers += 1
        records.extend(rec)
    gross = np.concatenate(chunks) if chunks else np.array([])
    net_summary = metrics(gross, cost)
    net_summary['tickers'] = tickers
    net_summary['gross'] = metrics(gross, 0)
    return net_summary, records


def config_of(row):
    return dict(hold=int(row['hold']), dip=None if pd.isna(row['dip']) else float(row['dip']),
                entry_name=row['entry_name'])


def rank(frame, prefix):
    return frame.sort_values([prefix+'numeric_passes', prefix+'margin', prefix+'trimmed_mean', prefix+'n'],
                             ascending=False, kind='stable')


def tests():
    d = pd.DataFrame({'Ticker':['X']*5, 'Date/Time':pd.date_range('2000-01-01',periods=5),
                      'Open':[100,100,80,90,95], 'High':[101,101,85,96,100],
                      'Low':[99,94,70,88,94], 'Close':[100,96,75,95,99]})
    g = prepare(d)[0]
    p, rec = simulate_group(g,5,.05,'always',detail=True)
    assert np.isclose(p[0],-.20) and rec[0]['exit_index']==2
    assert np.isclose(rec[0]['adverse_excursion'],-.20)
    assert rec[1]['entry_index']==3
    assert rec[1]['reason']=='period_end'
    p,_ = simulate_group(g,5,None,'always')
    assert len(p)==1 and np.isclose(p[0],-.01)
    # Signal on final scheduled day does not schedule an extra-day exit.
    p,rec = simulate_group(g,2,.05,'always',detail=True)
    assert rec[0]['exit_index']==1 and rec[0]['reason']=='time'
    p,_ = simulate_group(g,5,.05,'always',stop='2000-01-03')
    assert len(p)==1 and np.isclose(p[0],-.04)
    assert metrics(np.array([0., .1, -.1]),0)['wr']==1/3
    return 'PASS: gaps, exact deadline, next entry, period boundary, excursion and scoring'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--checks-only', action='store_true')
    args = parser.parse_args()
    checks = tests()
    print(checks,flush=True)
    if args.checks_only:
        return
    OUT.mkdir(exist_ok=True)
    started=time.monotonic()
    stocks, anomalies = load_data('stocks')
    anomalies.to_csv(OUT/'stock_ohlc_anomalies.csv',index=False)
    metadata = dict(stock_rows=len(stocks), stock_tickers=int(stocks.Ticker.nunique()),
                    stock_start=str(stocks['Date/Time'].min()), stock_end=str(stocks['Date/Time'].max()),
                    normalized_bars=len(anomalies), hold_grid=HOLDS, dip_grid=DIPS,
                    fading_reference=FADING_REFERENCE,
                    fading_formula='Low[t] <= Open[t] * (1 - dip)',
                    definition_correction='Previous entry-open fading results do not test the user-defined strategy.',
                    stock_cost_per_side=STOCK_COST, forex_cost_per_side=FOREX_COST,
                    result_basis='gross', cost_model='none',
                    fees=0.0, tax=0.0, spread_adjustment=0.0, slippage_adjustment=0.0,
                    selection='train <=2014; top20 -> validation 2015-2019; lock one -> test >=2020',
                    test_previously_explored=True, execution_checks=checks)
    print('Preparing stock indicators and causal exit lookup...',flush=True)
    groups=prepare(stocks)
    names=list(groups[0].signals)
    metadata['entry_grid']=names
    configs=[dict(hold=h,dip=d,entry_name=e) for h,d,e in product(HOLDS,DIPS,names)]
    metadata['configurations']=len(configs)
    (OUT/'methodology.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    print(f'TRAIN SEARCH: {len(configs)} configurations.',flush=True)
    rows=[]
    for index, config in enumerate(configs):
        s,_=evaluate(groups,config,stop='2015-01-01')
        row=dict(config_id=index,**config)
        row.update({'train_'+k:v for k,v in s.items() if k!='gross'})
        row.update({'train_gross_'+k:v for k,v in s['gross'].items()})
        rows.append(row)
        if (index+1)%100==0:
            print(f'{index+1}/{len(configs)}; elapsed={time.monotonic()-started:.1f}s',flush=True)
    train=pd.DataFrame(rows)
    train.to_csv(OUT/'train_grid.csv',index=False)
    eligible=train[(train.train_n>=200)&(train.train_tickers>=20)]
    if eligible.empty:
        raise RuntimeError('No sufficiently sampled configurations')
    shortlist=rank(eligible,'train_').head(SHORTLIST).copy()
    validation=[]
    for _, row in shortlist.iterrows():
        s,_=evaluate(groups,config_of(row),start='2015-01-01',stop='2020-01-01')
        item=row.to_dict()
        item.update({'validation_'+k:v for k,v in s.items() if k!='gross'})
        item.update({'validation_gross_'+k:v for k,v in s['gross'].items()})
        validation.append(item)
    validation=pd.DataFrame(validation)
    validation.to_csv(OUT/'validation_shortlist.csv',index=False)
    eligible_val=validation[(validation.validation_n>=100)&(validation.validation_tickers>=20)]
    if eligible_val.empty:
        raise RuntimeError('No validation candidate meeting sample thresholds')
    selected=rank(eligible_val,'validation_').iloc[0]
    config=config_of(selected)
    # Persist the final choice BEFORE testing; never replace after viewing test.
    (OUT/'locked_candidate.json').write_text(json.dumps(config,indent=2),encoding='utf-8')
    print('LOCKED CANDIDATE: '+json.dumps(config),flush=True)
    results={'fading_reference': FADING_REFERENCE, 'result_basis': 'gross',
             'cost_model': 'none', 'stock_cost_per_side': STOCK_COST,
             'forex_cost_per_side': FOREX_COST}
    for label,start,stop in [('train',None,'2015-01-01'),('validation','2015-01-01','2020-01-01'),
                             ('test','2020-01-01',None),('all',None,None)]:
        s,rec=evaluate(groups,config,start=start,stop=stop,detail=True)
        trades=pd.DataFrame(rec)
        trades['net_return']=(1+trades.gross_return)*(1-STOCK_COST)/(1+STOCK_COST)-1
        trades.to_csv(OUT/f'candidate_{label}_trades.csv',index=False)
        s['period_end_trades']=int(trades.reason.str.startswith('period_end').sum())
        s['unfilled_end_marks']=int((trades.reason=='period_end_mark').sum())
        s['mean_adverse_excursion']=float(trades.adverse_excursion.mean())
        s['worst_adverse_excursion']=float(trades.adverse_excursion.min())
        results[label]=s
        print(label+': '+json.dumps(s),flush=True)
    baseline,_=evaluate(groups,dict(hold=50,dip=None,entry_name='always'),start='2020-01-01')
    results['test_timehunter50_baseline']=baseline
    print('FOREX TRANSFER (same parameters, no retuning)...',flush=True)
    forex, fx_anomalies=load_data('forex')
    fx_anomalies.to_csv(OUT/'forex_ohlc_anomalies.csv',index=False)
    fx_groups=prepare(forex,dips=[] if config['dip'] is None else [config['dip']])
    fx_s,fx_rec=evaluate(fx_groups,config,cost=FOREX_COST,detail=True)
    pd.DataFrame(fx_rec).to_csv(OUT/'forex_transfer_trades.csv',index=False)
    results['forex_transfer']=fx_s
    results['forex_details']=dict(rows=len(forex),tickers=int(forex.Ticker.nunique()),
                                 start=str(forex['Date/Time'].min()),end=str(forex['Date/Time'].max()),
                                 note='Hourly forex vs daily stocks; bars do not mean identical elapsed time.')
    results['search_counts']=dict(configurations=len(configs),
                                  train_gross_5of5=int((train.train_gross_numeric_passes==5).sum()),
                                  train_net_5of5=int((train.train_numeric_passes==5).sum()),
                                  eligible_train_net_5of5=int((eligible.train_numeric_passes==5).sum()),
                                  validation_net_5of5=int((validation.validation_numeric_passes==5).sum()))
    results['locked_config']=config
    results['elapsed_seconds']=time.monotonic()-started
    (OUT/'summary.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    print('FOREX: '+json.dumps(fx_s),flush=True)
    print('COUNTS: '+json.dumps(results['search_counts']),flush=True)
    print(f'Done, elapsed={results["elapsed_seconds"]:.1f}s. See {OUT}',flush=True)


if __name__=='__main__':
    main()
