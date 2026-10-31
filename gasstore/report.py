"""Scores, charts and a plain-English summary."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from . import config  # noqa: E402
from .models import BENCHMARKS, MODELS  # noqa: E402

MODEL_NAMES = [M.name for M in MODELS]


def score(g: pd.DataFrame) -> dict:
    err = g["pred"] - g["actual"]
    bench = (g["avg5"] - g["actual"]).abs()
    surprise = g["actual"] - g["avg5"]
    called = g["pred"] - g["avg5"]
    big = surprise.abs() >= 5  # ignore weeks that were basically on the average
    inside = g["actual"].between(g["lower"], g["upper"])
    has_iv = g["lower"].notna()
    return {
        "weeks": len(g),
        "MAE (Bcf)": err.abs().mean(),
        "RMSE (Bcf)": np.sqrt((err ** 2).mean()),
        "bias (Bcf)": err.mean(),
        "beats 5-yr avg (% of weeks)": 100 * (err.abs() < bench).mean(),
        "surprise direction right (%)": (100 * (np.sign(surprise[big]) == np.sign(called[big])).mean()
                                         if called.abs().sum() > 0 else np.nan),  # the 5-yr avg calls no surprise
        "80% range covered (%)": 100 * inside[has_iv].mean() if has_iv.any() else np.nan,
    }


def metrics(pred: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (model, season), g in pd.concat([pred, pred.assign(season="all year")]).groupby(["model", "season"]):
        rows.append({"model": model, "season": season, **score(g)})
    m = pd.DataFrame(rows)
    order = {n: i for i, n in enumerate(MODEL_NAMES + list(BENCHMARKS))}
    return m.sort_values(["season", "model"], key=lambda c: c.map(order) if c.name == "model" else c)


def consensus_compare(pred: pd.DataFrame, best: str) -> pd.DataFrame | None:
    """If you've filled in data/consensus.csv (week_ending,consensus_bcf) from
    news surveys, compare the model with what analysts expected."""
    f = config.DATA / "consensus.csv"
    if not f.exists():
        return None
    c = pd.read_csv(f, parse_dates=["week_ending"]).dropna()
    if c.empty:
        return None
    g = pred[pred["model"] == best].merge(c, on="week_ending")
    if g.empty:
        return None
    return pd.DataFrame([{
        "weeks": len(g),
        "model MAE": (g["pred"] - g["actual"]).abs().mean(),
        "consensus MAE": (g["consensus_bcf"] - g["actual"]).abs().mean(),
        "model closer (% of weeks)": 100 * ((g["pred"] - g["actual"]).abs()
                                             < (g["consensus_bcf"] - g["actual"]).abs()).mean(),
    }])


def _save(fig, path):
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def charts(df, pred, m, best, out: Path):
    plt.rcParams.update({"axes.spines.top": False, "axes.spines.right": False, "font.size": 10})
    blue, grey, orange = "#2a6fdb", "#9aa3ad", "#e07b39"

    # 1. Last two years: actual vs model vs 5-yr average.
    g = pred[pred["model"] == best].sort_values("week_ending")
    g = g[g["week_ending"] >= g["week_ending"].max() - pd.DateOffset(years=2)]
    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.fill_between(g["week_ending"], g["lower"], g["upper"], color=blue, alpha=0.15, label="80% range")
    ax.plot(g["week_ending"], g["avg5"], color=grey, lw=1.3, ls="--", label="5-year average")
    ax.plot(g["week_ending"], g["pred"], color=blue, lw=1.6, label=f"{best} (made before release)")
    ax.scatter(g["week_ending"], g["actual"], s=10, color="black", zorder=3, label="EIA actual")
    ax.axhline(0, color="black", lw=0.5)
    ax.set_ylabel("Weekly storage change (Bcf)")
    ax.set_title("Weekly storage change: forecast vs actual, last two years")
    ax.legend(frameon=False, fontsize=8, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.08))
    _save(fig, out / "forecast_vs_actual.png")

    # 2. Weather drives the number.
    lab = df[df["change_bcf"].notna() & df["hdd"].notna()]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    for ax, col, name in [(axes[0], "hdd", "Heating degree days (week)"),
                          (axes[1], "cdd", "Cooling degree days (week)")]:
        sub = lab[lab["season"] == ("withdrawal" if col == "hdd" else "injection")]
        sc = ax.scatter(sub[col], sub["change_bcf"], c=sub["week_ending"].dt.year, s=8, cmap="viridis")
        ax.set_xlabel(name)
        ax.set_ylabel("Storage change (Bcf)")
    axes[0].set_title("Winter: colder week, bigger withdrawal")
    axes[1].set_title("Summer: hotter week, smaller injection")
    fig.colorbar(sc, ax=axes, label="Year", fraction=0.03)
    fig.savefig(out / "weather_vs_storage.png", dpi=130, bbox_inches="tight")
    plt.close(fig)

    # 3. Error by model and season.
    mm = m[m["season"] != "all year"].pivot(index="model", columns="season", values="MAE (Bcf)")
    mm = mm.loc[[n for n in MODEL_NAMES + list(BENCHMARKS) if n in mm.index]]
    fig, ax = plt.subplots(figsize=(10, 4))
    y = np.arange(len(mm))
    ax.barh(y - 0.2, mm["withdrawal"], height=0.4, color=blue, label="Winter (Nov-Mar)")
    ax.barh(y + 0.2, mm["injection"], height=0.4, color=orange, label="Summer (Apr-Oct)")
    ax.set_yticks(y, mm.index)
    ax.invert_yaxis()
    ax.set_xlabel("Average miss (Bcf), lower is better")
    ax.set_title("How far off each method is, by season")
    ax.legend(frameon=False)
    _save(fig, out / "error_by_model.png")

    # 4. Errors over time: is the model drifting?
    fig, ax = plt.subplots(figsize=(10, 3.6))
    for name, color in [(best, blue), ("5-year average", grey)]:
        e = pred[pred["model"] == name].sort_values("week_ending")
        ax.plot(e["week_ending"], (e["pred"] - e["actual"]).abs().rolling(26, min_periods=8).mean(),
                color=color, lw=1.6, label=name)
    ax.set_ylabel("Average miss, last 26 weeks (Bcf)")
    ax.set_title("Is the forecast getting worse over time?")
    ax.legend(frameon=False)
    _save(fig, out / "error_over_time.png")


def summary(m, best, now, quality, cons, mode, out: Path, last_week, m_hold=None):
    """Headline numbers come from the holdout years (2022 on), which played no part in any
    modelling choice. The full 2018-on table is shown too."""
    head = m_hold if m_hold is not None and len(m_hold) else m
    a = head[(head["season"] == "all year")].set_index("model")
    b, avg = a.loc[best], a.loc["5-year average"]
    full = m[(m["season"] == "all year")].set_index("model")
    cols = ["MAE (Bcf)", "RMSE (Bcf)", "bias (Bcf)", "beats 5-yr avg (% of weeks)",
            "surprise direction right (%)", "80% range covered (%)"]
    period = (f"{config.HOLDOUT_START[:4]} onward, {int(b['weeks'])} weeks the model choices never saw"
              if head is m_hold else f"{config.TEST_START[:4]} onward, {int(b['weeks'])} weeks")
    lines = [
        f"# Natural gas storage nowcast: results ({mode} data)", "",
        f"Last EIA week in the data: **{last_week:%Y-%m-%d}**. Every forecast was made using only "
        "information available before that week's release (walk-forward). The model was chosen "
        f"on {config.TEST_START[:4]}-{int(config.HOLDOUT_START[:4]) - 1}; the headline is scored on {period}.", "",
        "## Headline", "",
        f"- Best model: **{best}**, average miss **{b['MAE (Bcf)']:.1f} Bcf** a week, "
        f"vs **{avg['MAE (Bcf)']:.1f} Bcf** for the 5-year average "
        f"({100 * (1 - b['MAE (Bcf)'] / avg['MAE (Bcf)']):.0f}% smaller).",
        f"- Beat the 5-year average in **{b['beats 5-yr avg (% of weeks)']:.0f}%** of weeks.",
        f"- Called the direction of the surprise vs the 5-year average correctly in "
        f"**{b['surprise direction right (%)']:.0f}%** of weeks.",
        f"- The 80% range contained the real number **{b['80% range covered (%)']:.0f}%** of the time.",
        "", f"## All methods, {period}", "", a[cols].round(1).to_markdown(), "",
        f"## All methods, {config.TEST_START[:4]} onward", "", full[cols].round(1).to_markdown(), "",
    ]
    if now is not None and not now.empty:
        lines += ["## Nowcast for weeks EIA hasn't released yet", ""]
        for wk, g in now.groupby("week_ending"):
            r = g[g["model"] == best].iloc[0]
            fc = int(r["forecast_days"])
            note = f" ({fc} of 7 days use forecast weather, so less certain)" if fc else ""
            lines.append(f"- Week ending **{wk:%a %b %d, %Y}**: **{r['pred']:+.0f} Bcf** "
                         f"(80% range {r['lower']:+.0f} to {r['upper']:+.0f}); "
                         f"5-year average {r['avg5']:+.0f}{note}. "
                         f"EIA releases it {wk + pd.Timedelta(days=6):%a %b %d}.")
        lines.append("")
    if cons is not None:
        c = cons.iloc[0]
        lines += ["## Model vs analyst consensus", "",
                  f"Over {int(c['weeks'])} weeks from data/consensus.csv: model miss "
                  f"{c['model MAE']:.1f} Bcf vs consensus {c['consensus MAE']:.1f} Bcf; "
                  f"model closer in {c['model closer (% of weeks)']:.0f}% of weeks.", ""]
    else:
        lines += ["## Model vs analyst consensus", "",
                  "Not compared yet. Fill in data/consensus.csv with the survey numbers "
                  "reported in the news each Wednesday to add this.", ""]
    counts = quality["check"].value_counts()
    lines += ["## Data checks", "",
              ("No problems found." if counts.empty else
               "\n".join(f"- {k}: {v}" for k, v in counts.items()) +
               "\n\nDetails in quality.csv."), ""]
    (out / "summary.md").write_text("\n".join(lines))
    return "\n".join(lines)
