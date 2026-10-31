"""EIA weekly natural gas storage (Lower 48, Bcf).

Three ways to get it, tried in order:
  1. the free Excel download on eia.gov (no key needed)
  2. the EIA API, if you have a free key in eia_key.txt or EIA_API_KEY
  3. a file you saved yourself at data/raw/storage_manual.csv with
     columns week_ending,storage_bcf
"""
from __future__ import annotations

import io
import os

import numpy as np
import pandas as pd

from . import config


def parse_xls(content: bytes) -> pd.DataFrame:
    """Parse EIA's 'hist_xls' workbook. Sheet 'Data 1': two title rows, then
    a Date column and one value column."""
    raw = pd.read_excel(io.BytesIO(content), sheet_name="Data 1", header=None)
    # Find the header row: the first row whose first cell says "Date".
    hdr = raw.index[raw.iloc[:, 0].astype(str).str.strip().str.lower() == "date"]
    start = int(hdr[0]) + 1 if len(hdr) else 0
    df = raw.iloc[start:, :2].copy()
    df.columns = ["week_ending", "storage_bcf"]
    df["week_ending"] = pd.to_datetime(df["week_ending"], errors="coerce")
    df["storage_bcf"] = pd.to_numeric(df["storage_bcf"], errors="coerce")
    return _tidy(df)


def _tidy(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["storage_bcf"] = pd.to_numeric(df["storage_bcf"], errors="coerce")  # the API sends text
    df = df.dropna(subset=["week_ending", "storage_bcf"])
    df["week_ending"] = pd.to_datetime(df["week_ending"]).dt.normalize()
    df = df.drop_duplicates("week_ending", keep="last").sort_values("week_ending")
    return df.reset_index(drop=True)[["week_ending", "storage_bcf"]]


def _api_key() -> str | None:
    key = os.environ.get("EIA_API_KEY")
    f = config.ROOT / "eia_key.txt"
    if not key and f.exists():
        key = f.read_text().strip()
    return key or None


def _fetch_api(key: str) -> pd.DataFrame:
    import requests

    r = requests.get(config.API_URL, params={
        "api_key": key, "frequency": "weekly", "data[0]": "value",
        "facets[series][]": config.SERIES_ID, "start": config.STORAGE_START[:10],
        "sort[0][column]": "period", "sort[0][direction]": "asc", "length": 5000,
    }, timeout=60)
    r.raise_for_status()
    rows = r.json()["response"]["data"]
    df = pd.DataFrame(rows).rename(columns={"period": "week_ending", "value": "storage_bcf"})
    return _tidy(df)


def fetch_storage(refresh: bool = False) -> pd.DataFrame:
    config.RAW.mkdir(parents=True, exist_ok=True)
    cache = config.RAW / "storage.csv"
    manual = config.RAW / "storage_manual.csv"
    if cache.exists() and not refresh:
        return _tidy(pd.read_csv(cache))

    errors = []
    df = None
    try:
        import requests

        r = requests.get(config.XLS_URL, timeout=60,
                         headers={"User-Agent": "gas-storage-nowcast (student project)"})
        r.raise_for_status()
        df = parse_xls(r.content)
        print(f"  Downloaded EIA storage history: {len(df)} weeks")
    except Exception as e:  # noqa: BLE001 - try the next source
        errors.append(f"Excel download: {e}")
    if df is None and _api_key():
        try:
            df = _fetch_api(_api_key())
            print(f"  Downloaded EIA storage via API: {len(df)} weeks")
        except Exception as e:  # noqa: BLE001
            errors.append(f"EIA API: {e}")
    if df is None and manual.exists():
        df = _tidy(pd.read_csv(manual))
        print(f"  Using your saved file {manual.name}: {len(df)} weeks")
    if (df is None or df.empty) and cache.exists():
        print("  !! Couldn't download new storage data; using the last saved copy.\n  " + "\n  ".join(errors))
        return _tidy(pd.read_csv(cache))
    if df is None or df.empty:
        raise RuntimeError(
            "Couldn't get EIA storage data.\n  " + "\n  ".join(errors) +
            f"\nFix: open {config.XLS_URL} in your browser, copy the Date and value "
            f"columns into {manual} with headers week_ending,storage_bcf, and run again.")
    df = df[df["week_ending"] >= config.STORAGE_START]
    df.to_csv(cache, index=False)
    return df


def add_changes(df: pd.DataFrame) -> pd.DataFrame:
    """Weekly net change = this week's level minus last week's.

    EIA's headline 'implied flow' can differ from this when it reclassifies gas
    between working and base gas; quality.py flags those weeks."""
    df = df.sort_values("week_ending").copy()
    gap = df["week_ending"].diff().dt.days
    df["change_bcf"] = df["storage_bcf"].diff()
    df.loc[gap != 7, "change_bcf"] = np.nan  # don't difference across a missing week
    return df
