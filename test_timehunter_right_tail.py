import unittest
import numpy as np
import grid_search_timehunter as engine
from test_grid_timehunter import fixture
from backtest_timehunter_right_tail import simulate


class RightTailTests(unittest.TestCase):
    def run_case(self, opens, lows, closes, hold=4, timeout=0):
        highs=np.maximum(opens,closes)+1
        g=engine.prepare(fixture(opens,highs,lows,closes),dips=[.05])[0]
        return simulate(g,hold,.05,'always',loss_timeout=timeout,detail=True)[1]

    def test_profitable_fade_is_ignored(self):
        r=self.run_case([100,120,115,110],[99,110,114,109],[101,112,116,111])
        self.assertEqual(r[0]['reason'],'time')
        self.assertEqual(r[0]['exit_index'],3)

    def test_loss_fade_uses_next_open(self):
        r=self.run_case([100,100,85,90],[99,90,84,89],[101,92,86,91])
        self.assertEqual(r[0]['reason'],'loss_fading')
        self.assertEqual(r[0]['exit_price'],85)
        self.assertEqual(r[0]['exit_index'],2)

    def test_gap_loss_without_bar_fade_not_triggered(self):
        r=self.run_case([100,80,82,83],[99,79,81,82],[101,81,83,84])
        self.assertEqual(r[0]['reason'],'time')

    def test_intrabar_loss_recovered_by_close_ignored(self):
        r=self.run_case([100,101,103,104],[99,90,102,103],[101,102,104,105])
        self.assertEqual(r[0]['reason'],'time')

    def test_timeout_uses_next_open(self):
        r=self.run_case([100,98,97,96],[99,97,96,95],[99,98,97,96],timeout=2)
        self.assertEqual(r[0]['reason'],'loss_timeout')
        self.assertEqual(r[0]['exit_index'],2)


if __name__=='__main__':
    unittest.main()
