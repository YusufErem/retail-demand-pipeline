"""Small CSV extracts for the Tableau Public dashboard (Tableau Public reads CSV files directly)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from . import config


def export(gold: dict, backtest: dict, counts: dict, out_dir: str = str(config.EXPORT_DIR)) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    abc = pd.read_parquet(gold["abc_classes"]).sort_values("rank")
    weekly = pd.read_parquet(gold["weekly_demand"])
    weekly = weekly[weekly["complete"]].drop(columns="complete")
    top = backtest["top_skus"]
    names = abc.set_index("stock_code")[["description", "abc_class"]]

    files = {
        "abc_products.csv": abc[["rank", "stock_code", "description", "abc_class", "revenue", "units", "cum_share"]],
        "weekly_top_products.csv": (weekly[weekly["stock_code"].isin(top)].join(names, on="stock_code")
                                    .sort_values(["stock_code", "week"])),
        "weekly_total.csv": (weekly.groupby("week", as_index=False)[["units", "revenue", "orders"]].sum()
                             .sort_values("week")),
        "country_month.csv": pd.read_parquet(gold["country_month"]).sort_values(["month", "revenue"],
                                                                                  ascending=[True, False]),
        "backtest_summary.csv": pd.read_parquet(backtest["backtest_summary"]),
        "backtest_detail.csv": pd.read_parquet(backtest["backtest_detail"]).join(names, on="stock_code"),
        "pipeline_kpis.csv": pd.DataFrame([{**counts, "products": len(abc),
                                            "a_class_products": int((abc["abc_class"] == "A").sum()),
                                            "best_method": backtest["best_method"],
                                            "best_wape": round(backtest["best_wape"], 4)}]),
    }
    for name, df in files.items():
        df.to_csv(out / name, index=False)
    return {name: str(out / name) for name in files}
