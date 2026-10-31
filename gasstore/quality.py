"""Checks on the data before trusting any model built on it.

Each problem becomes a row in quality.csv with the week, what was found, and
why it matters. These are leads to investigate, not automatic corrections.
"""
from __future__ import annotations

import pandas as pd

from . import config


def check(df: pd.DataFrame, daily_weather: pd.DataFrame,
          best_pred: pd.DataFrame | None = None) -> pd.DataFrame:
    issues = []

    def add(week, kind, detail):
        issues.append({"week_ending": week, "check": kind, "detail": detail})

    s = df[df["storage_bcf"].notna()]
    last = s["week_ending"].max()

    # 1. Missing weeks inside the EIA series.
    for _, r in df[(df["week_ending"] <= last) & df["storage_bcf"].isna()].iterrows():
        add(r["week_ending"], "missing week", "No EIA storage value for this week.")

    # 2. Weeks the weather can't explain: the best model (which knows the
    #    weather) missed by far more than usual. Often an EIA reclassification
    #    (gas moved between working and base gas), a revision, or a real event
    #    like a pipeline or LNG plant outage. Look these up in the EIA report notes.
    if best_pred is not None and not best_pred.empty:
        g = best_pred.sort_values("week_ending")
        err = g["actual"] - g["pred"]
        typical = err.abs().rolling(104, min_periods=26).median().shift(1)
        for _, r in g[(err.abs() > 4 * typical) & (err.abs() > 15)].iterrows():
            add(r["week_ending"], "unexplained change",
                f"EIA {r['actual']:+.0f} Bcf vs model {r['pred']:+.0f} (5-yr avg {r['avg5']:+.0f}). "
                "Weather doesn't explain it: check the EIA report for a reclassification, "
                "revision, or outage.")

    # 3. Physically odd values.
    for _, r in s[(s["storage_bcf"] < 500) | (s["storage_bcf"] > 4500)].iterrows():
        add(r["week_ending"], "level out of range", f"Storage {r['storage_bcf']:.0f} Bcf.")
    for _, r in df[df["change_bcf"].abs() > 400].iterrows():
        add(r["week_ending"], "huge weekly change", f"{r['change_bcf']:+.0f} Bcf in one week.")

    # 4. Weather gaps: a week with a missing city day gets dropped from the model.
    d = daily_weather[daily_weather["source"] == "archive"]
    per_city = d.groupby("city")["date"].agg(["min", "max", "count"])
    for city, r in per_city.iterrows():
        expected = (r["max"] - r["min"]).days + 1
        if r["count"] < expected:
            add(r["max"], "weather gap", f"{city}: {expected - r['count']} missing days.")
    for _, r in d[(d["temp_f"] < -40) | (d["temp_f"] > 115)].iterrows():
        add(r["date"], "weather outlier", f"{r['city']} daily mean {r['temp_f']:.0f} °F.")

    # 5. Weeks that had a storage number but no usable weather.
    nw = df[df["storage_bcf"].notna() & df["hdd"].isna() & (df["week_ending"] >= config.STORAGE_START)]
    for _, r in nw.iterrows():
        add(r["week_ending"], "no weather", "Storage week without a full 7 days of weather.")

    return pd.DataFrame(issues, columns=["week_ending", "check", "detail"])
