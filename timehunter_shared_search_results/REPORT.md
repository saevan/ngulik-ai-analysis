# Shared TimeHunter ATR parameter search

{
  "searched": 1500,
  "both_forex_pass": 1,
  "all_four_pass": 1,
  "selected_config_id": 653,
  "selected_config": {
    "sma": 30,
    "high": 10,
    "hold": 200,
    "pull": 0.25,
    "fade": 5.0
  },
  "selection": "Exploratory same-data screening, not out-of-sample. Rank minimum numeric passes, minimum WR/payout margin, minimum N. No 7/7 claim.",
  "start": "2000-01-01",
  "costs": 0
}

Same architecture: Close>SMA, HHV-Close>=pull*previous ATR14, positive one-bar rebound; next tradable Open entry. Fading from each current Open by fade*previous ATR14; next tradable Open exit. Scheduled hold exit at Close; fees zero. All parameters identical across assets; no per-market optimization. Forex history only2023–2026, crypto2017–2025, stocks restricted2000–2025. Source-clock04:00 and00:00 forex sessions both screened.

Screening and ranking use already-observed full samples. Session variants share data, not independent replications. Common-date evaluation is a diagnostic, not untouched holdout. Small trade counts, correlated instruments, surviving crypto selection, unaudited corporate actions and uncertain forex timezone limit universality. Mean per trade, not annual/portfolio return. PF uses equal entry notional.

 market period    n       wr  avg_win  avg_loss    payout     mean    median  numeric_passes    margin     worst       p05  trimmed_mean        pf  fading_exits  period_end_exits
forex04   full   43 0.511628 0.041981  0.020086  2.090091 0.011669  0.000828               5  0.023256 -0.082166 -0.041564      0.009310  2.189619             8                 6
forex04 common   31 0.483871 0.038285  0.022511  1.700711 0.006906 -0.002576               3 -0.149644 -0.049272 -0.042762      0.003017  1.594417             4                 9
forex00   full   47 0.574468 0.042982  0.018685  2.300353 0.016741  0.007928               5  0.148936 -0.099043 -0.044219      0.014372  3.105477             6                 8
forex00 common   33 0.666667 0.031245  0.025841  1.209130 0.012216  0.011825               4 -0.395435 -0.099043 -0.040457      0.008674  2.418260             3                 8
 stocks   full 2098 0.535748 0.578212  0.216924  2.665501 0.211136  0.029754               5  0.071497 -0.827586 -0.443623      0.151959  3.140485           237                98
 stocks common  301 0.435216 0.380835  0.188397  2.021448 0.061219 -0.029703               4 -0.129568 -0.567708 -0.402597      0.026844  1.585686             7                98
 crypto   full  106 0.547170 4.754338  0.318450 14.929637 2.457227  0.066118               5  0.094340 -0.770717 -0.637585      0.671337 18.039978             9                 8
 crypto common   34 0.676471 0.745268  0.185264  4.022728 0.444213  0.268973               5  0.352941 -0.361178 -0.346453      0.331061  8.411159             2                 8

## Ledger audit and sensitivity

All four full-history ledgers independently re-scored:5/5 each. See robustness.csv for exclusion of terminal closures and top1% returns. Crypto has a DOGE winner of approximately+16,939%; PF is strongly affected by extreme returns. No independent/unseen validation has been performed. Candidate AFL: TimeHunter_ATR_Shared_Candidate.afl; main AFL unchanged. AmiBroker compilation/execution not performed.
