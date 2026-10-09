import unittest
from unittest.mock import patch
import numpy as np
from test_breakout_er_portfolio import frame
from backtest_choppy_inverted_signals import inverted_builders
from backtest_breakout_er_portfolio import portfolio

class InversionTests(unittest.TestCase):
    def fixture(self):
        prices=[99,101]*15+[90,91]+[92]*8+[130,140,140,140,140]
        return frame(prices,[False]*len(prices))

    def test_exit_outside_choppy_executes_next_open(self):
        f=self.fixture();er=np.array([.1]*40+[.8]*5)
        with patch('backtest_choppy_inverted_signals.efficiency_ratio',return_value=er):
            entry,exit_signal=inverted_builders(('market_stock',0),{f['Date/Time'].iloc[31]})
            _,t,_=portfolio({'A':f},hold=None,fade=float('inf'),entry_builder=entry,exit_builder=exit_signal)
        self.assertEqual(len(t),1)
        self.assertEqual(t.iloc[0].entry_price,91)
        self.assertEqual(t.iloc[0].exit_price,140)
        self.assertEqual(t.iloc[0].exit_date,f['Date/Time'].iloc[41])
        self.assertEqual(t.iloc[0].reason,'custom_exit')

    def test_stock_gate_blocks_stock_trend_even_if_market_choppy(self):
        f=self.fixture();allowed={f['Date/Time'].iloc[31]}
        with patch('backtest_choppy_inverted_signals.efficiency_ratio',return_value=np.ones(len(f))):
            market,_=inverted_builders(('market',0),allowed)
            both,_=inverted_builders(('market_stock',0),allowed)
            self.assertTrue(market(f)[31])
            self.assertFalse(both(f).any())

if __name__=='__main__':unittest.main()
