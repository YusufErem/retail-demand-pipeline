"""
### Retail demand pipeline

Weekly run over the UCI Online Retail II transactions:

1. **extract**: download the workbook once, store both sheets as Parquet
2. **build_silver**: PySpark cleaning (duplicates, cancellations, non-positive quantity or price, non-product codes)
3. **build_gold**: weekly demand per product, ABC classes, revenue by country and month
4. **quality_checks**: stop the run if any check fails, so a broken table never reaches the dashboard
5. **forecast_backtest**: one-week-ahead backtest of simple methods on the top A-class products
6. **export_tableau**: CSV extracts for the Tableau Public dashboard
"""
from __future__ import annotations

from datetime import datetime, timedelta

try:                                   # Airflow 3
    from airflow.sdk import dag, task
except ImportError:                    # Airflow 2.x
    from airflow.decorators import dag, task


@dag(dag_id="retail_demand_pipeline", schedule="@weekly", start_date=datetime(2026, 11, 2), catchup=False,
     default_args={"retries": 1, "retry_delay": timedelta(minutes=5)}, tags=["retail", "pyspark"], doc_md=__doc__)
def retail_demand_pipeline():
    # heavy imports stay inside the tasks, so the scheduler parses this file quickly

    @task
    def extract() -> str:
        from retail_pipeline import extract as step
        return step.extract()

    @task
    def build_silver(raw_path: str) -> dict:
        from retail_pipeline import transform
        return transform.build_silver(raw_path)

    @task
    def build_gold(silver: dict) -> dict:
        from retail_pipeline import transform
        return transform.build_gold(silver["path"])

    @task
    def quality_checks(silver: dict, gold: dict) -> list:
        from retail_pipeline import quality
        return quality.run_checks(silver["path"], gold)

    @task
    def forecast_backtest(gold: dict, checks: list) -> dict:
        from retail_pipeline import forecast
        return forecast.run_backtest(gold)

    @task
    def export_tableau(gold: dict, backtest: dict, silver: dict) -> dict:
        from retail_pipeline import export
        return export.export(gold, backtest, {k: v for k, v in silver.items() if k != "path"})

    silver = build_silver(extract())
    gold = build_gold(silver)
    backtest = forecast_backtest(gold, quality_checks(silver, gold))
    export_tableau(gold, backtest, silver)


retail_demand_pipeline()
