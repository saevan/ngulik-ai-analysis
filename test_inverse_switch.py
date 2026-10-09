import unittest
import numpy as np
from test_breakout_er_portfolio import frame
from backtest_breakout_er_portfolio import portfolio

class InverseSwitchTests(unittest.TestCase):
    def test_inverse_keeps_original_exit_after_gate_changes(self):
        f=frame([100,100,90,70,110,120],[False,False,True,False,False,False])
        sec=dict(style='inverse',slots=10,reserved=False,primary_first=True,
                 allowed_dates={f['Date/Time'].iloc[1]},
                 entry_builder=lambda f:np.array([False,True,False,False,False,False]),
                 exit_builder=lambda f:np.array([False,False,False,False,True,False]))
        _,t,_=portfolio({'A':f},hold=None,fade=.1,exit_sma=2,entry_builder=lambda f:f.test_entry.to_numpy(),secondary=sec)
        self.assertEqual(len(t),1)
        self.assertEqual(t.iloc[0].module,'range')
        self.assertEqual(t.iloc[0].exit_date,f['Date/Time'].iloc[5])
        self.assertEqual(t.iloc[0].reason,'inverse_original_buy')

    def test_inverse_only_matches_direct_custom_exit(self):
        f=frame([100,100,90,70,110,120],[False,True,False,False,False,False])
        ent=lambda f:f.test_entry.to_numpy()
        ex=lambda f:np.array([False,False,False,False,True,False])
        sec=dict(style='inverse',slots=10,reserved=False,primary_first=True,allowed_dates=set(f['Date/Time']),entry_builder=ent,exit_builder=ex)
        a,_,_=portfolio({'A':f},hold=None,fade=float('inf'),entry_builder=ent,exit_builder=ex)
        b,_,_=portfolio({'A':f},hold=None,fade=2,entry_builder=lambda f:np.zeros(len(f),bool),secondary=sec)
        np.testing.assert_allclose(a.equity,b.equity)

if __name__=='__main__':unittest.main()
