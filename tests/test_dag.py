from pathlib import Path

import pytest

DAGS = Path(__file__).resolve().parents[1] / "dags"


def test_dag_loads_with_the_expected_task_order(monkeypatch):
    monkeypatch.setenv("AIRFLOW__CORE__LOAD_EXAMPLES", "False")
    pytest.importorskip("airflow")
    from airflow.models.dagbag import DagBag
    bag = DagBag(dag_folder=str(DAGS))
    assert bag.import_errors == {}
    dag = bag.get_dag("retail_demand_pipeline")
    order = {t.task_id: sorted(t.upstream_task_ids) for t in dag.tasks}
    assert order == {"extract": [], "build_silver": ["extract"], "build_gold": ["build_silver"],
                     "quality_checks": ["build_gold", "build_silver"],
                     "forecast_backtest": ["build_gold", "quality_checks"],
                     "export_tableau": ["build_gold", "build_silver", "forecast_backtest"]}
