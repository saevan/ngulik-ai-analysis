import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd
from backtest_prototype_swinger import signals,run_portfolio


class SwingerTests(unittest.TestCase):
    def fixture(self):
        return pd.DataFrame(dict(Open=[19.,30.,33.,37.],High=[21.,35.,35.,39.],
            Low=[18.,28.,31.,35.],Close=[20.,34.,34.,36.],tradable=True,
            **{'Date/Time':pd.date_range('2000-01-01',periods=4)}))

    def controlled(self,f):
        return pd.DataFrame(dict(tsl=[20.,25.,40.,40.],level=[np.nan,20.,25.,40.],
            buy=[False,True,False,False],sell=[False,False,False,True],
            next_buy=[False,False,True,False],next_sell=[False]*4,
            armed_buy=[False,True,False,False]))

    def test_ideal_is_level_not_close_and_flags_impossible_range(self):
        with patch('backtest_prototype_swinger.signals',side_effect=self.controlled):
            _,t,c=run_portfolio({'X':self.fixture()},'afl_ideal',0,0)
        self.assertEqual(t.entry_price.iloc[0],20)
        self.assertEqual(t.exit_price.iloc[0],40)
        self.assertEqual(c['outside_bar_fills'],2)

    def test_stop_order_respects_gap(self):
        with patch('backtest_prototype_swinger.signals',side_effect=self.controlled):
            _,t,c=run_portfolio({'X':self.fixture()},'stop_order',0,0)
        self.assertEqual(t.entry_price.iloc[0],30)
        self.assertEqual(t.exit_price.iloc[0],37)
        self.assertEqual(c['outside_bar_fills'],0)

    def test_next_open_waits_for_completed_signal(self):
        with patch('backtest_prototype_swinger.signals',side_effect=self.controlled):
            _,t,_=run_portfolio({'X':self.fixture()},'next_open',0,0)
        self.assertEqual(t.entry_price.iloc[0],33)
        self.assertEqual(t.entry_date.iloc[0],pd.Timestamp('2000-01-03'))

    def test_signal_prefix_and_scalar_direction(self):
        rng=np.random.default_rng(8);c=100+np.cumsum(rng.normal(0,3,100))
        f=pd.DataFrame(dict(Close=c,High=c+1,Low=c-1))
        s=signals(f)
        pd.testing.assert_frame_equal(s.iloc[:60],signals(f.iloc[:60]))
        state=0
        for i in range(5,len(f)):
            if c[i]>f.High.iloc[i-5:i].max():state=1
            elif c[i]<f.Low.iloc[i-5:i].min():state=-1
            expected=f.Low.iloc[i-4:i+1].min() if state==1 else f.High.iloc[i-4:i+1].max()
            self.assertEqual(s.tsl.iloc[i],expected)


if __name__=='__main__':unittest.main()
