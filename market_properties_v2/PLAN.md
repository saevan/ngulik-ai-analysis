# Market properties v2: pre-registered plan (written 18 Oct 2026, before any v2 result)

Goal: find properties of the Kompas100 daily data that are real, stable and usable for our long-only IDX swing
systems (entry, ranking, exit, exposure). v1 (`market_property_results/`, 15 Oct) measured 9 properties without HAC
t-stats, multiple-testing control or survivorship checks; v2 re-tests them and adds new ones.

## Data and conventions (fixed)
- Panel: `panel.py` (cache `cache/panel.pkl`, not committed). 100 current Kompas100 tickers, 1994-07-12..2025-08-15,
  adjusted OHLCV. Volume 0 = not tradable. Simple daily |return| >= 50% = data error / unadjusted action (123 cases):
  return NaN and jump removed from the clean log levels `lnP, lnO, lnH, lnL`. All level-based signals use clean levels.
- Signals use information up to the Close of day t. Default entry = Open of t+1 (stock tradable that day); h-day
  forward return `fo[h] = lnP[t+h] - lnO[t+1]` (log). Intraday stop entries are defined per test.
- Abnormal return = event return minus the same-day equal-weight mean of all universe stocks over the identical window.
- Periods: MAIN 2000-01-01..2025-08-15; subperiods P1 2000-07, P2 2008-15, P3 2016-20, P4 2021-25.
  P0 1994-99 (27-36 tickers, used only as warm-up by earlier portfolio backtests) is a secondary check, not a criterion.
- Universes: `all` (100) and `pre2018` (80; without the 20 tickers first listed 2018 or later).
- Market proxy: equal-weight daily simple return of the universe (`idx_ret`), NOT the IHSG (not in the data).
- Statistics (`mpstats.py`): event tests average per day first, then Newey-West t on the market-day series
  (lags = h for h-day windows, 5 for daily series); monthly sorts lags 2, weekly sorts lags 2.
  Group differences: t = (mA - mB)/sqrt(seA^2 + seB^2) (conservative). Units: % for multi-day windows, bps for daily.

## Pass criteria (applied to every primary test)
1. Significance: |NW t| >= 3.0 in MAIN (all universe) AND Benjamini-Hochberg q <= 0.05 across all primary tests.
2. Stability: same sign as MAIN in >= 3 of the 4 subperiods P1-P4.
3. Survivorship check: pre2018 universe, MAIN period: same sign and >= 50% of the MAIN magnitude.
4. Usability: standalone trade -> abnormal effect > round-trip cost B 0.90% (A 0.40% reported);
   filter/ranking inside an existing signal -> |difference| >= 0.25 pp per trade; timing -> net improvement in a
   simple exposure backtest after costs.
Classes: ROBUST_USABLE (1-4), ROBUST_NOT_USABLE_ALONE (1-3), REGIME_DEPENDENT (1 but not 2), NOT_SUPPORTED (fails 1).
Every test also carries a survivorship-risk label (low/medium/high): effects that favour losers, crashed or illiquid
stocks are high risk because delisted stocks are missing from the data.

## Primary tests (62). IDs are fixed; exploratory extras must use IDs starting with `X-` and are not classified.

### A. Time-series structure (owner: main session) - raw (not market-adjusted) returns
- A1.1 TSMOM(1,1): mean over stocks of sign(r_cc[t]) * fo[1]; bps; lags 5.
- A1.2 TSMOM(5,5): sign(lnP[t]-lnP[t-5]) * fo[5]; %; lags 5.
- A1.3 TSMOM(20,20): sign(lnP[t]-lnP[t-20]) * fo[20]; %; lags 20.
- A1.4 TSMOM(60,20): sign(lnP[t]-lnP[t-60]) * fo[20]; %; lags 20.
- A1.5 TSMOM(120 skip 20, 20): sign(lnP[t-21]-lnP[t-141]) * fo[20]; %; lags 20 (our mom120 definition).
- A1.6 TSMOM(250 skip 20, 20): sign(lnP[t-21]-lnP[t-252]) * fo[20]; %; lags 20.
- A1.7 Index AC1: OLS slope of idx_ret[t+1] on idx_ret[t]; lags 5.
- A1.8 Index TSMOM(20,20): sign(20-day log return of the idx_ret index) * (EW mean of fo[20]); %; lags 20.

