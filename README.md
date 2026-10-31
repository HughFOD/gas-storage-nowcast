# Natural gas storage nowcast

Every Thursday at 10:30 ET the US Energy Information Administration (EIA) publishes how much natural gas went into or out of underground storage in the Lower 48 the week before. It is one of the most closely watched numbers in energy markets: when it comes in different from what traders expected, natural gas futures move within seconds.

This project predicts that number before it is released, using only information a trader would have on Thursday morning, then checks how those predictions would actually have done since 2018.

## The idea

Most of the week-to-week swing in storage is weather:

- **Winter:** a colder week means more gas burned for heating, so a bigger **withdrawal**. Measured with *heating degree days* (HDD): how far each day's average temperature fell below 65 °F.
- **Summer:** a hotter week means more air conditioning, more gas burned in power plants, and a smaller **injection**. Measured with *cooling degree days* (CDD).

The weather for the report week has already happened by Thursday, so it is fair game. The models turn temperatures in 17 cities into weighted HDD and CDD (heating weights lean North-East/Midwest, cooling weights lean Texas/South/California), then combine them with the market's standard reference point, the **5-year average** change for that week, and with last week's report.

## Methods compared

| Method | What it does |
|---|---|
| 5-year average | The benchmark quoted in every storage report. |
| Same week last year | Last year's number for this week. |
| Last week's change | Assumes this week looks like last week. |
| Weather-adjusted 5-yr avg | 5-year average plus a correction for colder/hotter than normal. Learns only from the last 3 years, because the market keeps changing (LNG exports, more gas-fired power). |
| Ridge regression | Linear model on all features. |
| Gradient boosting | Trees that can learn that extra cold in January matters differently from extra cold in October. |

## How it is tested

**Walk-forward:** to predict a given week, each model is trained only on earlier weeks, as if it were that Thursday morning. Then the real number is revealed and it moves on a week. Every result below was made this way. Automated tests check that no feature can depend on the number being predicted, that the walk-forward loop never trains on the future, and that prediction ranges are built only from errors already known at the time.

Scores reported for each method: average miss (Bcf), how often it beats the 5-year average, how often it calls the *direction* of the surprise against the 5-year average (what moves prices), and whether the 80% range really contains the actual number 80% of the time.

**Data checks** (in `quality.csv`): missing weeks, weeks the weather can't explain (often EIA reclassifications, revisions, or real events like LNG plant outages), out-of-range values, and gaps in the weather data.

## Findings

**How the test was kept honest.** Every forecast is walk-forward: to predict a week, the models are trained only on earlier weeks. On top of that, every modelling choice (which features, which model) was made looking only at 2018-2021. The numbers below are for **2022 to October 2026 (251 weeks)**, which played no part in those choices.

| Method | Avg miss (Bcf) | Winter miss | Summer miss | Surprise direction right |
|---|---:|---:|---:|---:|
| **Ridge regression** | **13.1** | **15.4** | **11.6** | **86%** |
| Gradient boosting | 16.2 | 20.9 | 13.1 | 83% |
| Weather-adjusted 5-yr avg | 18.3 | 21.1 | 16.4 | 80% |
| 5-year average | 31.4 | 53.9 | 16.7 | – |
| Last week's change | 35.2 | 61.1 | 18.4 | 65% |
| Same week last year | 40.1 | 70.2 | 20.6 | 53% |

- **The best model's average miss is 58% smaller than the 5-year average's** (13 vs 31 Bcf), and it calls whether the report comes in above or below the 5-year average correctly 86% of the time.
- **Winter is where weather pays off most:** 15 Bcf vs 54 for the 5-year average. Cold snaps cause the big swings, and they show up in temperature data.
- **Summer was the first version's weak spot** (it barely beat the 5-year average). Adding last week's weather, curvature for extreme cold and heat, and season-aware weather effects brought the summer miss to 12 Bcf vs 17.
- **Simple beat fancy.** Ridge regression beat gradient-boosted trees on both the years used to choose it and the later years.
- **The 80% ranges are honest:** they contained the real number 80% of the time.
- **Misses point to real events.** The largest was February 2021 (Winter Storm Uri): EIA reported −338 Bcf vs the model's −257, because freezing wells cut production on top of the cold. Such weeks are listed in `quality.csv`.

The website updates itself every day after EIA's release (see `.github/workflows/update.yml`), so its numbers and the latest nowcast stay current.

**Live test:** the week ending Oct 30, 2026 was forecast before EIA's Nov 5 release at about **+83 Bcf** (5-year average +70). *Add the actual number here once it's out.*

Project website: **https://hughfod.github.io/gas-storage-nowcast/**

## Analyst consensus (optional)

The real test is beating the analyst survey published by news outlets each Wednesday. Those numbers aren't free to download in bulk, so add them by hand to `data/consensus.csv` (`week_ending,consensus_bcf`) as the weeks go by. The results will then include a model vs consensus comparison.

## Running it (PyCharm)

1. `step1_setup.py`: one-time install.
2. `step2_run_demo.py`: runs everything on made-up data, no internet needed.
3. `step3_run_real_data.py`: downloads real data and makes this week's nowcast. Re-run weekly.
4. `step4_run_tests.py`: runs the automated checks.
5. `step5_build_website.py`: rebuilds the website in `docs/` from the latest results.

On GitHub, a scheduled workflow runs step 3 and step 5 every day and publishes the result.

Results go to `output/real/`: `summary.md`, `nowcast.csv`, `metrics.csv`, `predictions.csv`, `quality.csv`, and charts.

## Data sources (free, no key)

- EIA weekly working gas in storage, Lower 48 (series `NW2_EPG0_SWO_R48_BCF`), from 2010.
- Daily mean temperatures from the [Open-Meteo](https://open-meteo.com/) historical archive and forecast APIs, from 2000.

## Limitations

- City weights are hand-set approximations, not official gas-customer weights.
- Storage change is computed as the difference in reported levels, which differs from EIA's "implied flow" in weeks with reclassifications.
- Nowcasts for weeks still in progress use forecast weather, so they are less certain than the ranges suggest.
- Weather is not the only driver: production, LNG exports, pipeline exports to Mexico and outages also matter, and are not in the model yet.
