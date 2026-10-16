"""Forward test (paper trading) with the FROZEN strategy: run on data that starts after the freeze date.

Usage:  python -m uts.forward_test --data path/to/new_kompas100.csv [--start 2026-10-17]
The CSV must have the same columns as Data/Data kompas 100.csv (Ticker, Date/Time, Open, High, Low, Close, Volume) and
should include at least ~160 trading days BEFORE --start so indicators warm up. Parameters and code are read from
output/results.json ("frozen"); the SHA-256 of the code files is checked so the frozen version is the one that runs.
Writes output/forward_results.json; build_dashboard shows it separately from the backtest.
"""
import argparse, hashlib, json
from dataclasses import replace
from pathlib import Path
import numpy as np
from .data import load_stocks, frames
from .engine import run, Params, Execution
from . import metrics as M

HERE=Path(__file__).resolve().parent

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--data',required=True);ap.add_argument('--start',default=None);a=ap.parse_args()
    res=json.load(open(HERE/'output'/'results.json'));fz=res['frozen']
    h=hashlib.sha256()
    for f in ['engine.py','indicators.py','data.py','metrics.py']:h.update((HERE/f).read_bytes())
    if h.hexdigest()!=fz['code_sha256']:raise SystemExit('Code changed after the freeze date: forward test refused.')
    start=a.start or fz['date'];p=replace(Params(),**fz['params'])
    with np.errstate(invalid='ignore',divide='ignore'):eq,tr,op=run(frames(load_stocks(a.data)),p,Execution(),start=start)
    m=M.compute(eq,tr,res['meta']['capital'],op)
    out=dict(start=start,end=str(eq.index[-1].date()),weeks=(eq.index[-1]-eq.index[0]).days/7,metrics=m,
        trades=tr.astype(str).to_dict('records'),open_positions=op.astype(str).to_dict('records'),equity=[[str(d.date()),float(v)] for d,v in eq.equity.items()])
    json.dump(out,open(HERE/'output'/'forward_results.json','w'),indent=1,default=str)
    print(f"forward {start}..{out['end']} ({out['weeks']:.1f} weeks): return {eq.equity.iloc[-1]/res['meta']['capital']-1:.2%}, trades {len(tr)}, open {len(op)}")

if __name__=='__main__':main()
