"""Builds a one-page project website in docs/ from the latest real-data results.

GitHub Pages can publish the docs/ folder as a free website. Every number on
the page is read from output/real, so re-running step 3 and then this updates it.
"""
from __future__ import annotations

import html
import shutil

import pandas as pd

from . import config

REPO_URL = "https://github.com/HughFOD/gas-storage-nowcast"

CHARTS = [
    ("forecast_vs_actual.png", "Forecast vs actual, last two years",
     "Each blue point was predicted before EIA released the number. Black dots are what EIA reported."),
    ("weather_vs_storage.png", "Weather drives the number",
     "Colder winter weeks mean bigger withdrawals; hotter summer weeks mean smaller injections."),
    ("error_by_model.png", "How far off each method is",
     "Average weekly miss in Bcf, winter vs summer. Lower is better."),
    ("error_over_time.png", "Is it getting worse over time?",
     "Average miss over the previous 26 weeks, for the best model and the 5-year average."),
]

CSS = """
:root{--bg:#fafaf8;--card:#fff;--ink:#1d2329;--muted:#5f6b76;--line:#e3e6e9;--accent:#2a6fdb;--warm:#e07b39}
@media (prefers-color-scheme:dark){:root{--bg:#14171a;--card:#1c2024;--ink:#e8eaec;--muted:#9aa5af;--line:#2e343a;--accent:#6ea0f0;--warm:#f09a5e}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);
font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Helvetica,Arial,sans-serif}
main{max-width:960px;margin:0 auto;padding:40px 16px 64px}
h1{font-size:2rem;line-height:1.2;margin:0 0 8px}h2{font-size:1.3rem;margin:48px 0 12px}
.lede{color:var(--muted);font-size:1.1rem;margin:0 0 28px;max-width:720px}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px}
.tile{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px}
.tile .v{font-size:1.8rem;font-weight:650;color:var(--accent);font-variant-numeric:tabular-nums}
.tile .l{color:var(--muted);font-size:.9rem}
.now{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--warm);border-radius:10px;padding:16px 20px}
figure{margin:24px 0;background:#fff;border:1px solid var(--line);border-radius:10px;padding:12px}
figure img{width:100%;height:auto;display:block}figcaption{color:#5f6b76;font-size:.9rem;margin-top:6px}
figure h3{margin:0 0 6px;font-size:1rem;color:#1d2329}
.tablewrap{overflow-x:auto}table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums;font-size:.95rem}
th,td{padding:8px 10px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}
th:first-child,td:first-child{text-align:left}th{color:var(--muted);font-weight:600}
tr.best td{font-weight:650}ul{padding-left:20px}li{margin:6px 0}
footer{margin-top:56px;color:var(--muted);font-size:.9rem;border-top:1px solid var(--line);padding-top:16px}
a{color:var(--accent)}
"""


def _fmt(x, d=1):
    return "–" if pd.isna(x) else f"{x:.{d}f}"


