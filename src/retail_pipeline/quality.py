"""Data-quality checks. The pipeline stops when one fails, so a broken table never reaches the dashboard."""
from __future__ import annotations

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from . import config
from .transform import get_spark


class DataQualityError(RuntimeError):
    pass


def _check(name: str, ok: bool, detail: str) -> dict:
    return {"check": name, "ok": bool(ok), "detail": detail}


def check_tables(clean_df: DataFrame, weekly: DataFrame, abc: DataFrame) -> list[dict]:
    bad = clean_df.agg(
        F.sum((F.col("quantity") <= 0).cast("int")).alias("qty"), F.sum((F.col("price") <= 0).cast("int")).alias("price"),
        F.sum(F.col("invoice").startswith("C").cast("int")).alias("cancel"),
        F.sum((F.col("stock_code").isNull() | F.col("invoice_date").isNull()).cast("int")).alias("nulls"),
        F.sum((~F.col("stock_code").rlike(config.PRODUCT_CODE)).cast("int")).alias("codes"),
        F.sum("revenue").alias("revenue")).first()
    dup = weekly.groupBy("stock_code", "week").count().filter("count > 1").count()
    weekly_rev = weekly.agg(F.sum("revenue")).first()[0] or 0.0
    gap = abs(weekly_rev - bad["revenue"]) / max(abs(bad["revenue"]), 1e-9)
    classes = {r["abc_class"]: r["n"] for r in abc.groupBy("abc_class").agg(F.count("*").alias("n")).collect()}
    top_share = abc.agg(F.max("cum_share")).first()[0] or 0.0
    return [
        _check("no non-positive quantities", bad["qty"] == 0, f"{bad['qty']} rows"),
        _check("no non-positive prices", bad["price"] == 0, f"{bad['price']} rows"),
        _check("no cancellations", bad["cancel"] == 0, f"{bad['cancel']} rows"),
        _check("no missing keys", bad["nulls"] == 0, f"{bad['nulls']} rows"),
        _check("only product codes", bad["codes"] == 0, f"{bad['codes']} rows"),
        _check("one row per product and week", dup == 0, f"{dup} duplicated keys"),
        _check("weekly revenue reconciles with transactions", gap < 1e-6, f"relative gap {gap:.2e}"),
        _check("ABC classes A, B and C all present", set(classes) == {"A", "B", "C"}, str(classes)),
        _check("ABC cumulative share ends at 100%", abs(top_share - 1) < 1e-9, f"{top_share:.6f}"),
    ]


def run_checks(silver_path: str, gold: dict) -> list[dict]:
    spark = get_spark()
    results = check_tables(spark.read.parquet(silver_path), spark.read.parquet(gold["weekly_demand"]),
                           spark.read.parquet(gold["abc_classes"]))
    failed = [r for r in results if not r["ok"]]
    if failed:
        raise DataQualityError("; ".join(f"{r['check']} ({r['detail']})" for r in failed))
    return results
