# Market properties in sideways markets (20 Oct 2026)

Plan first (`PLAN.md`); code `battery.py`; addendum `s6_random_walk_baseline.py` (written after seeing S6, superseded);
independent recomputation `verify_battery.py` (every number reproduced, no look-ahead); critic `critic_sideways.py/.csv`.
Realistic universe (liquid at the time, not stale), 2000-2025-08-15, regime = EW-proxy ER20 label from the previous Close.

What sideways markets look like here
- 56% of days (2000-07 47%, 2021-25 66%). Episodes are short: median 5 days, 90th percentile 22.
- Stocks move as much on sideways days as on uptrend days: mean |daily return| 1.9% vs 1.9%, ATR14 3.5% vs 3.3%.
  "Sideways" describes the index path, not quiet stocks. Lower cross-sectional dispersion existed mainly before 2016.
- Buying the EW market on sideways days earns about 0 over 20 days (-0.14%, t -0.3), whatever the episode age.
- The direction the market leaves sideways is not predictable: 63% of exits are 'uptrend', exactly the base rate of this
  survivor index (its +24%/yr drift); breadth and SMA200 do not predict it (z 1.4, 0.4).

Ranges do not behave like ranges
- After touching the 20-day low, price reaches the range mid first in 23% and falls 1 ATR lower first in 60%; at the
  20-day high, 62% / 23%. Against each stock's own bootstrapped paths over the same 10 days both are at chance (excess
  0 to -3 pp, |t| <= 1.6). The split is geometry (break level ~1 ATR away, mid ~2-2.6 ATR away) plus the horizon.
  (The 'support worse than chance' in the addendum used an infinite-horizon formula on 10-day-censored outcomes: wrong.)
- Level-to-level long trades lose about 0.25% per trade before costs.
- HHV20 breakouts in sideways: +0.33% vs market over 20 days (t 1.2); 45% close back below the level within 3 days.

Short-term dynamics
- Daily close-to-close continuation (+5.6 bps, t 3.6) is index-level autocorrelation, not specific to sideways, and gone:
  since 2021 stocks show a significant next-session reversal on all days (abnormal -6.7 bps, t -4.2); next-day intraday
  after a down day in sideways -11.4 bps.
- Since 2016 the overnight gain / intraday loss pattern holds on sideways days as on other days (overnight +14..+21 bps).
- 5-day reversal, 20-day trend sign, volatility squeeze, up-day volume spikes, beta and liquidity terciles: not
  significant on sideways days.

Implication for the second logic: no sideways property found here yields a short-horizon (5-20 day) long trade above the
0.90% cost. Sideways stocks move like random walks around a flat index; ranges neither hold nor break more than chance.
Leads, not established: 12-1 momentum top-quintile long leg held 60 days +1.7% abnormal (t 2.6, 4/4 subperiods; not
sideways-specific, survivorship-exposed); stocks trending on their own in a sideways market +0.8% over 20 days (t 2.1);
support right after a downtrend holds better than chance (+5.6 pp, t 2.7). Execution rule: buy at the Close, sell at the
Open. AFL unchanged.
