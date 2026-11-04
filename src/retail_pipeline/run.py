"""Run the whole pipeline without Airflow and print a short report:  python -m retail_pipeline.run"""
from __future__ import annotations

import time

import pandas as pd

from . import extract, export, forecast, quality, transform


def run_all() -> dict:
    t0 = time.time()
    raw = extract.extract()
    silver = transform.build_silver(raw)
    gold = transform.build_gold(silver["path"])
    checks = quality.run_checks(silver["path"], gold)
    bt = forecast.run_backtest(gold)
    counts = {k: v for k, v in silver.items() if k != "path"}
    files = export.export(gold, bt, counts)

    print(f"rows: {silver['raw_rows']:,} raw → {silver['clean_rows']:,} clean")
    for k, v in counts.items():
        if k.startswith("removed_"):
            print(f"  removed {k[8:].replace('_', ' ')}: {v:,}")
    print(f"quality checks: {sum(c['ok'] for c in checks)}/{len(checks)} passed")
    summary = pd.read_parquet(bt["backtest_summary"])
    print(f"forecast backtest (top {len(bt['top_skus'])} A-class products, one week ahead, WAPE):")
    for _, r in summary.iterrows():
        print(f"  {r['method']:<32} {r['wape']:.3f}")
    print(f"tableau extracts: {len(files)} CSV files · {time.time() - t0:.0f} s")
    return {"silver": silver, "gold": gold, "checks": checks, "backtest": bt, "files": files}


if __name__ == "__main__":
    run_all()
