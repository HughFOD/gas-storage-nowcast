"""Made-up but realistic data for the demo, so the whole project can run and be
tested without internet. Built so that the answer is known: storage changes
are driven by weather, with a weather sensitivity that slowly grows over the
years (like the real market), holiday effects, and noise."""
from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd

from . import config
from .weather import weekly_degree_days


def make(seed: int = config.RANDOM_SEED, today: date | None = None):
    rng = np.random.default_rng(seed)
    today = today or date.today()
    days = pd.date_range(config.WEATHER_START, today + timedelta(days=7))
    n = len(days)
    doy = days.dayofyear.to_numpy()
    # A shared national weather pattern (cold snaps cover many cities at once).
    shared = np.zeros(n)
    for t in range(1, n):
        shared[t] = 0.8 * shared[t - 1] + rng.normal(0, 3.5)
    frames = []
    for city, (lat, lon, _, _) in config.CITIES.items():
        mean = 95 - 1.05 * lat            # colder up north
        amp = 0.55 * lat - 3              # bigger seasons up north
        local = np.zeros(n)
        for t in range(1, n):
            local[t] = 0.6 * local[t - 1] + rng.normal(0, 3)
        temp = mean - amp * np.cos(2 * np.pi * (doy - 15) / 365.25) + shared + local
        frames.append(pd.DataFrame({"date": days, "city": city, "temp_f": temp.round(1)}))
    daily = pd.concat(frames, ignore_index=True)
    daily["source"] = np.where(daily["date"] > pd.Timestamp(today - timedelta(days=6)),
                               "forecast", "archive")

    wk = weekly_degree_days(daily)
    years = (wk["week_ending"] - pd.Timestamp("2010-01-01")).dt.days / 365.25
    a = 1.0 + 0.012 * years.clip(lower=0)      # weather sensitivity grows over time
    b = 0.55
    demand = a * wk["hdd"] + b * wk["cdd"]
    base = demand.groupby(wk["week_ending"].dt.year).transform("mean")  # ~zero net per year
    hol = wk["week_ending"].map(lambda d: 12.0 if (d.month == 11 and 22 <= d.day <= 30)
                                or (d.month == 12 and d.day >= 25) or (d.month == 1 and d.day <= 7)
                                else 0.0)
    noise = np.zeros(len(wk))
    for t in range(1, len(wk)):
        noise[t] = 0.4 * noise[t - 1] + rng.normal(0, 7)
    change = base - demand + hol + noise
    level = 3100 + np.cumsum(change)
    level = level - (level[wk["week_ending"] >= pd.Timestamp(config.STORAGE_START)].mean() - 2700)
    storage = pd.DataFrame({"week_ending": wk["week_ending"], "storage_bcf": level.round(0)})
    last_release = pd.Timestamp(today - timedelta(days=6))  # EIA publishes 6 days after week end
    storage = storage[(storage["week_ending"] >= config.STORAGE_START)
                      & (storage["week_ending"] <= last_release)].reset_index(drop=True)
    return storage, daily
