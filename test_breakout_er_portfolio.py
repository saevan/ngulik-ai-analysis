import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd
from backtest_breakout_er_portfolio import portfolio


def frame(prices,entries):
    n=len(prices)
    return pd.DataFrame({'Date/Time':pd.date_range('2000-01-01',periods=n),
        'Open':prices,'High':prices,'Low':prices,'Close':prices,
        'tradable':True,'test_entry':entries})


class PortfolioTests(unittest.TestCase):
    def run_model(self,frames,**kwargs):
        with patch('backtest_breakout_er_portfolio.entry_signal',side_effect=lambda f,t:f.test_entry.to_numpy(bool)),patch('backtest_breakout_er_portfolio.atr_previous',side_effect=lambda f:np.full(len(f),10000.)):
            return portfolio(frames,capital=1000,**kwargs)

    def test_compounding_from_previous_equity(self):
        curve,trades,_=self.run_model({'A':frame([100,200,200,400],[1,0,1,0])},hold=2)
        np.testing.assert_allclose(trades.entry_notional,[100,110])
        self.assertAlmostEqual(curve.equity.iloc[-1],1210)

    def test_no_hold_limit_keeps_position_past_200(self):
        _,trades,_=self.run_model({'A':frame([100]*205,[1]+[0]*204)},hold=None)
        self.assertEqual(trades.bars.iloc[0],205)
        self.assertEqual(trades.reason.iloc[0],'period_end')

    def test_no_hold_limit_still_fades_from_current_open(self):
        f=frame([100,110,90,95],[1,0,0,0])
        f.loc[1,'Low']=50
        with patch('backtest_breakout_er_portfolio.entry_signal',side_effect=lambda f,t:f.test_entry.to_numpy(bool)),patch('backtest_breakout_er_portfolio.atr_previous',side_effect=lambda f:np.full(len(f),10.)):
            _,trades,_=portfolio({'A':f},capital=1000,hold=None)
        self.assertEqual(trades.reason.iloc[0],'fading')
        self.assertEqual(trades.exit_price.iloc[0],90)
        self.assertEqual(trades.bars.iloc[0],3)

    def test_max_ten_and_cash(self):
        frames={f'A{i:02}':frame([100,100,100],[1,0,0]) for i in range(11)}
        curve,trades,c=self.run_model(frames)
        self.assertEqual(len(trades),10)
        self.assertEqual(curve.positions.max(),10)
        self.assertEqual(c['rejected_slots'],1)
        self.assertAlmostEqual(curve.cash.iloc[0],0)

    def test_close_exit_does_not_free_slot_at_same_open(self):
        frames={'A':frame([100,100,100],[1,0,0]),'B':frame([100,100,100],[0,1,0])}
        _,trades,c=self.run_model(frames,slots=1,hold=2)
        self.assertEqual(trades.ticker.tolist(),['A'])
        self.assertEqual(c['rejected_slots'],1)

    def test_prior_close_not_current_close_sizes_entry(self):
        frames={'A':frame([100,100,1000],[1,0,0]),'B':frame([100,100,100],[0,0,1])}
        _,trades,_=self.run_model(frames)
        self.assertAlmostEqual(trades.loc[trades.ticker=='B','entry_notional'].iloc[0],100)


if __name__=='__main__':unittest.main()
