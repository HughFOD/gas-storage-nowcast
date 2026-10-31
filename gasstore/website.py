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
    ("forecast_vs_actual.png", "Predictions vs. what EIA reported, last two years",
     "Blue line: the model's prediction, made before each report came out. Black dots: the real number. "
     "Grey dashes: the standard guess (5-year average). Above zero means gas was added to storage; below zero, taken out."),
    ("weather_vs_storage.png", "Cold weeks drain storage; hot weeks slow the refill",
     "Left: in winter, the colder the week, the more gas comes out of storage. Right: in summer, hot weeks mean "
     "more gas burned for air conditioning, so less goes into storage."),
    ("error_by_model.png", "Typical miss for each method, winter vs. summer",
     "Shorter bars are better. Winter is where the standard guess struggles most."),
    ("error_over_time.png", "Typical miss over time",
     "Each point is the average miss over the previous 26 weeks. The model stays well below the standard guess."),
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
.muted{color:var(--muted)}.big{font-size:2rem;font-weight:700;color:var(--warm);line-height:1.2;margin-bottom:6px}
ol{padding-left:22px}ol li{margin:8px 0}
.explain{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 20px;margin:0 0 8px}
.explain h3{margin:0 0 4px;font-size:1.05rem}.explain ul{margin:0}
.tablewrap{overflow-x:auto}table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums;font-size:.95rem}
th,td{padding:8px 10px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}
th:first-child,td:first-child{text-align:left}th{white-space:normal;vertical-align:bottom}th{color:var(--muted);font-weight:600}
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
    wf = pd.read_csv(src / "weekly_features.csv", usecols=["week_ending", "storage_bcf"], parse_dates=["week_ending"]).dropna()
    level, level_week = wf["storage_bcf"].iloc[-1], wf["week_ending"].iloc[-1]
    hold_from = pd.Timestamp(info.get("holdout_from", config.HOLDOUT_START))
    chosen_on = info.get("chosen_on", f"{first:%Y}-{hold_from.year - 1}")
    summer_head = "Summer is harder to beat."
    summer = (f"From April to October the model misses by {sum_b:.0f} Bcf; the standard guess misses by {sum_a:.0f}. "
              "Summer weeks swing less, so the standard guess is already closer, and summer storage also depends on "
              "things the model doesn't see, like gas exports and power-plant demand.")

    for f, *_ in CHARTS:
        shutil.copy(src / f, dest / "img" / f)

    plain = {"5-year average": "Standard guess (5-year average)",
             "Weather-adjusted 5-yr avg": "5-year average, adjusted for weather",
             "Gradient boosting": "Gradient-boosted trees", "Ridge regression": "Ridge regression",
             "Same week last year": "Same week last year", "Last week's change": "Same as last week"}
    plain[best] = f"My model ({best.lower()})"
    rows = "".join(
        f"<tr{' class=best' if name == best else ''}><td>{html.escape(plain.get(name, name))}</td>"
        f"<td>{_fmt(r['MAE (Bcf)'])}</td><td>{_fmt(r['beats 5-yr avg (% of weeks)'], 0)}%</td>"
        f"<td>{_fmt(r['surprise direction right (%)'], 0)}{'%' if pd.notna(r['surprise direction right (%)']) else ''}</td>"
        f"<td>{_fmt(r['80% range covered (%)'], 0)}%</td></tr>"
        for name, r in pd.concat([a.loc[[best]], a.drop(index=best)]).iterrows())

    now_html = ""
    if now is not None and not now.empty:
        items = []
        # Only the next report EIA will publish. Later weeks rest entirely on weather forecasts.
        for wk, g in list(now.groupby("week_ending"))[:1]:
            r = g[g["model"] == best].iloc[0]
            verb = "added to" if r["pred"] >= 0 else "taken out of"
            items.append(
                f"<div class=big>{abs(r['pred']):.0f} Bcf {verb} storage</div>"
                f"<p>Prediction for the week ending <b>{wk:%A, %B %-d}</b>. EIA publishes the real number on "
                f"<b>{wk + pd.Timedelta(days=6):%A, %B %-d} at 10:30 a.m. ET</b>.</p>"
                f"<p class=muted>Likely range: {r['lower']:+.0f} to {r['upper']:+.0f} Bcf. "
                f"The standard guess (5-year average) is {r['avg5']:+.0f} Bcf.</p>")
        now_html = ("<h2>This week's prediction</h2><div class=now>" + "".join(items) +
                    "<p class=muted style='margin:0'>Some of the week's weather is still a forecast, "
                    "so the real range is a little wider.</p></div>")

    flagged = "".join(f"<li><b>Week ending {r['week_ending']:%b %-d, %Y}</b>: EIA reported {r['detail'].split(' Bcf vs model ')[0].replace('EIA ', '')} Bcf; "
                      f"the model predicted {r['detail'].split(' Bcf vs model ')[1].split(' (')[0]} Bcf.</li>"
                      for _, r in q[q["check"] == "unexplained change"].iterrows())

    figs = "".join(f"<figure><img src='img/{f}' alt='{html.escape(t)}' loading=lazy>"
                   f"<figcaption>{c}</figcaption></figure>" for f, t, c in CHARTS)
    repo = f" · <a href='{REPO_URL}'>Code on GitHub</a>" if REPO_URL else ""

    page = f"""<!doctype html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>Gas Storage Predictions</title><style>{CSS}</style></head><body><main>
<h1>Predicting the weekly US natural gas storage number</h1>
<p class=lede>Every Thursday, the US Energy Information Administration (EIA) reports how much natural gas was
added to or taken out of underground storage the week before. Gas prices jump when the number surprises traders.
This project predicts the number from the weather before EIA publishes it.</p>
<div class=explain><h3>What the numbers mean</h3><ul>
<li><b>Bcf</b> means <b>billion cubic feet</b> of natural gas. One Bcf is enough to heat about 15,000 US homes for a year.
The whole country uses about 90 Bcf a day.</li>
<li>US underground storage holds about <b>{level:,.0f} Bcf</b> right now (week ending {level_week:%B %-d}).</li>
<li><b>Positive numbers</b> mean gas was <b>added</b> to storage, usually April to October: a normal week is +50 to +100 Bcf.
<b>Negative numbers</b> mean gas was <b>taken out</b>, usually in winter: a cold week can be −200 Bcf or more.</li>
<li>The <b>standard guess</b> is the average change for the same week over the past five years. It's the number every storage report is compared with.</li>
</ul></div>
{now_html}
<h2>How accurate is it?</h2>
<div class=tiles>
<div class=tile><div class=v>{b['MAE (Bcf)']:.0f} Bcf</div><div class=l>typical miss each week</div></div>
<div class=tile><div class=v>{avg['MAE (Bcf)']:.0f} Bcf</div><div class=l>typical miss of the standard guess</div></div>
<div class=tile><div class=v>{b['surprise direction right (%)']:.0f}%</div><div class=l>of weeks it correctly said whether the real number would beat the standard guess</div></div>
<div class=tile><div class=v>{int(b['weeks'])}</div><div class=l>weeks tested ({hold_from:%Y} to {last:%Y}), none used to build the model</div></div>
</div>
<p class=muted>Every prediction was made using only data available before that week's report. The model was designed
using {chosen_on} only, and the scores above come from {hold_from:%Y} onward, so they show how it does on weeks it has never seen.</p>

<h2>How it works</h2>
<ol>
<li><b>Measure the weather.</b> Daily temperatures from 17 US cities show how cold or hot each week was. Cold weeks
count most in the gas-heated North-East and Midwest; hot weeks count most in Texas, the South and California, where
power plants burn gas for air conditioning.</li>
<li><b>Start from the standard guess.</b> The average for the same week over the past five years.</li>
<li><b>Adjust for the weather.</b> A model learns how much colder or hotter than normal weather moves storage away
from the standard guess, using every past week.</li>
<li><b>Test it fairly.</b> Each week is predicted using only earlier data, as if it were that Thursday morning.</li>
</ol>

<h2>Every method compared</h2>
<p class=muted>Weeks from {hold_from:%Y} onward. "Typical miss" is the average gap between the prediction and the real number.
"Beat the standard guess" is the share of weeks it was closer than the 5-year average. "Higher or lower right" is how often it
correctly said whether the real number would come in above or below the standard guess. "Inside likely range" should be about 80%.</p>
<div class=tablewrap><table><thead><tr><th>Method</th><th>Typical miss (Bcf)</th><th>Beat the standard guess</th>
<th>Higher or lower right</th><th>Inside likely range</th></tr></thead><tbody>{rows}</tbody></table></div>

<h2>What I found</h2>
<ul>
<li><b>Winter is where weather matters most.</b> From November to March the model misses by {win_b:.0f} Bcf on average;
the standard guess misses by {win_a:.0f}. Cold snaps cause the big swings, and the temperature data catches them.</li>
<li><b>{summer_head}</b> {summer}</li>
<li><b>Simple beat fancy.</b> A straightforward linear model (ridge regression) beat a more complex one (gradient-boosted trees).</li>
<li><b>Big misses point to real events.</b> The largest was February 2021, Winter Storm Uri: frozen gas wells cut
supply, so storage fell much further than the cold alone would suggest.</li>
</ul>

<h2>Weeks the weather couldn't explain</h2>
<p class=muted>Weeks where the model missed far more than usual. These usually come from events the weather can't
show, like frozen wells, pipeline outages, or EIA reclassifying gas.</p>
<ul>{flagged}</ul>

<h2>Charts</h2>
{figs}
<footer>Updated automatically every day after EIA's report. Data: EIA weekly working gas in storage (Lower 48 states)
and Open-Meteo temperatures. Built with Python, pandas and scikit-learn{repo}.</footer>
</main></body></html>"""
    (dest / "index.html").write_text(page)
    return str(dest / "index.html")
