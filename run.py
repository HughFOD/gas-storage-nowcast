"""Runs the whole pipeline. Use the step*.py files in PyCharm rather than this.

    python run.py demo              fake data, no internet needed
    python run.py analyze           real EIA + weather data
    python run.py analyze --refresh re-download everything
"""
import argparse
import json
import sys
import time

import pandas as pd

from gasstore import config, features, models, quality, report, storage, synthetic, weather


def analyze(stor: pd.DataFrame, wk: pd.DataFrame, daily: pd.DataFrame, out, mode: str) -> str:
    """Everything after the download. wk = weekly degree days; daily = daily temperatures
    (only used for the weather data checks; may be empty)."""
    out.mkdir(parents=True, exist_ok=True)
    print("2/5 Building weekly features ...")
    df = features.build(stor, wk)
    last_week = df.loc[df["change_bcf"].notna(), "week_ending"].max()
    print(f"    {df['change_bcf'].notna().sum()} storage weeks, latest {last_week:%Y-%m-%d}")

    print("3/5 Walk-forward test (each week predicted using only earlier data) ...")
    pred = models.walk_forward(df)
    m = report.metrics(pred)
    hold = pd.Timestamp(config.HOLDOUT_START)
    m_val = report.metrics(pred[pred["week_ending"] < hold])
    m_hold = report.metrics(pred[pred["week_ending"] >= hold])
    # The model is chosen on the validation years only, so the holdout score is an honest estimate.
    val = m_val[(m_val["season"] == "all year") & m_val["model"].isin(report.MODEL_NAMES)]
    best = val.sort_values("MAE (Bcf)").iloc[0]["model"]
    now = models.nowcast(df, pred)

    print("4/5 Checking data quality ...")
    q = quality.check(df, daily, pred[pred["model"] == best])
    q.to_csv(out / "quality.csv", index=False)
    print(f"    {len(q)} items flagged")

    print("5/5 Writing results ...")
    pred.to_csv(out / "predictions.csv", index=False)
    m.round(2).to_csv(out / "metrics.csv", index=False)
    m_val.round(2).to_csv(out / "metrics_validation.csv", index=False)
    m_hold.round(2).to_csv(out / "metrics_holdout.csv", index=False)
    (out / "best.json").write_text(json.dumps({
        "best": best, "chosen_on": f"{config.TEST_START[:4]}-{hold.year - 1}",
        "holdout_from": config.HOLDOUT_START, "last_week": f"{last_week:%Y-%m-%d}"}))
    df.to_csv(out / "weekly_features.csv", index=False)
    if not now.empty:
        now.round({"pred": 1, "lower": 1, "upper": 1}).to_csv(out / "nowcast.csv", index=False)
    cons = report.consensus_compare(pred, best)
    report.charts(df, pred, m, best, out)
    return report.summary(m, best, now, q, cons, mode, out, last_week, m_hold=m_hold)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["demo", "analyze"])
    ap.add_argument("--refresh", action="store_true", help="re-download all data")
    ap.add_argument("--fresh-storage", action="store_true", help="always re-download the EIA storage data")
    args = ap.parse_args()
    t0 = time.time()

    print("1/5 Getting data ...")
    if args.mode == "demo":
        stor, daily = synthetic.make()
        out = config.OUTPUT / "demo"
    else:
        stor = storage.fetch_storage(refresh=args.refresh or args.fresh_storage)
        # Always refresh the latest storage weeks if the cache is old.
        if not args.refresh and stor["week_ending"].max() < pd.Timestamp.today() - pd.Timedelta(days=13):
            stor = storage.fetch_storage(refresh=True)
        daily = weather.fetch_daily(refresh=args.refresh)
        out = config.OUTPUT / "real"
    text = analyze(stor, weather.weekly_degree_days(daily), daily, out, args.mode)
    print("\n" + text)
    print(f"Finished in {time.time() - t0:.0f}s. Results in {out}")


if __name__ == "__main__":
    sys.exit(main())
