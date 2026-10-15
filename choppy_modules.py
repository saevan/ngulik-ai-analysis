"""System 1 (ER-gated breakout) and candidate choppy 'parking' modules for backtest_two_module.run.

All module signals are computed at the Close (signal bar) and shifted to the entry bar; market ER labels come from
regime_proxy (equal-weight 100-stock proxy, ER20, known at the signal Close)."""
import numpy as np
import pandas as pd
from backtest_timehunter_atr import atr_previous
from backtest_breakout_er import entry_signal, efficiency_ratio

CTX={}  # filled by set_context: er (Series), trend/choppy entry-day date sets, mom_rank / atr_rank panels

def set_context(proxy,closes,atr_pct_panel):
    er=proxy.er;CTX['er']=er
    CTX['trend']=set(proxy.index[er.shift(1)>=.3]);CTX['choppy']=set(proxy.index[er.shift(1)<.3])
    CTX['mom_rank']=np.log(closes.ffill().shift(20)/closes.ffill().shift(140)).rank(axis=1,pct=True)
    CTX['atr_rank']=atr_pct_panel.rank(axis=1,pct=True)

def _panel(name,f):
    s=CTX[name][f.Ticker.iloc[0]] if f.Ticker.iloc[0] in CTX[name] else None
    return pd.Series(np.nan,index=f.index) if s is None else f['Date/Time'].map(s)

def _shift(x):return pd.Series(np.asarray(x,bool)).shift(1,fill_value=False).to_numpy(bool)

def _gate(f,dates):return f['Date/Time'].isin(dates).to_numpy()&f.tradable.to_numpy(bool)

def _fade_sma(f,a,sma=30,fade=2.):
    return dict(fade=np.isfinite(a)&(a>0)&((f.Open-f.Low).to_numpy()>=fade*a),smaexit=(f.Close<f.Close.rolling(sma).mean()).to_numpy(bool))

def system1():
    def prep(f):
        a=atr_previous(f);c=f.Close
        raw=(c>f.High.shift(1).rolling(20).max())&(efficiency_ratio(c,20)>=.3)
        d=dict(entry=entry_signal(f,.3)&_gate(f,CTX['trend']),
            sigclose=(raw&(f['Date/Time'].map(CTX['er'])>=.3)).fillna(False).to_numpy(bool))
        d.update(_fade_sma(f,a));return d
    def ex(md,i,p,age):return 'fading' if md['fade'][i] else ('sma_exit' if md['smaexit'][i] else None)
    return dict(name='system1',cap=10,prepare=prep,exit_fn=ex)

def rs_breakout(er_min=.5,channel=20,cap=10):
    """Choppy market, stock itself trending: Close > HHV(channel) and stock ER20 >= er_min. Exits as system 1."""
    def prep(f):
        a=atr_previous(f);c=f.Close
        sig=(c>f.High.shift(1).rolling(channel).max())&(efficiency_ratio(c,20)>=er_min)
        d=dict(entry=_shift(sig.fillna(False))&_gate(f,CTX['choppy']));d.update(_fade_sma(f,a));return d
    def ex(md,i,p,age):return 'fading' if md['fade'][i] else ('sma_exit' if md['smaexit'][i] else None)
    return dict(name=f'rs_breakout_er{er_min}_hhv{channel}',cap=cap,prepare=prep,exit_fn=ex)

def momentum_parking(top=.9,time_exit=20,cap=10):
    """Choppy market: top cross-sectional 120d momentum (skip 20d) and Close > SMA50; best momentum first.
    Exit: Close < SMA50, fading 2 ATR, or age >= time_exit (0 = no time exit)."""
    def prep(f):
        a=atr_previous(f);c=f.Close;mr=_panel('mom_rank',f);sma50=c.rolling(50).mean()
        sig=(mr>=top)&(c>sma50)
        d=dict(entry=_shift(sig.fillna(False))&_gate(f,CTX['choppy']),score=mr.shift(1).to_numpy(float),
            below50=(c<sma50).to_numpy(bool))
        d.update(_fade_sma(f,a));return d
    def ex(md,i,p,age):
        if md['fade'][i]:return 'fading'
        if md['below50'][i]:return 'below_sma50'
        if time_exit and age>=time_exit:return 'time'
        return None
    return dict(name=f'momentum_top{top}_t{time_exit}',cap=cap,prepare=prep,exit_fn=ex)

def lowvol_uptrend(max_rank=.3,cap=10):
    """Choppy market: stable uptrend (Close > SMA200, SMA50 > SMA200) with low ATR% (cross-sectional rank <= max_rank);
    lowest volatility first. Exit: Close < SMA50 or fading 2 ATR."""
    def prep(f):
        a=atr_previous(f);c=f.Close;sma50=c.rolling(50).mean();sma200=c.rolling(200).mean();ar=_panel('atr_rank',f)
        sig=(c>sma200)&(sma50>sma200)&(ar<=max_rank)
        d=dict(entry=_shift(sig.fillna(False))&_gate(f,CTX['choppy']),score=(-ar).shift(1).to_numpy(float),below50=(c<sma50).to_numpy(bool))
        d.update(_fade_sma(f,a));return d
    def ex(md,i,p,age):
        if md['fade'][i]:return 'fading'
        if md['below50'][i]:return 'below_sma50'
        return None
    return dict(name=f'lowvol_uptrend_r{max_rank}',cap=cap,prepare=prep,exit_fn=ex)
