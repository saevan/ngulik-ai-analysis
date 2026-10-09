import unittest
from unittest.mock import patch
import numpy as np
from backtest_idx_costs import Costs,tick_size
from backtest_breakout_er_portfolio import portfolio
from test_breakout_er_portfolio import frame


class CostTests(unittest.TestCase):
    def test_tick_bands(self):
        self.assertEqual([tick_size(x) for x in [199,200,499,500,1999,2000,4999,5000]],[1,2,2,5,5,10,10,25])

    def test_side_rounding(self):
        c=Costs(grid=True,ticks_per_side=1)
        self.assertEqual(c.quote(501,499,'buy'),504)
        self.assertEqual(c.quote(501,499,'sell'),498)
        # Prior close fixes daily tick despite crossing price bands.
        self.assertEqual(c.quote(2000,1995,'buy'),2005)

    def test_round_lot_includes_buy_fee(self):
        c=Costs(round_lot=100)
        q=c.quantity(100000000,1000)
        self.assertEqual(q%100,0)
        self.assertLessEqual(q*1000*1.0015,100000000)
        self.assertGreater((q+100)*1000*1.0015,100000000)

    def test_fees_charged_once_and_equity_liquidation_mark(self):
        f=frame([100,100,100],[1,0,0]);c=Costs()
        with patch('backtest_breakout_er_portfolio.entry_signal',side_effect=lambda f,t:f.test_entry.to_numpy(bool)),patch('backtest_breakout_er_portfolio.atr_previous',side_effect=lambda f:np.full(len(f),10000.)):
            curve,trades,_=portfolio({'X':f},capital=1000,slots=1,cost_model=c)
        expected=1000/1.0015*.9975
        np.testing.assert_allclose(curve.equity,expected)
        self.assertAlmostEqual(trades.pnl.iloc[0],expected-1000)
        self.assertAlmostEqual(trades.buy_fee.iloc[0]+trades.sell_fee.iloc[0],1000-expected)


if __name__=='__main__':unittest.main()
