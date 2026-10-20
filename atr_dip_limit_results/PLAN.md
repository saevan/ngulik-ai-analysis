# Bounce after a drop of more than x ATR, bought with a buy limit (20 Oct 2026, written before results)

Order: before the Open of day t, a buy limit at L = Close[t-1] - x * ATR14 (Wilder, through t-1). Fill if Low[t] < L
(price trades through the limit; touch-only fills reported as sensitivity); fill price = min(Open[t], L).
x in {1, 1.5, 2, 3}. Exits measured: Close t (same day), Open t+1, Close t+1, Close t+5, Close t+20.
Returns from the fill price on the clean log levels of market_properties_v2/panel.py; cost B = 0.90% round trip
(A = 0.40%). Universe: 'realistic' = stock liquid at the time (top half by 120-day traded value, >= 250 bars) and not
stale (>= 90% traded days, <= 10% one-price bars in the prior 60); also 'all'. Days with a data-error return excluded.
Stats: daily mean over that day's fills, Newey-West t (lags = horizon), periods 2000-25, 2000-07, 2008-15, 2016-20,
2021-25, market regime on the fill day (er20 definition), and a control: the same exits from that day's Open for the
same stocks (does the limit add anything over just buying at the Open?).
Usable = net of cost B > 0 with t >= 3 in 2000-25 and positive in at least 3 of the 4 subperiods; only then a portfolio test.
