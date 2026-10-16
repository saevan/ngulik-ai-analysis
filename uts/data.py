"""Data loading for the UTS backtest (self-contained copy of the project loaders).

Stocks: Data/Data kompas 100.csv (daily OHLCV, 100 Kompas100 tickers, 2000-01-04 .. 2025-08-15).
Cleaning (identical to the research loader): drop intraday-timestamped rows, enforce High=max(OHLC), Low=min(OHLC),
`tradable` = Volume > 0 (a bar with no transactions can never produce a fill).
"""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent.parent
DATA=ROOT/'Data'


def load_stocks(path=None):
    df=pd.read_csv(path or DATA/'Data kompas 100.csv');df.columns=df.columns.str.strip()
    df['Date/Time']=pd.to_datetime(df['Date/Time'],format='mixed',dayfirst=True)
    df=df.sort_values(['Ticker','Date/Time']).reset_index(drop=True)
    df=df.loc[df['Date/Time']==df['Date/Time'].dt.normalize()].reset_index(drop=True)
    px=df[['Open','High','Low','Close']].to_numpy(float)
    if not np.isfinite(px).all() or (px<=0).any():raise ValueError('nonfinite/nonpositive prices')
    if df.duplicated(['Ticker','Date/Time']).any():raise ValueError('duplicate ticker dates')
    df['High']=px.max(axis=1);df['Low']=px.min(axis=1);df['tradable']=df.Volume>0
    return df


def load_crypto():
    cr=pd.concat([pd.read_csv(p,parse_dates=['Date/Time']) for p in sorted((DATA/'crypto_binance_daily').glob('*.csv'))],ignore_index=True)
    cr['tradable']=cr.Volume>0
    return cr.sort_values(['Ticker','Date/Time']).reset_index(drop=True)


def load_forex(offset_hours=0):
    """Hourly forex -> daily sessions starting at `offset_hours`; dataset-edge sessions dropped."""
    fx=pd.read_csv(DATA/'Data Forex.csv');fx.columns=fx.columns.str.strip()
    fx['Date/Time']=pd.to_datetime(fx['Date/Time'],format='mixed')
    out=[]
    for t,f in fx.sort_values(['Ticker','Date/Time']).groupby('Ticker',sort=True):
        s=(f['Date/Time']-pd.Timedelta(hours=offset_hours)).dt.normalize()
        d=f.assign(session=s).groupby('session').agg(Open=('Open','first'),High=('High','max'),Low=('Low','min'),Close=('Close','last'),Volume=('Volume','sum')).reset_index()
        d=d.iloc[1:-1].copy();d['Date/Time']=d.session;d['Ticker']=t;d['tradable']=True;out.append(d.drop(columns='session'))
    return pd.concat(out,ignore_index=True)


def frames(df):
    return {str(k):f.reset_index(drop=True) for k,f in df.groupby('Ticker',sort=True)}
