"""Weekly demand forecast backtest for the top A-class products: simple methods, scored the way they would be used.

Rolling origin: for each of the last HOLDOUT_WEEKS complete weeks, every method forecasts that week using only the
weeks before it. Scores are pooled over products and weeks (WAPE = sum |error| / sum actual units).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config

METHODS = {
    "naive (last week)": lambda hist: hist[-1],
    "moving average (4 weeks)": lambda hist: hist[-4:].mean(),
    "moving average (8 weeks)": lambda hist: hist[-8:].mean(),
    "seasonal naive (52 weeks ago)": lambda hist: hist[-52] if len(hist) >= 52 else np.nan,
}


def weekly_matrix(weekly: pd.DataFrame, skus: list[str]) -> pd.DataFrame:
    """Complete weeks only; a product with no sale in a week gets 0 units."""
    w = weekly[weekly["complete"] & weekly["stock_code"].isin(skus)]
    weeks = pd.date_range(w["week"].min(), w["week"].max(), freq="7D")
    return (w.pivot_table(index="week", columns="stock_code", values="units", aggfunc="sum")
             .reindex(weeks).fillna(0.0).reindex(columns=skus, fill_value=0.0))


def backtest(units: pd.DataFrame, holdout: int = config.HOLDOUT_WEEKS) -> tuple[pd.DataFrame, pd.DataFrame]:
    """One-week-ahead forecasts for the last `holdout` weeks. Returns (summary by method, rows by product and week)."""
    rows = []
    n = len(units)
    for t in range(n - holdout, n):
        week = units.index[t]
        for sku in units.columns:
            hist, actual = units[sku].to_numpy()[:t], float(units[sku].iloc[t])
            for name, f in METHODS.items():
                rows.append({"week": week, "stock_code": sku, "method": name, "actual": actual,
                             "forecast": float(f(hist))})
    detail = pd.DataFrame(rows).dropna(subset=["forecast"])
    detail["abs_error"] = (detail["actual"] - detail["forecast"]).abs()
    summary = (detail.groupby("method")
               .agg(wape=("abs_error", "sum"), actual=("actual", "sum"), mae=("abs_error", "mean"),
                    bias=("forecast", "sum"), forecasts=("forecast", "size"))
               .assign(wape=lambda d: d["wape"] / d["actual"], bias=lambda d: d["bias"] / d["actual"] - 1)
               .drop(columns="actual").sort_values("wape").reset_index())
    return summary, detail


def run_backtest(gold: dict, out_dir: str = str(config.GOLD_DIR)) -> dict:
    abc = pd.read_parquet(gold["abc_classes"])
    weekly = pd.read_parquet(gold["weekly_demand"])
    weekly["week"] = pd.to_datetime(weekly["week"])
    top = abc[abc["abc_class"] == "A"].nsmallest(config.TOP_SKUS, "rank")["stock_code"].tolist()
    summary, detail = backtest(weekly_matrix(weekly, top))
    paths = {"backtest_summary": f"{out_dir}/backtest_summary.parquet", "backtest_detail": f"{out_dir}/backtest_detail.parquet"}
    summary.to_parquet(paths["backtest_summary"], index=False)
    detail.to_parquet(paths["backtest_detail"], index=False)
    return {**paths, "top_skus": top, "best_method": summary.iloc[0]["method"], "best_wape": float(summary.iloc[0]["wape"])}
