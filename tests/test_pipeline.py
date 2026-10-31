"""The whole demo runs and the models beat the simple benchmarks on data where
weather really does drive storage."""
import pandas as pd

from gasstore import features, models, quality, report, synthetic, weather


def test_demo_pipeline_end_to_end(tmp_path):
    stor, daily = synthetic.make(today=pd.Timestamp("2024-11-09").date())
    df = features.build(stor, weather.weekly_degree_days(daily))
    pred = models.walk_forward(df, test_start="2022-01-01")
    m = report.metrics(pred)
    allyr = m[m["season"] == "all year"].set_index("model")["MAE (Bcf)"]
    best = allyr[report.MODEL_NAMES].idxmin()
    assert allyr[best] < 0.7 * allyr["5-year average"]

    now = models.nowcast(df, pred)
    assert not now.empty and now["week_ending"].min() > stor["week_ending"].max()
    assert (now["lower"] <= now["pred"]).all() and (now["pred"] <= now["upper"]).all()

    q = quality.check(df, daily, pred[pred["model"] == best])
    report.charts(df, pred, m, best, tmp_path)
    report.summary(m, best, now, q, None, "test", tmp_path, stor["week_ending"].max())
    assert (tmp_path / "summary.md").exists() and (tmp_path / "forecast_vs_actual.png").exists()
