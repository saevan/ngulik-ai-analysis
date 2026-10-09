import unittest
from unittest.mock import patch
import numpy as np
from test_breakout_er_portfolio import frame
from backtest_breakout_er_portfolio import portfolio


class SecondaryTests(unittest.TestCase):
    def test_primary_gets_last_slot_before_alphabetically_earlier_secondary(self):
        f=frame([100]*20+[90,90,105,110,110],[False]*25)
        trend=f.copy();trend.loc[21,'test_entry']=True
        with patch('backtest_breakout_er_portfolio.entry_signal',side_effect=lambda f,t:f.test_entry.to_numpy(bool)),patch('backtest_breakout_er_portfolio.atr_previous',side_effect=lambda f:np.full(len(f),10.)),patch('backtest_breakout_er_portfolio.efficiency_ratio',side_effect=lambda c,n:c*0):
            _,trades,_=portfolio({'A':f,'Z':trend},capital=1000,slots=1,
                secondary=dict(dip=.5,hold=10,slots=1,reserved=False,primary_first=True))
        self.assertEqual(trades.ticker.tolist(),['Z'])
        self.assertEqual(trades.module.tolist(),['trend'])

    def test_reserved_slots_and_independent_exit_next_open(self):
        # Stable history then discounted Close; entry next Open, mean recovery exit following Open.
        f=frame([100]*20+[90,90,105,110,110],[0]*25)
        f['test_entry']=False
        trend=f.copy();trend['test_entry']=False;trend.loc[21,'test_entry']=True
        with patch('backtest_breakout_er_portfolio.entry_signal',side_effect=lambda f,t:f.test_entry.to_numpy(bool)),patch('backtest_breakout_er_portfolio.atr_previous',side_effect=lambda f:np.full(len(f),10.)),patch('backtest_breakout_er_portfolio.efficiency_ratio',side_effect=lambda c,n:c*0):
            curve,trades,_=portfolio({'A':f,'B':trend,'C':trend},capital=1000,slots=2,
                secondary=dict(dip=.5,hold=10,slots=1,reserved=True))
        r=trades[trades.module=='range'].iloc[0]
        self.assertEqual(r.entry_price,90)
        self.assertEqual(r.exit_price,110)
        self.assertEqual(r.reason,'range_mean')
        self.assertEqual(r.bars,3)
        self.assertEqual(len(trades[trades.module=='trend']),1)
        self.assertLessEqual(curve.positions.max(),2)


if __name__=='__main__':unittest.main()