### B. Overnight, intraday and gaps (owner: main session)
- B1 Mean overnight log return r_on (EW over stocks, per day); bps.
- B2 Mean intraday log return r_id (EW over stocks, per day); bps.
- B3 Gap up (r_on > ln 1.02): same-day abnormal intraday return (r_id minus same-day EW mean r_id); bps.
- B4 Gap down (r_on < ln 0.98): same-day abnormal intraday return; bps.
- B5 Gap up > 2%: abnormal fo[5] (entry next Open); %.
- B6 Gap down < -2%: abnormal fo[5]; %.

### C. Calendar (owner: main session) - idx_ret, dummy regressions, lags 5, bps/day
- C1 Turn of month (last trading day + first 3 trading days) minus other days.
- C2 Monday minus other days.  C3 Friday minus other days.
- C4 December minus other months.  C5 January minus other months.
- C6 Pre-Lebaran: the 5 trading days ending at the last trading day before each year's longest closure (closures that
  include any date Dec 24 - Jan 2 excluded; ties -> earliest) minus other days.  C7 Post-Lebaran: the first 5
  trading days after that closure minus other days.
- C8 Pre-holiday: last trading day before a closure of >= 1 weekday minus other days.

### D. Cross-sectional sorts (owner: main session) - month-end Close, quintiles, hold next Open -> next month-end
Close, Q5 (highest signal) minus Q1, %/month, lags 2, >= 25 stocks; D5 is weekly (%/week).
- D1 MOM12-1 lnP[t-21]-lnP[t-252].  D2 MOM6-1 lnP[t-21]-lnP[t-141].  D3 MOM3-1 lnP[t-21]-lnP[t-84].
- D4 REV1M lnP[t]-lnP[t-21].  D5 REV1W lnP[t]-lnP[t-5] (weekly rebalance).
- D6 52-week-high proximity lnP[t] - max(lnH[t-251..t]).
- D7 Volatility: std of r_cc over 60 days (>= 40 obs).  D8 MAX: max r_cc over 21 days.
- D9 Amihud: mean(|simple return| / traded value) over 60 days (>= 40 obs).  D10 Liquidity: log mean traded value 60 days.
- D11 Signed ER60: (lnP[t]-lnP[t-60]) / sum(|daily lnP change|, 60).
- D12 Beta: 60-day OLS beta of r_cc on log(1+idx_ret) (>= 40 obs).
(Price-level effects are not tested: adjusted prices are not the historical traded prices.)

### W1. Breakout anatomy (owner: workflow agent) - clean levels, abnormal fo[20] unless stated, %, lags 20
- W1.1 HHV20 Close breakout: lnP[t] > max(lnH[t-20..t-1]).  W1.2 HHV55.  W1.3 HHV120.  W1.4 HHV250.
- W1.5 Intraday buy stop: L = max(lnH[t-20..t-1]); trigger lnH[t] >= L + ln(1.005); entry lnE = max(lnO[t], L+ln1.005);
  return lnP[t+19] - lnE minus same-day EW mean of lnP[t+19] - lnO[t] over all stocks (20-day window from day t).
- W1.6 Among W1.1 events: volume V[t] >= 2 x mean(V[t-20..t-1]) minus < 2x (difference).
- W1.7 Among W1.1 events: ER20 >= 0.3 minus < 0.3; ER20 = |lnP[t]-lnP[t-20]| / sum(|daily lnP change|, 20).
- W1.8 Among W1.1 events: idx level (cumulative idx_ret) above its SMA200 minus below.
- W1.9 Among W1.5 triggers: lnO[t] >= L + ln(1.02) (gapped >= 2% over the level) minus the rest; returns as in W1.5.
- W1.10 Failed breakout: W1.1 event with level L; first day f in t+1..t+3 with lnP[f] < L; abnormal fo[20] from
  the Open after f (Mean).

