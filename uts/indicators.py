"""Causal indicators and IDX market rules. Every value at bar i uses data up to bar i only; values used before the
Open of bar i are taken from bar i-1 explicitly (shift(1))."""
import math
import numpy as np
import pandas as pd


def atr_previous(frame,length=14):
    """Wilder ATR known BEFORE bar i (value at i uses bars <= i-1)."""
    h,l,c=(frame[x].to_numpy(float) for x in ['High','Low','Close'])
    tr=h-l
    if len(c)>1:tr[1:]=np.maximum(tr[1:],np.maximum(abs(h[1:]-c[:-1]),abs(l[1:]-c[:-1])))
    atr=np.full(len(c),np.nan)
    if len(c)>=length:
        atr[length-1]=tr[:length].mean()
        for i in range(length,len(c)):atr[i]=(atr[i-1]*(length-1)+tr[i])/length
    return np.r_[np.nan,atr[:-1]] if len(c) else atr


def efficiency_ratio(close,length=20):
    """Kaufman ER at bar i from Closes i-length..i (no future data)."""
    travel=close.diff().abs().rolling(length).sum()
    er=close.diff(length).abs()/travel.replace(0,np.nan)
    return er.mask(travel==0,0)


def tick_size(price):
    """IDX price fraction (fraksi harga): <200 Rp1; 200-<500 Rp2; 500-<2000 Rp5; 2000-<5000 Rp10; >=5000 Rp25."""
    if price<200:return 1.
    if price<500:return 2.
    if price<2000:return 5.
    if price<5000:return 10.
    return 25.


def ara_pct(prev):
    """Upper auto-reject band by reference price: Rp50-200: 35%, >200-5000: 25%, >5000: 20%."""
    return .35 if prev<=200 else (.25 if prev<=5000 else .20)


# ARB schedule assumed from IDX announcements (asymmetric periods); elsewhere ARB = ARA band (symmetric).
ARB_OVERRIDES=[(pd.Timestamp('2020-03-10'),pd.Timestamp('2020-03-12'),.10),(pd.Timestamp('2020-03-13'),pd.Timestamp('2023-06-04'),.07),
    (pd.Timestamp('2023-06-05'),pd.Timestamp('2023-09-03'),.15),(pd.Timestamp('2025-04-08'),pd.Timestamp('2100-01-01'),.15)]


def arb_pct(prev,date):
    d=pd.Timestamp(date)
    for a,b,p in ARB_OVERRIDES:
        if a<=d<=b:return p
    return ara_pct(prev)


def limits(prev,date):
    """(lower, upper) auto-reject prices for the day, from the previous Close."""
    return prev*(1-arb_pct(prev,date)),prev*(1+ara_pct(prev))
