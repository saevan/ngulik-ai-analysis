import unittest
import pandas as pd
from test_breakout_er_portfolio import frame
from optimize_primary_inverse_regimes import builders

class RotationTests(unittest.TestCase):
    def test_close_signal_current_er_entry_gate_previous_er(self):
        f=frame([100]*40,[False]*40)
        p=pd.DataFrame({'er':[.4]*30+[.1]*10},index=pd.DatetimeIndex(f['Date/Time']))
        signals,trend,choppy=builders(dict(hhv=20,sma=30,rotate=True),p)
        _,_,px,ix=signals(f)
        self.assertTrue(px[30])
        self.assertFalse(ix[30])
        self.assertIn(f['Date/Time'].iloc[30],trend)
        self.assertIn(f['Date/Time'].iloc[31],choppy)
        self.assertFalse(trend.intersection(choppy))

    def test_carry_does_not_add_regime_exit(self):
        f=frame([100]*40,[False]*40)
        p=pd.DataFrame({'er':[.4]*30+[.1]*10},index=pd.DatetimeIndex(f['Date/Time']))
        signals,_,_=builders(dict(hhv=20,sma=30,rotate=False),p)
        _,_,px,ix=signals(f)
        self.assertFalse(px.any());self.assertFalse(ix.any())

if __name__=='__main__':unittest.main()
