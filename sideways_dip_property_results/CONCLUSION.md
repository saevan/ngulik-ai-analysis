# Second logic step 1: buy a dip of a strong stock at the Close in sideways markets, sell at an Open (20 Oct 2026)

Plan first (`PLAN.md`); code `sideways_dip_property.py`; exploratory `sideways_dip_explore.py` (360 cells) and
`sideways_dip_holdout_1994.py`; independent verification `verify_sideways_dip.py` (all numbers reproduced, no look-ahead).

Pre-registered result (realistic universe, market sideways, Close > SMA200, Close in bottom 20% of the 10-day range,
buy Close t, sell Open t+h): FAILS.
- Gross peaks at h=4: +0.34% per trade (t 2.8); net of cost B -0.56% (t -4.7); negative in every subperiod at every h.
- Direction is right: strong-stock dips beat weak-stock dips by +0.25 pp at h4 (+0.64 pp at h10), and Close->Open beats
  Open->Open by about 0.2 pp (overnight property). The edge is about a third of the cost.
- Also fails with exit at the Close, with cost A (best -0.06%), with simple instead of log returns (net B -0.43%), and
  under the other three pre-registered dip/sideways definitions.

Exploratory lead (not established): stock ER20 < 0.3, 120-day momentum in the day's top quintile, Close >= 4 ATR below the
10-day high, buy Close, sell Open 9 days later: +0.84% net (t 0.9, 307 trades in 25 years, all 4 subperiods positive);
1994-99 +0.96% (t 0.4, 69 trades). Fragile: momentum ranked within the eligible universe gives 1994-99 -0.70%; the 1994-99
average comes from 1999 alone; with the signal taken one day earlier (fully executable) 2000-25 drops to +0.48%; best of
360 cells. The survivor-only data flatters dip buying, so the true figure is likely lower.

Conclusion: in this data a sideways 'buy the dip, hold a few days' second logic does not beat costs. AFL unchanged.
