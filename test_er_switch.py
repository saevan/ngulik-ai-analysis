import unittest
import pandas as pd
from backtest_er_switch import regime_dates


class SwitchTests(unittest.TestCase):
    def test_previous_bar_equality_and_unknown(self):
        index=pd.date_range('2020-01-01',periods=5)
        p=pd.DataFrame({'er':[float('nan'),.2,.4,.6,.8]},index=index)
        trend,choppy=regime_dates(p,.4)
        self.assertEqual(trend,{index[3],index[4]})
        self.assertEqual(choppy,{index[2]})
        t2,c2=regime_dates(p,.6)
        self.assertTrue(t2<=trend)
        self.assertTrue(choppy<=c2)


if __name__=='__main__':unittest.main()
