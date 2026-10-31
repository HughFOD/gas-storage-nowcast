"""One row per storage week with everything a forecaster would know at 10:29 ET
on the Thursday the number comes out:

  - the weather during that week (it has already happened)
  - every earlier week's storage number (released on earlier Thursdays)
  - the same week in earlier years

Nothing from the week's own storage number or any later week is used.
tests/test_features.py checks this.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config
from .storage import add_changes

FEATURES = ["hdd", "cdd", "hdd_dev", "cdd_dev", "avg5", "last_year", "chg_lag1",
            "dev_lag1", "surplus_lag1", "doy_sin", "doy_cos", "holiday", "trend"]


def same_week_years_ago(df: pd.DataFrame, col: str, k: int) -> pd.Series:
    """Value of `col` in the week k years earlier (nearest Friday within 3 days)."""
    look = df[["week_ending", col]].rename(columns={"week_ending": "match", col: "v"})
    q = pd.DataFrame({"pos": np.arange(len(df)),
                      "match": df["week_ending"] - pd.DateOffset(years=k)}).sort_values("match")
    m = pd.merge_asof(q, look.sort_values("match"), on="match", direction="nearest",
                      tolerance=pd.Timedelta(days=3))
    return pd.Series(m.sort_values("pos")["v"].to_numpy(), index=df.index)


def prior_years_mean(df, col, years, min_years):
    vals = pd.concat([same_week_years_ago(df, col, k) for k in range(1, years + 1)], axis=1)
    return vals.mean(axis=1).where(vals.notna().sum(axis=1) >= min_years)


def holiday_week(week_ending: pd.Series) -> pd.Series:
    """Thanksgiving, Christmas and New Year weeks: offices and factories close,
    so demand and the storage number behave differently."""
    start = week_ending - pd.Timedelta(days=6)
    out = []
    for s, e in zip(start, week_ending):
        days = pd.date_range(s, e)
        thanks = any(d.month == 11 and d.weekday() == 3 and 22 <= d.day <= 28 for d in days)
        xmas = any((d.month == 12 and d.day == 25) or (d.month == 1 and d.day == 1) for d in days)
        out.append(int(thanks or xmas))
    return pd.Series(out, index=week_ending.index)


def build(storage: pd.DataFrame, weekly_weather: pd.DataFrame) -> pd.DataFrame:
    s = add_changes(storage)
    grid = pd.DataFrame({"week_ending": pd.date_range(
        min(s["week_ending"].min(), weekly_weather["week_ending"].min()),
        max(s["week_ending"].max(), weekly_weather["week_ending"].max()), freq="W-FRI")})
    df = (grid.merge(weekly_weather, on="week_ending", how="left")
          .merge(s, on="week_ending", how="left"))

    df["hdd_normal"] = prior_years_mean(df, "hdd", config.NORMAL_YEARS, 7)
    df["cdd_normal"] = prior_years_mean(df, "cdd", config.NORMAL_YEARS, 7)
    df["hdd_dev"] = df["hdd"] - df["hdd_normal"]
    df["cdd_dev"] = df["cdd"] - df["cdd_normal"]

    # The 5-year average is the benchmark the market quotes every Thursday.
    df["avg5"] = prior_years_mean(df, "change_bcf", 5, 4)
    df["last_year"] = same_week_years_ago(df, "change_bcf", 1)
    df["storage_avg5"] = prior_years_mean(df, "storage_bcf", 5, 4)

    # Last week's report (already public by this Thursday).
    df["chg_lag1"] = df["change_bcf"].shift(1)
    df["dev_lag1"] = (df["change_bcf"] - df["avg5"]).shift(1)
    df["surplus_lag1"] = (df["storage_bcf"] - df["storage_avg5"]).shift(1)

    doy = df["week_ending"].dt.dayofyear
    df["doy_sin"] = np.sin(2 * np.pi * doy / 365.25)
    df["doy_cos"] = np.cos(2 * np.pi * doy / 365.25)
    df["holiday"] = holiday_week(df["week_ending"])
    df["trend"] = (df["week_ending"] - pd.Timestamp("2010-01-01")).dt.days / 365.25
    df["season"] = np.where(df["week_ending"].dt.month.between(4, 10), "injection", "withdrawal")
    return df[df["week_ending"] >= config.STORAGE_START].reset_index(drop=True)
