# Choppy-market diagnosis

Stocks 2000-01-04 to 2025-08-15. Initial Rp1 billion, ten slots, prior-close equity sizing with compounding. Buy fee 0.15%, sell fee 0.25%. Fee-only comparisons share cost assumptions with Swinger ideal. Additional tick scenario retains previous counterfactual modern IDX grid, 100-share lots and one tick each side; it is not reconstructed historical bid/ask.

Market regime: equal-weight available-stock return proxy, previous completed bar ER20 >= 0.30 with positive/negative 20-bar direction = up/down, otherwise sideways. Not IHSG. Entry filter uses individual stock ER, so sideways proxy does not imply every stock fails ER. Signal counts count all stock-bar opportunities, including already-held stocks and capacity-rejected signals; not executable trade counts. Actual entries are separately classified by entry-date market regime.

Daily equity attribution retains existing positions and never resets equity peaks. Conditional annualized returns concatenate noncontiguous regime days; they are NOT independently executable regime CAGRs. Whole-history annualized contributions reconcile multiplicatively to actual CAGR. Exposure and flat-day rates use daily closing snapshots, not intraday observations. Returns in sideways can arise from positions entered in other regimes.

No-filter control changes only ER entry gate; same breakout, hold200, fade5 prior ATR, ranking, sizing and costs. This tests removing the gate, NOT an unimplemented mean-reversion module. Results are in-sample and priority/universe dependent. Swinger literal ideal uses current Close signal with earlier level fills and contains 964 fills outside daily ranges; its gap is not a causal estimate of the benefit of sideways trading. Stop-order variant changes signal logic; next-open preserves original completed-close signals more closely.

Checks: prefix-causal regime labels, log-return/CAGR reconciliation and preservation of equity records. No live AFL changed.
