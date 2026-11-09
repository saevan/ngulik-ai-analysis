"""User claim check: win rate ~50% is fine when average win > average loss (plan addendum in swinger_fingerprint_results)."""
from pathlib import Path
import pandas as pd
OUT = Path(__file__).resolve().parent / 'swinger_fingerprint_results'
E = pd.read_csv(OUT / 'trades.csv.gz')
rows = []
for basis, col in [('as traded (ideal fill)', 'net'), ('Close-to-Close', 'c2c_net')]:
    for g, x in list(E.groupby('regime')) + [('all', E)]:
        r = x[col]; w = r > 0; W, L = r[w].mean(), -r[~w].mean()
        rows.append(dict(basis=basis, regime=g, win_rate=w.mean(), avg_win_pct=W * 100, avg_loss_pct=-L * 100, payoff=W / L,
                         breakeven_wr=1 / (1 + W / L), expectancy_pct=r.mean() * 100, median_trade_pct=r.median() * 100))
R = pd.DataFrame(rows); R.to_csv(OUT / 'wr_payoff_check.csv', index=False)
pd.set_option('display.width', 200); print(R.round(3).to_string(index=False))
print(pd.DataFrame([dict(win_rate=p, payoff_needed=(1 - p) / p) for p in (.3, .4, .45, .5, .55)]).round(2).to_string(index=False))
