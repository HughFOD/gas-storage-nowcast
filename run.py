"""Runs the whole pipeline. Use the step*.py files in PyCharm rather than this.

    python run.py demo              fake data, no internet needed
    python run.py analyze           real EIA + weather data
    python run.py analyze --refresh re-download everything
"""
import argparse
import sys
import time

import pandas as pd

from gasstore import config, features, models, quality, report, storage, synthetic, weather


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["demo", "analyze"])
    ap.add_argument("--refresh", action="store_true", help="re-download all data")
    args = ap.parse_args()
    t0 = time.time()

    print("1/5 Getting data ...")
    if args.mode == "demo":
        stor, daily = synthetic.make()
        out = config.OUTPUT / "demo"
    else:
        stor = storage.fetch_storage(refresh=args.refresh)
        # Always refresh the latest storage weeks if the cache is old.
        if not args.refresh and stor["week_ending"].max() < pd.Timestamp.today() - pd.Timedelta(days=13):
            stor = storage.fetch_storage(refresh=True)
        daily = weather.fetch_daily(refresh=args.refresh)
        out = config.OUTPUT / "real"
    out.mkdir(parents=True, exist_ok=True)

    print("2/5 Building weekly features ...")
    wk = weather.weekly_degree_days(daily)
    df = features.build(stor, wk)
    last_week = df.loc[df["change_bcf"].notna(), "week_ending"].max()
    print(f"    {df['change_bcf'].notna().sum()} storage weeks, latest {last_week:%Y-%m-%d}")

    print("3/5 Walk-forward test (each week predicted using only earlier data) ...")
    pred = models.walk_forward(df)
    m = report.metrics(pred)
    allyr = m[(m["season"] == "all year") & m["model"].isin(report.MODEL_NAMES)]
    best = allyr.sort_values("MAE (Bcf)").iloc[0]["model"]
    now = models.nowcast(df, pred)

    print("4/5 Checking data quality ...")
    q = quality.check(df, daily, pred[pred["model"] == best])
    q.to_csv(out / "quality.csv", index=False)
    print(f"    {len(q)} items flagged")

    print("5/5 Writing results ...")
    pred.to_csv(out / "predictions.csv", index=False)
    m.round(2).to_csv(out / "metrics.csv", index=False)
    df.to_csv(out / "weekly_features.csv", index=False)
    if not now.empty:
        now.round({"pred": 1, "lower": 1, "upper": 1}).to_csv(out / "nowcast.csv", index=False)
    cons = report.consensus_compare(pred, best)
    report.charts(df, pred, m, best, out)
    text = report.summary(m, best, now, q, cons, args.mode, out, last_week)
    print("\n" + text)
    print(f"Finished in {time.time() - t0:.0f}s. Results in {out}")


if __name__ == "__main__":
    sys.exit(main())
