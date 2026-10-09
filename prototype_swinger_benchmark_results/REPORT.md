# Prototype Swinger benchmark

{
  "source_original": "C:\\Program Files (x86)\\AmiBroker\\Formulas\\Custom\\prototype swinger.afl",
  "source_sha256": "d7f4edf5567d10704b5f111e0ff39768bb48851a6e98c4ae478a24b2b8ce4708",
  "swing": 5,
  "capital": 1000000000.0,
  "max_positions": 10,
  "sizing": "10% prior-close equity, includes buy fee, cash constrained; alphabetical priority; fractional units",
  "start": "2000-01-01",
  "fee_buy": 0.0015,
  "fee_sell": 0.0025,
  "not_actual_amibroker_run": true
}

Source is installed AmiBroker original; matching Downloads/Test Algo copy. Other discovered versions change delays/fees or add averaging-down and are not used. MACD/RSI/Stoch calculations only affect chart color; final Buy/Sell are Cross(C,tsl) and Cross(tsl,C). Earlier Buy=Cross(C,res) is overwritten. No TimeHunter hold/fading/ER rules imported.

res=HHV(High,5);sup=LLV(Low,5). Last nonzero directional event is Close>prior res =>+1, Close<prior sup =>-1. tsl=sup when last direction+1 else res. Original ideal fill is prior tsl on SAME BAR as Close-confirmed crossover. Mode afl_ideal reproduces that explicit level without price-bound clamping or gap correction. It is an optimistic/look-ahead benchmark, not executable causally. Counts of fills outside daily range are saved. Original file does not define external Analysis trade delays/price-bound settings; this is a clearly specified Python interpretation, not AmiBroker-native replication.

stop_order comparator changes confirmation to intraday prior-level touch: flat and priorClose<=priorTSL arms buy-stop, trigger High>priorTSL, buy max(Open,priorTSL); long sell-stop triggers Low<priorTSL, sell min(Open,priorTSL). Stop level known before bar. Newly bought positions have no same-bar stop (OHLC sequencing unresolved); existing positions can exit. Intraday sale proceeds/slots conservatively not reused until next bar. Recompute TSL at each completed Close. Volume-zero triggers are skipped, not fabricated fills.

next_open comparator keeps original Close crossover signals and executes next observed tradable signal bar Open; zero-volume signal days skipped. No Close fill except forced last-data liquidation. This comparator changes only signal execution timing, not the indicator rules.

Same100stock data,2000–2025, ten allocations with compounding. Ideal fills omit spread/tick/round-lot adjustments on purpose; net variants keep user-approved0.15%/0.25% all-in fees. Mark open positions at closing prices less estimated exit fee; estimates are not charged repeatedly. Price-bound rules/auto-rejection/orderbook/liquidity/corporate actions not verified. Huge compounding returns on adjusted historical universe cannot be assumed achievable.

Record month: at least one daily portfolio equity above all preceding daily equity and initial capital. Includes partial edge months. Never resets at trade or regime boundaries.

         variant  rejected  outside_bar_fills  gap_fills    n       wr   payout  money_pf  final_equity     cagr       mdd  record_months  months  fraction_record_months  numeric_passes   total_fees
 afl_ideal_gross     11509                964          0 3241 0.532243 4.837406  3.049130  1.118420e+18 1.255731 -0.170085            262     308                0.850649               5 0.000000e+00
   afl_ideal_net     11509                964          0 3241 0.518976 5.172968  2.634814  3.181764e+17 1.147693 -0.188097            249     308                0.808442               5 4.498079e+16
stop_order_gross     17812                  0       5130 7267 0.312646 3.453394  1.396951  1.411231e+13 0.452158 -0.430475            144     308                0.467532               4 0.000000e+00
  stop_order_net     17815                  0       5129 7266 0.291908 3.799597  1.192173  8.697136e+11 0.302456 -0.496668            102     308                0.331169               4 9.651050e+11
 next_open_gross     11076                  0          0 3086 0.350940 2.981226  1.155255  4.698506e+11 0.271517 -0.509615             96     308                0.311688               4 0.000000e+00
   next_open_net     11076                  0          0 3086 0.343811 2.962964  1.106711  1.470514e+11 0.215137 -0.555158             83     308                0.269481               4 1.411725e+11

## Same-fee comparison against previous breakout ER module

                              variant    n     cagr       mdd  record_months  months  fraction_record_months
                        afl_ideal_net 3241 1.147693 -0.188097            249     308                0.808442
                       stop_order_net 7266 0.302456 -0.496668            102     308                0.331169
                        next_open_net 3086 0.215137 -0.555158             83     308                0.269481
breakout_ER_same_fees_ideal_reference  340 0.334331 -0.563257            127     308                0.412338

Same capital,10slots,compounding and0.15%/0.25% fees, no spread or lot rounding. Literal ideal is not causal. Four dedicated tests and all ledger/cash checks passed.