### W2. Trade path (owner: workflow agent) - entry: W1.1 event with ER20 >= 0.2, buy at lnO[t+1]
- W2.1 u5 = lnP[t+5]-lnO[t+1]; later return z = lnP[t+60]-lnO[t+6]; z(u5 >= +5%) minus z(u5 <= -5%); %; lags 20.
- W2.2 Same at day 20: u20 = lnP[t+20]-lnO[t+1]; z = lnP[t+60]-lnO[t+21].
- W2.3 Trades whose Close-based gain first reaches >= +10% within 20 days at day g: abnormal return from lnO[g+1]
  to lnP[t+60] (Mean, abnormal vs same window EW mean).
- W2.4 Per-day abnormal drift in days 21-60 after entry: (abnormal lnP[t+60]-lnP[t+20]) / 40, in bps/day (Mean).
- W2.5 Same entries, exit comparison: trailing exit (first Close < min(lnL over prior 10 bars), sell next Open; cap
  at 120 bars) minus fixed 20-bar hold (sell at lnP[t+20]); paired per-trade difference; %; lags 20.

### W3. Market regime and volatility timing (owner: workflow agent) - idx = equal-weight proxy of the universe;
forward = EW mean of fo[20] (or fo[60]) across stocks; Dummy regressions unless stated
- W3.1 Volatility clustering: OLS slope of |idx_ret[t+1]| on |idx_ret[t]|; lags 5.
- W3.2 20-day realised idx vol in its top tercile minus bottom tercile (expanding-window thresholds known at t,
  >= 500 days history; middle tercile excluded) -> forward 20-day; %; lags 20.
- W3.3 Vol targeting: exposure = min(1.5, expanding median(sigma20)/sigma20[t]) applied to idx_ret[t+1] vs constant
  exposure 1; difference in annualised Sharpe with 20-day block bootstrap (2,000 resamples); also MDD.
- W3.4 idx above its SMA200 minus below -> forward 20-day; %; lags 20.
- W3.5 Breadth: share of stocks with lnP > SMA50(lnP) >= 60% minus < 40% -> forward 20-day; %; lags 20.
- W3.6 idx drawdown from running max < -25% minus others -> forward 60-day; %; lags 60.
- W3.7 Lead-lag: OLS slope of small-cap EW fo[1] at t+1... i.e. EW fo[1] of bottom-tercile stocks (60-day mean traded
  value, formed monthly) on large-cap (top tercile) EW r_cc at t; lags 5.

### W4. Extreme events and liquidity shocks (owner: workflow agent) - abnormal returns from next Open
- W4.1 Strong close at high: r_cc >= ln 1.15 and Close = High -> abnormal fo[5]; %; lags 5.
- W4.2 Weak close at low: r_cc <= ln 0.85 and Close = Low -> abnormal fo[5]; %; lags 5.
- W4.3 Volume spike up: V >= 3 x mean(V[t-20..t-1]) and r_cc > 0 -> abnormal fo[20]; %; lags 20.
- W4.4 Volume spike down: same with r_cc < 0 -> abnormal fo[20].
- W4.5 Run-up: lnP[t]-lnP[t-20] >= ln 1.5 -> abnormal fo[20].
- W4.6 Crash: lnP[t]-lnP[t-20] <= ln(1/1.5) -> abnormal fo[20] (survivorship risk high).

## Process
1. This plan, `panel.py`, `mpstats.py` and `test_mpstats.py` are committed before any test is run.
2. Families A-D are run in the main session; W1-W4 by workflow agents. Each W family is re-derived by an independent
   adversarial verifier with its own code; A-D are verified the same way afterwards.
3. BH q-values are computed over all 62 primary tests at the end; classification follows the criteria above.
4. Properties that pass are hypotheses for system levers; turning them into rules needs a separate pre-registered
   portfolio test. No AFL is changed.
