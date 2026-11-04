import datetime as dt

import pytest
from pyspark.sql import functions as F

from retail_pipeline import transform
from retail_pipeline.quality import check_tables


def test_clean_drops_each_bad_row_and_counts_it(raw):
    clean, counts = transform.clean(raw)
    assert counts == {"raw_rows": 9, "removed_exact_duplicates": 1, "removed_cancellations": 1,
                      "removed_non_positive_quantity": 1, "removed_non_positive_price": 1,
                      "removed_non_product_codes": 1, "clean_rows": 4}
    assert clean.filter(F.col("customer_id").isNull()).count() == 1            # sales without a customer stay
    assert {r["week"] for r in clean.select("week").collect()} == {dt.date(2011, 3, 7), dt.date(2011, 3, 14)}


def test_weekly_demand_reconciles_and_flags_partial_weeks(raw):
    clean, _ = transform.clean(raw)
    weekly = transform.weekly_demand(clean)
    total = clean.agg(F.sum("revenue")).first()[0]
    assert weekly.agg(F.sum("revenue")).first()[0] == pytest.approx(total)
    flags = {(r["stock_code"], str(r["week"])): r["complete"] for r in weekly.collect()}
    # data runs 7-16 March: the week of 7 March is complete, the week of 14 March is cut on the 16th
    assert flags[("85123A", "2011-03-07")] is True and flags[("85123A", "2011-03-14")] is False


def test_abc_classes_follow_the_cumulative_revenue_limits(spark):
    rev = {"10001": 50.0, "10002": 30.0, "10003": 10.0, "10004": 5.0, "10005": 3.0, "10006": 2.0}
    rows = [(f"9{i}", sku, sku, 1, dt.datetime(2011, 3, 7), r) for i, (sku, r) in enumerate(rev.items())]
    df = spark.createDataFrame(rows, ["invoice", "stock_code", "description", "quantity", "invoice_date", "price"])
    df = df.withColumn("revenue", F.col("quantity") * F.col("price"))
    abc = {r["stock_code"]: r["abc_class"] for r in transform.abc_classes(df).collect()}
    # revenue share before each product: 0, .5, .8, .9, .95, .98 -> A, A, B, B, C, C
    assert abc == {"10001": "A", "10002": "A", "10003": "B", "10004": "B", "10005": "C", "10006": "C"}


def test_quality_checks_pass_on_clean_tables_and_catch_broken_ones(raw):
    clean, _ = transform.clean(raw)
    weekly, abc = transform.weekly_demand(clean), transform.abc_classes(clean)
    checks = {c["check"]: c["ok"] for c in check_tables(clean, weekly, abc)}
    assert all(v for k, v in checks.items() if k != "ABC classes A, B and C all present")
    broken = {c["check"]: c["ok"] for c in check_tables(raw.withColumn("revenue", F.col("quantity") * F.col("price")),
                                                        weekly.unionByName(weekly.limit(1)), abc)}
    assert not broken["no non-positive quantities"] and not broken["no cancellations"]
    assert not broken["only product codes"] and not broken["one row per product and week"]
    assert not broken["weekly revenue reconciles with transactions"]
