"""PySpark steps: clean the transactions (silver) and build the weekly demand, ABC and country tables (gold)."""
from __future__ import annotations

import os
import sys
import warnings

from pyspark.sql import DataFrame, SparkSession, Window
from pyspark.sql import functions as F

from . import config


def get_spark(app: str = "retail-demand-pipeline") -> SparkSession:
    # PySpark 4.3 warns about pandas 3; the pipeline never converts between Spark and pandas DataFrames.
    warnings.filterwarnings("ignore", message="PySpark does not yet fully support pandas")
    os.environ.setdefault("PYSPARK_PYTHON", sys.executable)          # workers use this interpreter, not the system one
    spark = (SparkSession.builder.master(os.environ.get("SPARK_MASTER", "local[*]")).appName(app)
             .config("spark.sql.session.timeZone", "UTC")
             .config("spark.sql.shuffle.partitions", "8")
             .config("spark.ui.enabled", "false")
             .config("spark.ui.showConsoleProgress", "false")
             .config("spark.driver.memory", os.environ.get("SPARK_DRIVER_MEMORY", "2g"))
             .getOrCreate())
    spark.sparkContext.setLogLevel("ERROR")
    return spark


# ═══════════════════════════ silver: clean transactions ═════════════════════
CLEANING_RULES = [
    ("exact_duplicates", lambda d: d.dropDuplicates()),
    ("cancellations", lambda d: d.filter(~F.col("invoice").startswith("C"))),
    ("non_positive_quantity", lambda d: d.filter(F.col("quantity") > 0)),
    ("non_positive_price", lambda d: d.filter(F.col("price") > 0)),
    ("non_product_codes", lambda d: d.filter(F.col("stock_code").rlike(config.PRODUCT_CODE))),
]


def clean(raw: DataFrame) -> tuple[DataFrame, dict]:
    """Apply the rules in order and count what each one removes. Rows without a customer ID are kept: the
    sale still happened, so it is still demand."""
    counts = {"raw_rows": raw.count()}
    df, before = raw, counts["raw_rows"]
    for name, rule in CLEANING_RULES:
        df = rule(df)
        after = df.count()
        counts[f"removed_{name}"], before = before - after, after
    counts["clean_rows"] = before
    df = (df.withColumn("revenue", F.round(F.col("quantity") * F.col("price"), 2))
            .withColumn("week", F.to_date(F.date_trunc("week", "invoice_date")))      # weeks start on Monday
            .withColumn("month", F.to_date(F.date_trunc("month", "invoice_date"))))
    return df, counts


# ═══════════════════════════ gold tables ═════════════════════════════════════
def weekly_demand(clean_df: DataFrame) -> DataFrame:
    """Units, revenue and orders per product and week. `complete` marks weeks fully inside the data period
    (the first and last weeks are cut by the extract dates)."""
    first_day, last_day = clean_df.agg(F.to_date(F.min("invoice_date")), F.to_date(F.max("invoice_date"))).first()
    return (clean_df.groupBy("stock_code", "week")
            .agg(F.sum("quantity").alias("units"), F.round(F.sum("revenue"), 2).alias("revenue"),
                 F.countDistinct("invoice").alias("orders"))
            .withColumn("complete", (F.col("week") >= F.lit(first_day)) &
                        (F.date_add("week", 6) <= F.lit(last_day))))


def abc_classes(clean_df: DataFrame, limits: tuple[float, float] = config.ABC_LIMITS) -> DataFrame:
    """Rank products by revenue. A product is A while the revenue before it is under 80% of the total, B under
    95%, otherwise C, so the product that crosses a limit stays in the higher class."""
    sku = clean_df.groupBy("stock_code").agg(
        F.round(F.sum("revenue"), 2).alias("revenue"), F.sum("quantity").alias("units"),
        F.mode("description").alias("description"))
    total = sku.agg(F.sum("revenue")).first()[0]
    w = Window.orderBy(F.desc("revenue"), "stock_code").rowsBetween(Window.unboundedPreceding, 0)
    sku = (sku.withColumn("cum_share", F.sum("revenue").over(w) / F.lit(total))
              .withColumn("share_before", F.col("cum_share") - F.col("revenue") / F.lit(total))
              .withColumn("rank", F.row_number().over(Window.orderBy(F.desc("revenue"), "stock_code"))))
    return sku.withColumn("abc_class", F.when(F.col("share_before") < limits[0], "A")
                          .when(F.col("share_before") < limits[1], "B").otherwise("C")).drop("share_before")


def country_month(clean_df: DataFrame) -> DataFrame:
    return (clean_df.groupBy("country", "month")
            .agg(F.round(F.sum("revenue"), 2).alias("revenue"), F.countDistinct("invoice").alias("orders"),
                 F.countDistinct("customer_id").alias("customers")))


# ═══════════════════════════ steps used by the DAG ═══════════════════════════
def build_silver(raw_path: str = str(config.RAW_PARQUET), out: str = str(config.SILVER_DIR / "transactions")) -> dict:
    spark = get_spark()
    df, counts = clean(spark.read.parquet(raw_path))
    df.write.mode("overwrite").partitionBy("month").parquet(out)
    return {"path": out, **counts}


def build_gold(silver_path: str = str(config.SILVER_DIR / "transactions"), out_dir: str = str(config.GOLD_DIR)) -> dict:
    spark = get_spark()
    df = spark.read.parquet(silver_path)
    paths = {}
    for name, table in (("weekly_demand", weekly_demand(df)), ("abc_classes", abc_classes(df)),
                        ("country_month", country_month(df))):
        paths[name] = f"{out_dir}/{name}"
        table.write.mode("overwrite").parquet(paths[name])
    return paths
