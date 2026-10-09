import unittest
import numpy as np
import pandas as pd
from test_breakout_er_portfolio import frame
from backtest_choppy_breakout_only_exit import er_exit_builder
from backtest_choppy_inverted_signals import inverted_builders

class BreakoutOnlyTests(unittest.TestCase):
    def test_breakout_exits_even_when_stock_er_low(self):
        f=frame([80,100]*20+[101],[False]*41)
        _,old=inverted_builders(('market',0),set())
        p=pd.DataFrame({'er':.1},index=pd.DatetimeIndex(f['Date/Time']))
        self.assertFalse(old(f)[-1])
        self.assertTrue(er_exit_builder(f,p,'breakout_only',old)[-1])

    def test_equal_prior_high_is_not_breakout(self):
        f=frame([80,100]*20+[100],[False]*41)
        p=pd.DataFrame({'er':.1},index=pd.DatetimeIndex(f['Date/Time']))
        self.assertFalse(er_exit_builder(f,p,'breakout_only',lambda f:np.zeros(len(f),bool))[-1])

if __name__=='__main__':unittest.main()