def build(src=None, dest=None) -> str:
    src = src or config.OUTPUT / "real"
    dest = dest or config.ROOT / "docs"
    (dest / "img").mkdir(parents=True, exist_ok=True)
    import json
    info = json.loads((src / "best.json").read_text()) if (src / "best.json").exists() else {}
    hold_file = src / "metrics_holdout.csv"
    m = pd.read_csv(hold_file if hold_file.exists() else src / "metrics.csv")
    pred = pd.read_csv(src / "predictions.csv", parse_dates=["week_ending"])
    q = pd.read_csv(src / "quality.csv", parse_dates=["week_ending"])
    now = pd.read_csv(src / "nowcast.csv", parse_dates=["week_ending"]) if (src / "nowcast.csv").exists() else None

    a = m[m["season"] == "all year"].set_index("model")
    from .report import MODEL_NAMES
    best = info.get("best") or a.loc[MODEL_NAMES, "MAE (Bcf)"].idxmin()
    b, avg = a.loc[best], a.loc["5-year average"]
    s = m.set_index(["model", "season"])
    win_b, win_a = s.loc[(best, "withdrawal"), "MAE (Bcf)"], s.loc[("5-year average", "withdrawal"), "MAE (Bcf)"]
    sum_b, sum_a = s.loc[(best, "injection"), "MAE (Bcf)"], s.loc[("5-year average", "injection"), "MAE (Bcf)"]
    first, last = pred["week_ending"].min(), pred["week_ending"].max()
    hold_from = pd.Timestamp(info.get("holdout_from", config.HOLDOUT_START))
    chosen_on = info.get("chosen_on", f"{first:%Y}-{hold_from.year - 1}")
    summer_head = "Summer improved the most." if sum_b < 0.85 * sum_a else "Summer is harder."
    summer = (f"In April–October it misses by {sum_b:.0f} Bcf against {sum_a:.0f} for the 5-year average. "
              "Summer was the weak spot of the first version; last week's weather, curvature for extreme heat "
              "and season-aware weather effects closed most of the gap." if sum_b < 0.85 * sum_a else
              f"In April–October it misses by {sum_b:.0f} Bcf against {sum_a:.0f} for the 5-year average. "
              "Summer storage depends on things this model does not see yet: LNG exports, power demand, production.")

    for f, *_ in CHARTS:
        shutil.copy(src / f, dest / "img" / f)

    rows = "".join(
        f"<tr{' class=best' if name == best else ''}><td>{html.escape(name)}</td>"
        f"<td>{_fmt(r['MAE (Bcf)'])}</td><td>{_fmt(r['beats 5-yr avg (% of weeks)'], 0)}%</td>"
        f"<td>{_fmt(r['surprise direction right (%)'], 0)}{'%' if pd.notna(r['surprise direction right (%)']) else ''}</td>"
        f"<td>{_fmt(r['80% range covered (%)'], 0)}%</td></tr>"
        for name, r in a.iterrows())

    now_html = ""
    if now is not None and not now.empty:
        items = []
        for wk, g in now.groupby("week_ending"):
            r = g[g["model"] == best].iloc[0]
            items.append(f"<p><b>Week ending {wk:%a %b %d, %Y}: {r['pred']:+.0f} Bcf</b> "
                         f"(80% range {r['lower']:+.0f} to {r['upper']:+.0f}; 5-year average {r['avg5']:+.0f}). "
                         f"EIA publishes it {wk + pd.Timedelta(days=6):%A %b %d} at 10:30 ET.</p>")
        now_html = ("<h2>Latest nowcast</h2><div class=now>" + "".join(items) +
                    "<p style='color:var(--muted);margin:0'>Made before the release. Recent days use forecast "
                    "weather, so the real range is a little wider.</p></div>")

    flagged = "".join(f"<li><b>{r['week_ending']:%b %d, %Y}</b>: {html.escape(r['detail'].split('. Weather')[0])}.</li>"
                      for _, r in q[q["check"] == "unexplained change"].iterrows())

    figs = "".join(f"<figure><h3>{t}</h3><img src='img/{f}' alt='{html.escape(t)}' loading=lazy>"
                   f"<figcaption>{c}</figcaption></figure>" for f, t, c in CHARTS)
    repo = f" · <a href='{REPO_URL}'>Code on GitHub</a>" if REPO_URL else ""

    page = f"""<!doctype html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>Gas Storage Nowcast</title><style>{CSS}</style></head><body><main>
<h1>Predicting the weekly natural gas storage report</h1>
<p class=lede>Every Thursday the US Energy Information Administration reports how much natural gas went into
or out of storage the week before, and gas prices move on any surprise. This project predicts that number
from weather before it is released, and tests every prediction honestly: each week is forecast using only
data that existed before its release.</p>
<div class=tiles>
<div class=tile><div class=v>{b['MAE (Bcf)']:.0f} Bcf</div><div class=l>average weekly miss ({html.escape(best)})</div></div>
<div class=tile><div class=v>{100 * (1 - b['MAE (Bcf)'] / avg['MAE (Bcf)']):.0f}%</div><div class=l>smaller miss than the 5-year average ({avg['MAE (Bcf)']:.0f} Bcf)</div></div>
<div class=tile><div class=v>{b['surprise direction right (%)']:.0f}%</div><div class=l>of weeks the direction of the surprise was called right</div></div>
<div class=tile><div class=v>{int(b['weeks'])}</div><div class=l>untouched test weeks, {hold_from:%b %Y} to {last:%b %Y}</div></div>
</div>
{now_html}
<h2>How it works</h2>
<ul>
<li><b>Weather:</b> daily temperatures for 17 US cities become weighted <i>heating degree days</i> (how cold) and
<i>cooling degree days</i> (how hot) for each Saturday–Friday storage week. Heating weights lean to the gas-heated
North-East and Midwest; cooling weights lean to Texas, the South and California, where gas power plants run air conditioning.</li>
<li><b>Benchmarks:</b> the 5-year average for that week (the number every storage report is compared with),
last year's number, and last week's number.</li>
<li><b>Models:</b> a weather-adjusted 5-year average that learns only from the last 3 years, a ridge regression,
and gradient-boosted trees.</li>
<li><b>Testing:</b> walk-forward. For each week since {first:%Y}, models are retrained on earlier weeks only.
Automated tests check that no input can depend on the number being predicted.</li>
</ul>
<h2>Results, {hold_from:%Y} onward</h2><p class=lede style='font-size:1rem;margin-bottom:12px'>Scored only on years that played no part in choosing the model.</p>
<div class=tablewrap><table><thead><tr><th>Method</th><th>Avg miss (Bcf)</th><th>Beats 5-yr avg</th>
<th>Surprise direction right</th><th>80% range covered</th></tr></thead><tbody>{rows}</tbody></table></div>
<h2>What I learned</h2>
<ul>
<li><b>Winter is where weather pays off.</b> In November–March the best model misses by {win_b:.0f} Bcf on average,
against {win_a:.0f} Bcf for the 5-year average. Cold snaps cause most of the big swings, and they show up in the temperature data.</li>
<li><b>{summer_head}</b> {summer}</li>
<li><b>Honest testing.</b> Every model and feature choice was made looking only at {chosen_on}. The numbers above are
for {hold_from:%Y} onward, which played no part in those choices, so they are a fair estimate of live performance.</li>
<li><b>Simple beat fancy.</b> A ridge regression beat gradient-boosted trees, both on the years used to choose it and on the later years.</li>
<li><b>The misses are informative.</b> Weeks the weather cannot explain point to real events.
The largest was February 2021, Winter Storm Uri, when freezing wells cut production and storage fell far more than cold alone implied.</li>
</ul>
<h2>Weeks the weather couldn't explain</h2><ul>{flagged}</ul>
{figs}
<footer>Data: EIA weekly working gas in storage (Lower 48) and Open-Meteo temperature archive.
Built with Python, pandas and scikit-learn{repo}.</footer>
</main></body></html>"""
    (dest / "index.html").write_text(page)
    return str(dest / "index.html")
