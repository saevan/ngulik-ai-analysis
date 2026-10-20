# Market properties during SIDEWAYS markets (pre-registered 20 Oct 2026, before any result)

Purpose: learn how the market behaves in sideways periods before designing a second logic. Nothing here is a system.

Data: market_properties_v2 panel (clean log levels), 2000-01-01..2025-08-15; P0 1994-99 not used (too few eligible stocks).
Universe: realistic = liquid at the time (top half by 120-day traded value, >= 250 bars) and not stale (pit_universe.py,
pit_stale_liquidity.py). Abnormal return = minus the same-day equal-weight mean of eligible stocks over the same window.
Regime: analyze_portfolio_regimes.regime_proxy (EW proxy ER20 >= 0.3 with 20-day direction up/down, else sideways),
label taken from the previous Close (conservative). Secondary check: ret60 definition (+-5% over 60 days).
Statistics: per-day mean over events/stocks -> mean over the days of each regime, Newey-West t (lags = horizon, 5 for
daily); sideways minus other days via dummy regression; sign of the sideways effect in 2000-07, 2008-15, 2016-20, 2021-25.

Tests (S1-S11):
- S1 market dynamics: share of days and episode lengths (descriptive); EW forward 20-day return (Open t+1 -> Close t+20)
  on sideways vs other days; what follows a sideways episode of >= 5 days (uptrend vs downtrend), binomial test.
- S2 dispersion: cross-sectional std of daily returns by regime; within sideways days, stocks trending on their own
  (own ER20 >= 0.3 and 20-day change > 0): abnormal fo20.
- S3 time-series predictability by regime: sign(r_cc[t]) x r_cc[t+1] (bps); sign(5-day) x fc5; sign(20-day) x fo20.
- S4 cross-section by regime: daily-formed quintiles; 5-day return bottom minus top -> abnormal fo5 (short-term reversal);
  12-1 momentum top minus bottom -> abnormal fo20.
- S5 overnight r_on and intraday r_id (EW, bps) by regime.
- S6 range reliability: touch of the 20-day low (Low[t] <= min Low[t-20..t-1]): within the next 10 days, does High reach
  the 20-day mid first, or Low fall 1 ATR14 below the old low first (P(up first) - P(down first)); also fc10. Resistance
  analogue: touch of the 20-day high: new high + 1 ATR first vs back to mid first.
- S7 breakouts by regime: HHV20 Close breakout abnormal fo20; failure rate (Close back below the level within 3 days).
- S8 volatility squeeze: own 20-day volatility in the bottom decile of its trailing 250 days -> |fo20| and abnormal fo20.
- S9 volume spike on an up day (V >= 3 x 20-day mean, r_cc > 0) -> abnormal fo20 by regime.
- S10 characteristics on sideways days: beta (60-day vs EW index) and liquidity terciles, top minus bottom abnormal fo20.
- S11 what predicts the exit from sideways: within sideways days, breadth (share of eligible stocks above SMA50) >= 60%
  minus < 40%, and EW proxy above minus below its SMA200 -> EW forward 20-day return.
Robust in sideways = |t| >= 3 on sideways days, BH q <= 5% over all primary sideways statistics, same sign in >= 3 of 4
subperiods. Usable for a long-only logic = the per-trade effect it implies is above the 0.90% round-trip cost (B).
Survivorship caveat: survivors-only data (delisted stocks missing) flatter dip-buying and illiquid-stock effects.
