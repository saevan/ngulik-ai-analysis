"""Download public daily spot candles; no account/key or trading requests."""
import hashlib
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen
import pandas as pd

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'Data'/'crypto_binance_daily'
SYMBOLS=['BTCUSDT','ETHUSDT','BNBUSDT','XRPUSDT','ADAUSDT','SOLUSDT','DOGEUSDT','LTCUSDT']


def main():
    OUT.mkdir(exist_ok=True)
    start=int(pd.Timestamp('2017-01-01',tz='UTC').timestamp()*1000)
    end=int(pd.Timestamp('2025-08-16',tz='UTC').timestamp()*1000)-1
    metadata=[]
    for symbol in SYMBOLS:
        rows=[]; cursor=start; urls=[]
        while cursor <= end:
            url='https://api.binance.com/api/v3/klines?'+urlencode(dict(symbol=symbol,interval='1d',startTime=cursor,endTime=end,limit=1000))
            with urlopen(url,timeout=30) as response:
                page=json.load(response)
            if not isinstance(page,list): raise ValueError(page)
            urls.append(url)
            if not page: break
            rows.extend(page)
            next_cursor=int(page[-1][0])+86400000
            if next_cursor <= cursor: raise ValueError('Non-progressing pagination')
            cursor=next_cursor
            if len(page)<1000: break
        if not rows: raise ValueError('No rows for '+symbol)
        raw=OUT/f'{symbol}_raw.json'
        raw.write_text(json.dumps(rows),encoding='utf-8')
        frame=pd.DataFrame(rows)
        result=pd.DataFrame({'Ticker':symbol,'Date/Time':pd.to_datetime(frame[0],unit='ms',utc=True).dt.tz_localize(None),
            'Open':frame[1].astype(float),'High':frame[2].astype(float),'Low':frame[3].astype(float),
            'Close':frame[4].astype(float),'Volume':frame[5].astype(float)})
        assert not result['Date/Time'].duplicated().any()
        assert (frame[6].astype('int64')<=end).all()
        result.to_csv(OUT/f'{symbol}.csv',index=False)
        metadata.append(dict(symbol=symbol,rows=len(result),start=str(result['Date/Time'].min()),
            end=str(result['Date/Time'].max()),urls=urls,raw_sha256=hashlib.sha256(raw.read_bytes()).hexdigest()))
        print(symbol,len(result),str(result['Date/Time'].min()),str(result['Date/Time'].max()),flush=True)
    (OUT/'sources.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')


if __name__=='__main__': main()
