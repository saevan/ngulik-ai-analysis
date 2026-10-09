import unittest
from unittest.mock import patch
import numpy as np
from test_breakout_er_portfolio import frame
from backtest_breakout_er_portfolio import portfolio


class TrailTests(unittest.TestCase):
    def run_case(self, prices, tradable=None):
        f=frame(prices,[1]+[0]*(len(prices)-1))
        if tradable is not None:f['tradable']=tradable
        with patch('backtest_breakout_er_portfolio.entry_signal',side_effect=lambda f,t:f.test_entry.to_numpy(bool)),patch('backtest_breakout_er_portfolio.atr_previous',side_effect=lambda f:np.full(len(f),10.)):
            return portfolio({'A':f},capital=1000,profit_trail=(2,1))[1]

    def test_completed_close_then_gap_at_next_open(self):
        t=self.run_case([100,130,115,90,100])
        self.assertEqual(t.reason.iloc[0],'profit_trail')
        self.assertEqual(t.exit_price.iloc[0],90)
        self.assertEqual(t.bars.iloc[0],4)

    def test_does_not_activate_before_threshold(self):
        t=self.run_case([100,115,100,90,100])
        self.assertEqual(t.reason.iloc[0],'period_end')

    def test_exit_waits_for_tradable_open(self):
        t=self.run_case([100,130,115,110,95,100],[True,True,True,False,True,True])
        self.assertEqual(t.exit_price.iloc[0],95)
        self.assertEqual(t.bars.iloc[0],5)


if __name__=='__main__':unittest.main()
