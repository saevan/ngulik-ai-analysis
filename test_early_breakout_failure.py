import unittest
import numpy as np
from test_breakout_er_portfolio import frame
from backtest_breakout_er_portfolio import portfolio


class FailureTests(unittest.TestCase):
    def run_case(self,prices,window=5,confirm=2):
        f=frame(prices,[False]*4+[True]+[False]*(len(prices)-5))
        return portfolio({'A':f},hold=None,fade=100,early_failure=(3,window,confirm),
            entry_builder=lambda f:f.test_entry.to_numpy(bool))[1].iloc[0]

    def test_fixed_pre_signal_level_two_closes_then_next_open(self):
        t=self.run_case([100,100,100,105,110,99,98,90,105])
        self.assertEqual(t.reason,'early_breakout_failure')
        self.assertEqual(t.exit_price,90)
        self.assertEqual(t.bars,4)

    def test_recovery_resets_confirmation(self):
        t=self.run_case([100,100,100,105,110,99,101,99,105])
        self.assertEqual(t.reason,'period_end')

    def test_no_trigger_after_observation_window(self):
        t=self.run_case([100,100,100,105,110,99,98,90,105],window=1)
        self.assertEqual(t.reason,'period_end')


if __name__=='__main__':unittest.main()
