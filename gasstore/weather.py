"""Daily temperatures from Open-Meteo (free, no key) turned into weekly
weighted heating and cooling degree days (HDD/CDD).

HDD for a day = max(0, 65 °F - mean temperature). A cold week has many HDDs,
homes burn more gas for heat, and storage withdrawals are bigger.
CDD = max(0, mean temperature - 65 °F). A hot week has many CDDs, power plants
burn more gas for air conditioning, and summer injections are smaller.

Two sources: the historical archive (lags real time by about 5 days) and the
forecast service, which also returns the last couple of weeks and the next 7
days. Archive values always win; forecast values only fill the most recent days.
"""
from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd

from . import config


def _get(url: str, params: dict) -> pd.DataFrame:
    import time

    import requests

    for attempt in range(4):
        try:
            r = requests.get(url, params=params, timeout=90)
            r.raise_for_status()
            d = r.json()["daily"]
            return pd.DataFrame({"date": pd.to_datetime(d["time"]),
                                 "temp_f": pd.to_numeric(d["temperature_2m_mean"])})
        except Exception as e:  # noqa: BLE001
            if attempt == 3:
                raise
            # Open-Meteo's free tier limits requests per minute; long downloads count extra.
            wait = 65 if "429" in str(e) else 10
            print(f"    (download hiccup: {str(e)[:80]} - waiting {wait}s and retrying)")
            time.sleep(wait)
    raise RuntimeError("unreachable")


def fetch_daily(end: date | None = None, refresh: bool = False) -> pd.DataFrame:
    """Long frame: date, city, temp_f, source ('archive' or 'forecast')."""
    config.RAW.mkdir(parents=True, exist_ok=True)
    cache = config.RAW / "weather_daily.csv"
    today = date.today()
    archive_end = min(end or today, today - timedelta(days=6))
    old = pd.DataFrame(columns=["date", "city", "temp_f", "source"])
    if cache.exists() and not refresh:
        old = pd.read_csv(cache, parse_dates=["date"])
        old = old[old["source"] == "archive"]  # forecast days are always re-fetched

    frames = [old]
    for city, (lat, lon, _, _) in config.CITIES.items():
        have = old.loc[old["city"] == city, "date"]
        start = (have.max() + pd.Timedelta(days=1)).date() if len(have) else \
            date.fromisoformat(config.WEATHER_START)
        if start <= archive_end:
            print(f"  Weather archive: {city} {start} to {archive_end}")
            df = _get(config.ARCHIVE_URL, {
                "latitude": lat, "longitude": lon, "start_date": start.isoformat(),
                "end_date": archive_end.isoformat(), "daily": "temperature_2m_mean",
                "temperature_unit": "fahrenheit", "timezone": "auto"})
            frames.append(df.assign(city=city, source="archive"))
            # Save after every city, so an interrupted download picks up where it stopped.
            pd.concat(frames, ignore_index=True).dropna(subset=["temp_f"]).to_csv(cache, index=False)
    archive = pd.concat(frames, ignore_index=True).dropna(subset=["temp_f"])

    recent = []
    try:
        for city, (lat, lon, _, _) in config.CITIES.items():
            df = _get(config.FORECAST_URL, {
                "latitude": lat, "longitude": lon, "past_days": 14, "forecast_days": 7,
                "daily": "temperature_2m_mean", "temperature_unit": "fahrenheit",
                "timezone": "auto"})
            recent.append(df.assign(city=city, source="forecast"))
        print("  Weather forecast: last 14 days + next 7 days")
    except Exception as e:  # noqa: BLE001 - the nowcast just covers fewer weeks
        print(f"  (Couldn't get the weather forecast, skipping the latest weeks: {e})")
    out = pd.concat([archive, *recent], ignore_index=True).dropna(subset=["temp_f"])
    # Keep the archive value when both sources have a day.
    out["rank"] = (out["source"] == "forecast").astype(int)
    out = (out.sort_values("rank").drop_duplicates(["date", "city"], keep="first")
           .drop(columns="rank").sort_values(["city", "date"]).reset_index(drop=True))
    return out


def week_ending(dates: pd.Series) -> pd.Series:
    """EIA storage weeks run Saturday to Friday and are labeled by the Friday."""
    d = pd.to_datetime(dates)
    return d + pd.to_timedelta((4 - d.dt.weekday) % 7, unit="D")


def weekly_degree_days(daily: pd.DataFrame) -> pd.DataFrame:
    """One row per week: weighted HDD and CDD (sums over the 7 days), number of
    complete days, and how many of the days came from the forecast."""
    w = pd.DataFrame(config.CITIES, index=["lat", "lon", "hdd_w", "cdd_w"]).T
    w["hdd_w"] /= w["hdd_w"].sum()
    w["cdd_w"] /= w["cdd_w"].sum()
    d = daily.merge(w[["hdd_w", "cdd_w"]], left_on="city", right_index=True)
    d["hdd"] = np.maximum(0, config.BASE_F - d["temp_f"]) * d["hdd_w"]
    d["cdd"] = np.maximum(0, d["temp_f"] - config.BASE_F) * d["cdd_w"]
    d["fc"] = (d["source"] == "forecast").astype(float)
    per_day = d.groupby("date").agg(hdd=("hdd", "sum"), cdd=("cdd", "sum"),
                                    n_cities=("city", "nunique"), fc=("fc", "max"))
    per_day = per_day[per_day["n_cities"] == len(config.CITIES)].reset_index()
    per_day["week_ending"] = week_ending(per_day["date"])
    wk = per_day.groupby("week_ending").agg(hdd=("hdd", "sum"), cdd=("cdd", "sum"),
                                            days=("date", "count"),
                                            forecast_days=("fc", "sum")).reset_index()
    return wk[wk["days"] == 7].drop(columns="days").reset_index(drop=True)
