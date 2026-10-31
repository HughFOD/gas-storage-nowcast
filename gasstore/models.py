"""Benchmarks, models, and the walk-forward test.

Walk-forward means: to predict the week ending on date t, a model is trained
only on weeks before t, exactly as if we were standing on that Thursday
morning. Then t's real number is revealed and we move on a week. Every
prediction in the results was made this way, so none of them saw the answer.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from . import config
from .features import FEATURES

# The simple rules a trader would compare against.
BENCHMARKS = {
    "5-year average": lambda df: df["avg5"],
    "Same week last year": lambda df: df["last_year"],
    "Last week's change": lambda df: df["chg_lag1"],
}

WEATHER_ADJ = ["hdd_dev", "cdd_dev", "dev_lag1"]


class WeatherAdjusted:
    """5-year average, plus a correction for this week being colder or hotter than
    normal. Learns only from the last few years, because the market keeps
    changing (more LNG exports, more gas-fired power), so old years mislead."""
    name = "Weather-adjusted 5-yr avg"
    refit_every = 1

    def fit(self, df):
        recent = df[df["week_ending"] > df["week_ending"].max() - pd.DateOffset(years=config.DRIFT_YEARS)]
        self.m = LinearRegression().fit(recent[WEATHER_ADJ], recent["change_bcf"] - recent["avg5"])
        return self

    def predict(self, df):
        return df["avg5"] + self.m.predict(df[WEATHER_ADJ])


class RidgeModel:
    """Linear model on every feature, trained on all past weeks."""
    name = "Ridge regression"
    refit_every = 1

    def fit(self, df):
        self.m = make_pipeline(StandardScaler(), Ridge(alpha=1.0)).fit(df[FEATURES], df["change_bcf"])
        return self

    def predict(self, df):
        return self.m.predict(df[FEATURES])


class Boosting:
    """Gradient-boosted trees: can learn that 10 extra HDDs in January matter
    differently from 10 extra HDDs in October. Predicts the surprise versus the
    5-year average, then adds the average back."""
    name = "Gradient boosting"
    refit_every = 13  # retrain every quarter to keep the run quick

    def fit(self, df):
        self.m = HistGradientBoostingRegressor(
            max_iter=300, learning_rate=0.05, max_leaf_nodes=15, min_samples_leaf=20,
            l2_regularization=1.0, random_state=config.RANDOM_SEED,
        ).fit(df[FEATURES], df["change_bcf"] - df["avg5"])
        return self

    def predict(self, df):
        return df["avg5"] + self.m.predict(df[FEATURES])


MODELS = [WeatherAdjusted, RidgeModel, Boosting]


def usable(df: pd.DataFrame) -> pd.Series:
    return df[FEATURES].notna().all(axis=1)


def walk_forward(df: pd.DataFrame, test_start: str | None = None) -> pd.DataFrame:
    """Long frame: week_ending, model, pred, actual, avg5, season, lower, upper."""
    test_start = pd.Timestamp(test_start or config.TEST_START)
    ok = usable(df) & df["change_bcf"].notna()
    test_idx = df.index[ok & (df["week_ending"] >= test_start)]
    rows = []
    for M in MODELS:
        model, since = None, 0
        for i in test_idx:
            t = df.at[i, "week_ending"]
            if model is None or since >= M.refit_every:
                train = df[ok & (df["week_ending"] < t)]
                model, since = M().fit(train), 0
            since += 1
            rows.append((t, M.name, float(np.asarray(model.predict(df.loc[[i]]))[0])))
    for name, rule in BENCHMARKS.items():
        p = rule(df)
        rows += [(df.at[i, "week_ending"], name, p[i]) for i in test_idx]
    out = pd.DataFrame(rows, columns=["week_ending", "model", "pred"])
    out = out.merge(df[["week_ending", "change_bcf", "avg5", "season", "forecast_days"]],
                    on="week_ending").rename(columns={"change_bcf": "actual"})
    return add_intervals(out)


def add_intervals(pred: pd.DataFrame, window: int = 52, min_hist: int = 26) -> pd.DataFrame:
    """80% range for each week from that model's own errors over the previous
    52 weeks (only errors already known at the time)."""
    lo_q, hi_q = (1 - config.INTERVAL) / 2, 1 - (1 - config.INTERVAL) / 2
    out = []
    for _, g in pred.sort_values("week_ending").groupby("model", sort=False):
        err = (g["actual"] - g["pred"]).shift(1)  # this week's error is not known yet
        roll = err.rolling(window, min_periods=min_hist)
        g = g.assign(lower=g["pred"] + roll.quantile(lo_q), upper=g["pred"] + roll.quantile(hi_q))
        out.append(g)
    return pd.concat(out, ignore_index=True)


def nowcast(df: pd.DataFrame, history: pd.DataFrame) -> pd.DataFrame:
    """Predict weeks that have full weather but no EIA number yet. If there are
    two such weeks, the first prediction stands in for 'last week's change'."""
    target = df[df["change_bcf"].isna() & df[["hdd", "cdd", "avg5"]].notna().all(axis=1)
                & (df["week_ending"] > df.loc[df["change_bcf"].notna(), "week_ending"].max())]
    if target.empty:
        return pd.DataFrame()
    train = df[usable(df) & df["change_bcf"].notna()]
    lo_q, hi_q = (1 - config.INTERVAL) / 2, 1 - (1 - config.INTERVAL) / 2
    out = []
    for M in MODELS:
        model = M().fit(train)
        h = history[history["model"] == M.name].sort_values("week_ending").tail(52)
        err = h["actual"] - h["pred"]
        work = df.copy()
        for i in target.index:
            row = work.loc[[i]].copy()
            prev = work.loc[i - 1]
            row["chg_lag1"] = prev["change_bcf"]
            row["dev_lag1"] = prev["change_bcf"] - prev["avg5"]
            row["surplus_lag1"] = prev["storage_bcf"] - prev["storage_avg5"]
            prev2 = work.loc[i - 2]
            row["dev_lag2"] = prev2["change_bcf"] - prev2["avg5"]
            p = float(np.asarray(model.predict(row))[0])
            work.at[i, "change_bcf"] = p
            work.at[i, "storage_bcf"] = work.at[i - 1, "storage_bcf"] + p
            out.append({"week_ending": work.at[i, "week_ending"], "model": M.name, "pred": p,
                        "lower": p + err.quantile(lo_q), "upper": p + err.quantile(hi_q),
                        "avg5": work.at[i, "avg5"], "forecast_days": work.at[i, "forecast_days"]})
    return pd.DataFrame(out)
