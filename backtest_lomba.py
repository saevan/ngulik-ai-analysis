"""Backtest dua sistem investasi berbasis waktu untuk lomba.

Aturan eksekusi dibuat eksplisit dan bebas look-ahead:

1. TimeHunter
   Beli pada open, tahan tepat 50 bar, jual pada close bar ke-50.

2. RecoverHunter
   Beli pada open. Jika High menyentuh entry + 1%, jadikan itu sinyal recovery
   dan jual pada open berikutnya. Jika sinyal belum muncul, jual pada close
   bar ke-50.

Setiap ticker memakai satu posisi pada satu waktu. Setelah posisi ditutup,
siklus berikutnya dimulai pada open bar berikutnya. Hasil bersifat gross,
sebelum fee, pajak, slippage, dan pembatasan likuiditas.
"""

from __future__ import annotations

import os
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

DATA_DIR = r"C:\Users\ACER\OneDrive\Documents\Ngulik AI\Data"
DATA_FILE = os.path.join(DATA_DIR, "Data kompas 100.csv")
HOLD_BARS = 50
RECOVERY_TARGET = 0.01


def load_stocks() -> pd.DataFrame:
    df = pd.read_csv(DATA_FILE)
    df.columns = [column.strip() for column in df.columns]
    df["Date/Time"] = pd.to_datetime(
        df["Date/Time"], format="mixed", dayfirst=True
    )
    df = df.sort_values(["Ticker", "Date/Time"]).reset_index(drop=True)

    required = {"Ticker", "Date/Time", "Open", "High", "Low", "Close"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Kolom data tidak lengkap: {sorted(missing)}")

    price_columns = ["Open", "High", "Low", "Close"]
    non_positive = (df[price_columns] <= 0).any(axis=1)
    if non_positive.any():
        raise ValueError(
            f"Ditemukan {int(non_positive.sum())} bar dengan harga non-positif"
        )

    # Vendor data contains a handful of bars where Open/Close falls just
    # outside the reported High-Low range. Preserve Open and Close (the actual
    # execution fields) and expand the range to contain all four OHLC values.
    inconsistent = (
        (df["High"] < df[["Open", "Close"]].max(axis=1))
        | (df["Low"] > df[["Open", "Close"]].min(axis=1))
    )
    if inconsistent.any():
        print(
            f"Normalizing {int(inconsistent.sum())} inconsistent OHLC bars."
        )
        df["High"] = df[price_columns].max(axis=1)
        df["Low"] = df[price_columns].min(axis=1)

    return df


def _trade_record(
    df: pd.DataFrame,
    entry_bar: int,
    exit_bar: int,
    exit_price: float,
    exit_reason: str,
) -> dict:
    entry_price = float(df.at[entry_bar, "Open"])
    return {
        "entry_date": df.at[entry_bar, "Date/Time"],
        "exit_date": df.at[exit_bar, "Date/Time"],
        "entry_price": entry_price,
        "exit_price": float(exit_price),
        "pnl_pct": (float(exit_price) - entry_price) / entry_price,
        "bars_held": exit_bar - entry_bar + 1,
        "exit_reason": exit_reason,
    }


def timehunter_strategy(df: pd.DataFrame, hold_bars: int = HOLD_BARS) -> pd.DataFrame:
    """Entry open; exit close after exactly ``hold_bars`` bars."""
    df = df.reset_index(drop=True)
    trades = []
    entry_bar = 0

    while entry_bar + hold_bars <= len(df):
        exit_bar = entry_bar + hold_bars - 1
        trades.append(
            _trade_record(
                df,
                entry_bar,
                exit_bar,
                float(df.at[exit_bar, "Close"]),
                "time_exit",
            )
        )
        entry_bar = exit_bar + 1

    return pd.DataFrame(trades)


def recoverhunter_strategy(
    df: pd.DataFrame,
    hold_bars: int = HOLD_BARS,
    recovery_target: float = RECOVERY_TARGET,
) -> pd.DataFrame:
    """Entry open; recovery signal exits next open, else exit at time limit."""
    df = df.reset_index(drop=True)
    trades = []
    entry_bar = 0

    while entry_bar + hold_bars <= len(df):
        entry_price = float(df.at[entry_bar, "Open"])
        target_price = entry_price * (1.0 + recovery_target)
        deadline = entry_bar + hold_bars - 1

        # A signal on the deadline cannot exit at the next open without
        # violating the 50-bar maximum, so only scan through deadline - 1.
        window_highs = df.loc[entry_bar:deadline - 1, "High"].to_numpy()
        hits = np.flatnonzero(window_highs >= target_price)

        if hits.size:
            signal_bar = entry_bar + int(hits[0])
            exit_bar = signal_bar + 1
            exit_price = float(df.at[exit_bar, "Open"])
            exit_reason = "recovery_next_open"
        else:
            exit_bar = deadline
            exit_price = float(df.at[exit_bar, "Close"])
            exit_reason = "time_exit"

        trades.append(
            _trade_record(df, entry_bar, exit_bar, exit_price, exit_reason)
        )
        entry_bar = exit_bar + 1

    return pd.DataFrame(trades)


def summarize(df: pd.DataFrame, name: str, round_trip_cost: float = 0.0) -> dict:
    pnl = df["pnl_pct"] - round_trip_cost
    wins = pnl[pnl > 0]
    losses = pnl[pnl <= 0]
    total = len(pnl)
    win_rate = len(wins) / total
    avg_win = float(wins.mean()) if len(wins) else 0.0
    avg_loss = abs(float(losses.mean())) if len(losses) else 0.0
    payout = avg_win / avg_loss if avg_loss > 0 else float("inf")
    mean = float(pnl.mean())
    median = float(pnl.median())

    criteria = {
        "mean > median": mean > median,
        "avg win > avg loss": avg_win > avg_loss,
        "payout > 2": payout > 2,
        "win rate > 50%": win_rate > 0.50,
        "expectancy > 0": mean > 0,
        "price + time only": True,
        "executable prices": True,
    }

    return {
        "name": name,
        "trades": total,
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": win_rate,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "payout": payout,
        "mean": mean,
        "median": median,
        "sum_pnl": float(pnl.sum()),
        "passes": sum(criteria.values()),
        "criteria": criteria,
    }


def collect_trades(stocks: pd.DataFrame, strategy, **kwargs) -> pd.DataFrame:
    frames = []
    for ticker, ticker_df in stocks.groupby("Ticker", sort=False):
        trades = strategy(ticker_df, **kwargs)
        if not trades.empty:
            trades["ticker"] = ticker
            frames.append(trades)
    if not frames:
        raise RuntimeError("Tidak ada transaksi yang dihasilkan")
    return pd.concat(frames, ignore_index=True)


def print_summary(summary: dict) -> None:
    print("\n" + "=" * 72)
    print(summary["name"])
    print("=" * 72)
    print(f"Trades            : {summary['trades']:,}")
    print(f"Wins / losses     : {summary['wins']:,} / {summary['losses']:,}")
    print(f"Win rate          : {summary['win_rate']:.2%}")
    print(f"Average win       : {summary['avg_win']:+.4%}")
    print(f"Average loss      : {-summary['avg_loss']:.4%}")
    print(f"Payout ratio      : {summary['payout']:.4f}")
    print(f"Mean / trade      : {summary['mean']:+.4%}")
    print(f"Median / trade    : {summary['median']:+.4%}")
    print(f"Sum of trade PnL  : {summary['sum_pnl']:+.2%}")
    print(f"Criteria          : {summary['passes']}/7")
    for criterion, passed in summary["criteria"].items():
        print(f"  [{'PASS' if passed else 'FAIL'}] {criterion}")


def main() -> None:
    print("Loading market data...")
    stocks = load_stocks()
    print(
        f"Loaded {len(stocks):,} bars across "
        f"{stocks['Ticker'].nunique()} tickers."
    )

    time_trades = collect_trades(
        stocks, timehunter_strategy, hold_bars=HOLD_BARS
    )
    recovery_trades = collect_trades(
        stocks,
        recoverhunter_strategy,
        hold_bars=HOLD_BARS,
        recovery_target=RECOVERY_TARGET,
    )

    summaries = [
        summarize(time_trades, "SYSTEM A - TimeHunter (50-bar close)"),
        summarize(
            recovery_trades,
            "SYSTEM B - RecoverHunter (+1% signal, next open exit)",
        ),
    ]
    for summary in summaries:
        print_summary(summary)

    print("\n" + "=" * 72)
    print("HEAD-TO-HEAD")
    print("=" * 72)
    print(f"{'Metric':<20}{'TimeHunter':>18}{'RecoverHunter':>18}")
    print("-" * 72)
    left, right = summaries
    rows = [
        ("Trades", f"{left['trades']:,}", f"{right['trades']:,}"),
        ("Win rate", f"{left['win_rate']:.2%}", f"{right['win_rate']:.2%}"),
        ("Payout", f"{left['payout']:.2f}", f"{right['payout']:.2f}"),
        ("Mean / trade", f"{left['mean']:+.2%}", f"{right['mean']:+.2%}"),
        ("Median / trade", f"{left['median']:+.2%}", f"{right['median']:+.2%}"),
        ("Criteria", f"{left['passes']}/7", f"{right['passes']}/7"),
    ]
    for metric, value_a, value_b in rows:
        print(f"{metric:<20}{value_a:>18}{value_b:>18}")

    print("\nExecution model:")
    print("- One open position per ticker; cycles do not overlap.")
    print("- A +1% intraday recovery signals an exit at the next open.")
    print("- Results are gross and exclude all trading costs.")


if __name__ == "__main__":
    main()
