# Bounces when ER says the stock is choppy: descriptive distribution (13 Nov 2026, written before results)
User: "pada saat ER bilang sedang choppy berapa aja sih pantulan-pantulan yang ada itu?" Descriptive only, no rules.

Bounce = zigzag up-leg on Close (`sideways_swings.zigzag`) with reversal threshold X = 3% / 5% / 10%: from a swing
low L (confirmed on bar k when Close >= L x (1 + X)) to the next swing high H (confirmed when Close <= H x (1 - X)).
Each bounce is labelled at bar k (the first real-time moment the low is known) by:
- the stock's own ER20 bucket: < 0.1, 0.1-0.2, 0.2-0.3, >= 0.3 (choppy = < 0.2);
- the market label (`regime_proxy`): sideways or not.
Stocks must be eligible on bar k (realistic universe). Confirmations 2000-01-01..2025-08-15.

Reported per X and ER bucket (and for the Logic 2 state: stock ER20 < 0.2 and market sideways):
- bounces per stock-year (count / eligible stock-days in that bucket x 252);
- preceding drop (median), bounce size low -> high: p25 / median / p75 / p90, share >= 5% / 10% / 20%;
- bars low -> high (median); bounce in ATR14 units and relative to the 20-day range width (medians);
- share that recovers the previous swing high;
- real-time catch (Close at the low's confirmation -> Close at the high's confirmation): median, mean net of cost B,
  share positive after cost.
Plus a histogram of bounce sizes for X = 3% in choppy stocks (bins 3-5, 5-7, 7-10, 10-15, 15-20, > 20%) with
median duration and mean net catch per bin.
