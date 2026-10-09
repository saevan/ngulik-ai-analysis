import unittest
import numpy as np
import pandas as pd
from test_breakout_er_portfolio import frame
from backtest_choppy_er_exit import er_exit_builder
from backtest_breakout_er_portfolio import portfolio

class ERExitTests(unittest.TestCase):
    def test_completed_market_er_exits_next_open_not_same_bar(self):
        f=frame([100]*31+[98,97,96,80,79],[False]*31+[True]+[False]*4)
        p=pd.DataFrame({'er':[.1]*33+[.4]*3},index=pd.DatetimeIndex(f['Date/Time']))
        exits=lambda f:er_exit_builder(f,p,'market_er',lambda f:np.zeros(len(f),bool))
        _,t,_=portfolio({'A':f},hold=None,fade=float('inf'),entry_builder=lambda f:f.test_entry.to_numpy(),exit_builder=exits)
        self.assertEqual(t.iloc[0].exit_date,f['Date/Time'].iloc[34])
        self.assertEqual(t.iloc[0].exit_price,80)

    def test_stock_downtrend_also_exits(self):
        f=frame(list(range(100,60,-1)),[False]*40)
        p=pd.DataFrame({'er':0.1},index=pd.DatetimeIndex(f['Date/Time']))
        result=er_exit_builder(f,p,'stock_er',lambda f:np.zeros(len(f),bool))
        self.assertTrue(result[20:].all())

    def test_combined_retains_original_signal_when_market_choppy(self):
        f=frame([100]*40,[False]*40)
        p=pd.DataFrame({'er':0.1},index=pd.DatetimeIndex(f['Date/Time']))
        original=np.zeros(40,bool);original[30]=True
        self.assertTrue(er_exit_builder(f,p,'market_or_original',lambda f:original)[30])
        self.assertFalse(er_exit_builder(f,p,'market_er',lambda f:original)[30])

if __name__=='__main__':unittest.main()
