import unittest
import numpy as np
import pandas as pd
from backtest_timehunter_atr import atr_previous, signals


class ATRTests(unittest.TestCase):
    def setUp(self):
        rng=np.random.default_rng(99)
        c=100*np.exp(np.cumsum(rng.normal(0,.03,200)))
        self.f=pd.DataFrame(dict(Open=c,High=c*1.03,Low=c*.96,Close=c*1.01))

    def test_price_scale_invariance(self):
        a,b=signals(self.f,1,2)
        for scale in [.0001,10000]:
            x,y=signals(self.f*scale,1,2)
            np.testing.assert_array_equal(a,x)
            np.testing.assert_array_equal(b,y)

    def test_prefix_causality(self):
        a,b=signals(self.f,1,2)
        x,y=signals(self.f.iloc[:100],1,2)
        np.testing.assert_array_equal(a[:100],x)
        np.testing.assert_array_equal(b[:100],y)

    def test_current_bar_does_not_change_its_atr(self):
        a=atr_previous(self.f)
        f=self.f.copy();f.loc[100,'High']*=10
        self.assertEqual(a[100],atr_previous(f)[100])
        self.assertNotEqual(a[101],atr_previous(f)[101])

    def test_seed_and_flat_data(self):
        f=pd.DataFrame(dict(Open=[100.]*40,High=[102.]*40,Low=[98.]*40,Close=[100.]*40))
        a=atr_previous(f)
        self.assertTrue(np.isnan(a[:14]).all())
        np.testing.assert_allclose(a[14:],4)
        f[:]=100
        entry,fade=signals(f,1,2)
        self.assertFalse(entry.any());self.assertFalse(fade.any())


if __name__=='__main__': unittest.main()
