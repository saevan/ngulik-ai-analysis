import unittest
import numpy as np
import pandas as pd
from backtest_breakout_er import efficiency_ratio,entry_signal


class ERTests(unittest.TestCase):
    def test_trend_chop_flat(self):
        self.assertAlmostEqual(efficiency_ratio(pd.Series(np.arange(50.))).iloc[-1],1)
        self.assertAlmostEqual(efficiency_ratio(pd.Series([100.,101.]*25)).iloc[-1],0)
        self.assertEqual(efficiency_ratio(pd.Series([100.]*50)).iloc[-1],0)

    def test_scale_invariance_and_prefix(self):
        rng=np.random.default_rng(1)
        c=pd.Series(100+np.cumsum(rng.normal(size=100)))
        np.testing.assert_allclose(efficiency_ratio(c),efficiency_ratio(c*1000),atol=1e-12,equal_nan=True)
        f=pd.DataFrame(dict(Close=c,High=c+0.1))
        np.testing.assert_array_equal(entry_signal(f)[:70],entry_signal(f.iloc[:70]))
        np.testing.assert_array_equal(entry_signal(f,.3)[:70],entry_signal(f.iloc[:70],.3))

    def test_previous_high_and_next_open(self):
        f=pd.DataFrame(dict(Close=[100.]*21+[102.,103.,104.],High=[101.]*21+[103.,104.,105.]))
        s=entry_signal(f,.3)
        self.assertFalse(s[21])
        self.assertTrue(s[22]) # Close102 broke PRIOR high101, not current High103.


if __name__=='__main__':unittest.main()
