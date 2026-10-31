"""Checks that nothing the model sees could only be known after the release."""
import io

import numpy as np
import pandas as pd
import pytest

from gasstore import features, models, storage, synthetic, weather
from gasstore.features import FEATURES


@pytest.fixture(scope="module")
def data():
    stor, daily = synthetic.make(today=pd.Timestamp("2024-06-15").date())
    wk = weather.weekly_degree_days(daily)
    return stor, wk, features.build(stor, wk)


def test_week_ending_is_friday():
    d = pd.Series(pd.to_datetime(["2024-06-08", "2024-06-13", "2024-06-14"]))  # Sat, Thu, Fri
    assert list(weather.week_ending(d)) == list(pd.to_datetime(["2024-06-14"] * 3))


def test_changing_a_week_does_not_change_its_own_features(data):
    """If week t's storage number were different, every feature for week t
    (and all earlier weeks) must be identical: they can't depend on it."""
    stor, wk, base = data
    t = pd.Timestamp("2022-01-14")
    stor2 = stor.copy()
    later = stor2["week_ending"] >= t
    stor2.loc[later, "storage_bcf"] += 500  # big shock from week t onward
    alt = features.build(stor2, wk)
    upto = base["week_ending"] <= t
    pd.testing.assert_frame_equal(base.loc[upto, FEATURES], alt.loc[upto, FEATURES])
    # ...and the week after does see it, through last week's change.
    nxt = base.index[base["week_ending"] == t + pd.Timedelta(days=7)][0]
    assert alt.at[nxt, "chg_lag1"] == base.at[nxt, "chg_lag1"] + 500


def test_five_year_average_uses_only_earlier_years(data):
    _, _, df = data
    i = df.index[df["week_ending"] == pd.Timestamp("2021-03-12")][0]
    prev = []
    for k in range(1, 6):
        target = df.at[i, "week_ending"] - pd.DateOffset(years=k)
        j = (df["week_ending"] - target).abs().idxmin()
        prev.append(df.at[j, "change_bcf"])
    assert df.at[i, "avg5"] == pytest.approx(np.mean(prev))


def test_walk_forward_never_trains_on_the_future(data, monkeypatch):
    _, _, df = data
    seen = []
    orig = models.RidgeModel.fit

    def spy(self, train):
        seen.append(train["week_ending"].max())
        return orig(self, train)

    monkeypatch.setattr(models.RidgeModel, "fit", spy)
    monkeypatch.setattr(models, "MODELS", [models.RidgeModel])
    pred = models.walk_forward(df, test_start="2023-06-01")
    weeks = sorted(pred["week_ending"].unique())
    assert len(seen) == len(weeks)
    assert all(s < w for s, w in zip(seen, weeks))


def test_intervals_use_only_past_errors():
    p = pd.DataFrame({"week_ending": pd.date_range("2020-01-03", periods=60, freq="W-FRI"),
                      "model": "m", "pred": 0.0, "actual": 1.0})
    p.loc[59, "actual"] = 1000.0  # a huge miss in the last week
    out = models.add_intervals(p)
    assert out.loc[59, "upper"] == pytest.approx(1.0)  # its own miss isn't used


def test_parse_eia_workbook():
    buf = io.BytesIO()
    with pd.ExcelWriter(buf) as xw:
        pd.DataFrame([["Back to Contents", None], ["Sourcekey", "NW2_EPG0_SWO_R48_BCF"],
                      ["Date", "Weekly Lower 48 States ..."],
                      [pd.Timestamp("2010-01-01"), 3117], [pd.Timestamp("2010-01-08"), 2850]]
                     ).to_excel(xw, sheet_name="Data 1", header=False, index=False)
    df = storage.parse_xls(buf.getvalue())
    assert list(df["storage_bcf"]) == [3117, 2850]
    assert storage.add_changes(df)["change_bcf"].iloc[1] == -267
