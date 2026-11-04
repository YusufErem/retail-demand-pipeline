"""Download the UCI Online Retail II workbook once and store both sheets as one Parquet file."""
from __future__ import annotations

import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

from . import config

COLUMNS = {"Invoice": "invoice", "StockCode": "stock_code", "Description": "description", "Quantity": "quantity",
           "InvoiceDate": "invoice_date", "Price": "price", "Customer ID": "customer_id", "Country": "country"}


def download(url: str = config.SOURCE_URL, dest: Path = config.SOURCE_ZIP) -> Path:
    """Fetch the zip unless it is already there (the data set does not change)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        tmp = dest.with_suffix(".part")
        urllib.request.urlretrieve(url, tmp)
        tmp.rename(dest)
    return dest


def to_parquet(zip_path: Path = config.SOURCE_ZIP, out: Path = config.RAW_PARQUET) -> Path:
    """Both sheets (2009-2010, 2010-2011) in one table with snake_case columns and stable types."""
    if out.exists():
        return out
    with zipfile.ZipFile(zip_path) as z:
        name = next(n for n in z.namelist() if n.lower().endswith(".xlsx"))
        with z.open(name) as f:
            sheets = pd.read_excel(f, sheet_name=None, dtype={"Invoice": str, "StockCode": str})
    df = pd.concat(sheets.values(), ignore_index=True).rename(columns=COLUMNS)
    df["customer_id"] = df["customer_id"].astype("Int64").astype("string")
    df["invoice_date"] = pd.to_datetime(df["invoice_date"])
    for c in ("invoice", "stock_code", "description", "country"):
        df[c] = df[c].astype("string").str.strip()
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    return out


def extract() -> str:
    return str(to_parquet(download()))
