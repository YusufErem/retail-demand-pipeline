import datetime as dt

import pytest


@pytest.fixture(scope="session")
def spark():
    from retail_pipeline.transform import get_spark
    s = get_spark("tests")
    yield s
    s.stop()


@pytest.fixture
def raw(spark):
    """Two weeks of transactions with one example of every row the cleaning must drop."""
    t = lambda d, h=10: dt.datetime(2011, 3, d, h)          # 2011-03-07 is a Monday  # noqa: E731
    rows = [
        ("500001", "85123A", "WHITE HEART", 6, t(7), 2.55, "13085", "United Kingdom"),
        ("500001", "85123A", "WHITE HEART", 6, t(7), 2.55, "13085", "United Kingdom"),   # exact duplicate
        ("500002", "22423", "CAKESTAND", 2, t(8), 12.75, None, "France"),                # no customer: kept
        ("C500003", "22423", "CAKESTAND", -1, t(9), 12.75, "13085", "United Kingdom"),   # cancellation
        ("500004", "22423", "CAKESTAND", 0, t(9), 12.75, "13085", "United Kingdom"),     # zero quantity
        ("500005", "84879", "BIRD ORNAMENT", 3, t(10), 0.0, "12583", "France"),          # zero price
        ("500006", "POST", "POSTAGE", 1, t(10), 18.0, "12583", "France"),                # fee, not a product
        ("500007", "84879", "BIRD ORNAMENT", 8, t(15), 1.69, "12583", "France"),
        ("500008", "85123A", "WHITE HEART", 4, t(16), 2.95, "13085", "United Kingdom"),
    ]
    cols = ["invoice", "stock_code", "description", "quantity", "invoice_date", "price", "customer_id", "country"]
    return spark.createDataFrame(rows, cols)
