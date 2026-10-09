import unittest
from unittest.mock import patch
import numpy as np
from test_breakout_er_portfolio import frame
from backtest_breakout_er_portfolio import portfolio


class EntryStopTests(unittest.TestCase):
    def run_case(self,prices,low=None,tradable=None):
        f=frame(prices,[True]+[False]*(len(prices)-1))
        if low is not None:f['Low']=low
        if tradable is not None:f['tradable']=tradable
        with patch('backtest_breakout_er_portfolio.atr_previous',return_value=np.array([10.]+[100.]*(len(f)-1))):
            return portfolio({'A':f},hold=None,fade=100,entry_builder=lambda f:f.test_entry.to_numpy(bool),entry_stop_atr=1)[1]

    def test_fixed_entry_atr_and_gap_next_open(self):
        t=self.run_case([100,90,70,80]).iloc[0]
        self.assertEqual(t.reason,'entry_atr_stop')
        self.assertEqual(t.exit_price,70)
        self.assertEqual(t.bars,3)

    def test_intraday_touch_not_close_signal(self):
        t=self.run_case([100,95,105],[100,80,105]).iloc[0]
        self.assertEqual(t.reason,'period_end')

    def test_pending_survives_suspension_and_recovery(self):
        t=self.run_case([100,90,105,110,115],tradable=[True,True,False,True,True]).iloc[0]
        self.assertEqual(t.reason,'entry_atr_stop')
        self.assertEqual(t.exit_price,110)


if __name__=='__main__':unittest.main()
