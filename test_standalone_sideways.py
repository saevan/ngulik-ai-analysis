import unittest
import numpy as np
import pandas as pd
from search_standalone_sideways import make_entry
from backtest_breakout_er_portfolio import portfolio


class StandaloneTests(unittest.TestCase):
    def test_custom_recovery_and_age_exits_use_next_open(self):
        f=pd.DataFrame({'Date/Time':pd.date_range('2000-01-01',periods=5),'Open':[100,101,105,110,115],
            'High':[100,101,105,110,115],'Low':[100,101,105,110,115],'Close':[100,101,105,110,115],'tradable':True})
        entry=lambda f:np.array([True,False,False,False,False])
        _,t,_=portfolio({'A':f},hold=None,entry_builder=entry,exit_builder=lambda f:(f.Close>=105).to_numpy())
        self.assertEqual(t.reason.iloc[0],'custom_exit')
        self.assertEqual(t.exit_price.iloc[0],110)
        _,t,_=portfolio({'A':f},hold=None,entry_builder=entry,max_age_signal=2)
        self.assertEqual(t.reason.iloc[0],'max_age_next_open')
        self.assertEqual(t.exit_price.iloc[0],105)

    def test_signal_prefix_and_market_gate(self):
        n=260;prices=100+np.arange(n)*.05+np.sin(np.arange(n))
        f=pd.DataFrame({'Date/Time':pd.date_range('2000-01-01',periods=n),'Open':prices,'High':prices+1,'Low':prices-1,'Close':prices,'tradable':True})
        allowed=set(f['Date/Time'].iloc[::2])
        for family in ['rsi5','rsi15','channel_rebound','breakout5']:
            builder=make_entry(dict(family=family),allowed)
            a=builder(f)
            np.testing.assert_array_equal(builder(f.iloc[:240]),a[:240])
            self.assertFalse(a[~f['Date/Time'].isin(allowed)].any())

    def test_start_flat_with_warmup_history(self):
        f=pd.DataFrame({'Date/Time':pd.date_range('2000-01-01',periods=40),'Open':100.,'High':101.,'Low':99.,'Close':100.,'tradable':True})
        curve,t,_=portfolio({'A':f},start='2000-02-01',entry_builder=lambda f:np.ones(len(f),dtype=bool))
        self.assertEqual(str(curve.index[0].date()),'2000-02-01')
        self.assertEqual(str(t.entry_date.iloc[0].date()),'2000-02-01')
        self.assertEqual(t.entry_notional.iloc[0],1e8)


if __name__=='__main__':unittest.main()
