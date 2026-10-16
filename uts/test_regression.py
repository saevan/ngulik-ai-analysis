"""The UTS engine in compatibility mode must reproduce the audited research engine exactly
(lookahead_audit_results/full_{fees,spread1}_buystop_strict_equity.csv, from backtest_stop_execution strict_orders=True)."""
from pathlib import Path
import numpy as np
import pandas as pd
from uts.data import load_stocks, frames
from uts.engine import run, Params, Execution

ROOT=Path(__file__).resolve().parent.parent

def main():
    fr=frames(load_stocks())
    for name,ex in [('fees',Execution(ticks=0,lot=0,grid=False)),('spread1',Execution(ticks=1,lot=100,grid=True))]:
        ex.liquidity=None;ex.price_limits=False;ex.mark='liquidation';ex.close_at_end=True;ex.orderbook_tradable_filter=True
        with np.errstate(invalid='ignore',divide='ignore'):eq,tr,op=run(fr,Params(),ex)
        ref=pd.read_csv(ROOT/'lookahead_audit_results'/f'full_{name}_buystop_strict_equity.csv')
        np.testing.assert_allclose(eq.equity.to_numpy(),ref.equity.to_numpy(),rtol=1e-10)
        print(name,'regression OK',len(tr),'trades',len(op),'open')

if __name__=='__main__':main()
