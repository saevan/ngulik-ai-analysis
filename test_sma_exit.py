import unittest
from unittest.mock import patch
import numpy as np
from test_breakout_er_portfolio import frame
from backtest_breakout_er_portfolio import portfolio


class SmaExitTests(unittest.TestCase):
    def run_case(self, suspended=False):
        f=frame([100]*30+[90,80,85,95],[0]*29+[1]+[0]*4)
        if suspended:f.loc[31,'tradable']=False
        with patch('backtest_breakout_er_portfolio.atr_previous',side_effect=lambda f:np.full(len(f),10000.)):
            return portfolio({'A':f},capital=1000,hold=None,exit_sma=30,
                entry_builder=lambda f:f.test_entry.to_numpy(bool))[1]

    def test_equality_does_not_exit_and_below_sma_exits_next_open(self):
        t=self.run_case().iloc[0]
        self.assertEqual(t.reason,'sma_exit')
        self.assertEqual(t.exit_price,80)
        self.assertEqual(t.bars,3)

    def test_suspension_preserves_exit_queue(self):
        t=self.run_case(True).iloc[0]
        self.assertEqual(t.exit_price,85)
        self.assertEqual(t.bars,4)


if __name__=='__main__':unittest.main()
