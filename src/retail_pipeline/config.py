"""Paths and constants. Override the folders with RETAIL_DATA_DIR and RETAIL_EXPORT_DIR."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.environ.get("RETAIL_DATA_DIR", ROOT / "data"))
EXPORT_DIR = Path(os.environ.get("RETAIL_EXPORT_DIR", ROOT / "tableau"))

RAW_DIR, SILVER_DIR, GOLD_DIR = DATA_DIR / "raw", DATA_DIR / "silver", DATA_DIR / "gold"
SOURCE_URL = "https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip"
SOURCE_ZIP = RAW_DIR / "online_retail_ii.zip"
RAW_PARQUET = RAW_DIR / "online_retail_ii.parquet"

# Product stock codes are five digits with an optional letter suffix (85123A); POST, DOT, M, BANK CHARGES,
# AMAZONFEE and similar codes are fees or adjustments, not products.
PRODUCT_CODE = r"^\d{5}[A-Za-z]{0,2}$"
ABC_LIMITS = (0.80, 0.95)          # A: first 80% of revenue, B: next 15%, C: the rest
TOP_SKUS = 50                      # A-class SKUs used for the forecast backtest and the dashboard
HOLDOUT_WEEKS = 12                 # rolling-origin backtest: one-week-ahead forecasts for the last 12 weeks
