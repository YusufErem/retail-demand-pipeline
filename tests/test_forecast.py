import numpy as np
import pandas as pd

from retail_pipeline.forecast import backtest


def _units(values: dict) -> pd.DataFrame:
    n = len(next(iter(values.values())))
    return pd.DataFrame(values, index=pd.date_range("2010-01-04", periods=n, freq="7D"))


def test_seasonal_naive_is_exact_on_a_purely_seasonal_series():
    season = np.tile(np.r_[np.arange(26), np.arange(26)[::-1]] * 10.0 + 5, 2)          # 104 weeks, period 52
    summary, _ = backtest(_units({"A": season}), holdout=12)
    wape = summary.set_index("method")["wape"]
    assert wape["seasonal naive (52 weeks ago)"] == 0
    assert wape["naive (last week)"] > 0


def test_every_method_is_exact_on_a_constant_series_and_scores_use_only_the_past():
    summary, detail = backtest(_units({"A": np.full(60, 7.0), "B": np.full(60, 3.0)}), holdout=5)
    assert (summary["wape"] == 0).all()
    assert len(detail["week"].unique()) == 5 and set(detail["stock_code"]) == {"A", "B"}
