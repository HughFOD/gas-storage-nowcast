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

Walk-forward test, January 2018 to October 2026 (460 weeks):

| Method | Avg miss (Bcf) | Winter miss | Summer miss | Surprise direction right |
|---|---:|---:|---:|---:|
| **Ridge regression** | **17.4** | **18.8** | 16.5 | 79% |
| Gradient boosting | 17.9 | 22.9 | **14.5** | 80% |
| Weather-adjusted 5-yr avg | 20.2 | 24.0 | 17.6 | 75% |
| 5-year average | 30.2 | 49.1 | 17.3 | – |
| Last week's change | 34.8 | 58.1 | 18.9 | 64% |
| Same week last year | 39.7 | 64.4 | 22.9 | 51% |

- **The best model's average miss is 42% smaller than the 5-year average's** (17 vs 30 Bcf), and it calls whether the report will come in above or below the 5-year average correctly 79% of the time.
- **Winter is where weather pays off:** a 19 Bcf average miss vs 49 for the 5-year average. Cold snaps cause most of the big swings, and they show up in temperature data.
- **Summer is harder:** the models barely beat the 5-year average. Summer storage depends more on things not in the model yet (LNG exports, power-sector demand, production), which is the obvious next step.
- **Simple beat fancy overall.** Ridge regression edged out gradient boosting for the year, though the trees were better in summer.
- **It has improved over time:** ridge's average miss fell from about 21 Bcf in 2018 to 13 Bcf in 2026 so far, as more training years accumulated.
- **The 80% ranges are honest:** they contained the real number 76% of the time.
- **Misses point to real events.** The largest was February 2021 (Winter Storm Uri): EIA reported −338 Bcf vs the model's −257, because freezing wells cut production on top of the cold. Six such weeks are listed in `quality.csv`.

**Live test:** the week ending Oct 30, 2026 was forecast at **+85 Bcf** (80% range +71 to +111; 5-year average +70) before EIA's release on Nov 5. *Add the actual number here once it's out.*

Project website: **https://hughfod.github.io/gas-storage-nowcast/**

## Analyst consensus (optional)

The real test is beating the analyst survey published by news outlets each Wednesday. Those numbers aren't free to download in bulk, so add them by hand to `data/consensus.csv` (`week_ending,consensus_bcf`) as the weeks go by. The results will then include a model vs consensus comparison.

## Running it (PyCharm)

1. `step1_setup.py`: one-time install.
2. `step2_run_demo.py`: runs everything on made-up data, no internet needed.
3. `step3_run_real_data.py`: downloads real data and makes this week's nowcast. Re-run weekly.
4. `step4_run_tests.py`: runs the automated checks.
5. `step5_build_website.py`: rebuilds the website in `docs/` from the latest results.

Results go to `output/real/`: `summary.md`, `nowcast.csv`, `metrics.csv`, `predictions.csv`, `quality.csv`, and charts.

## Data sources (free, no key)

- EIA weekly working gas in storage, Lower 48 (series `NW2_EPG0_SWO_R48_BCF`), from 2010.
- Daily mean temperatures from the [Open-Meteo](https://open-meteo.com/) historical archive and forecast APIs, from 2000.

## Limitations

- City weights are hand-set approximations, not official gas-customer weights.
- Storage change is computed as the difference in reported levels, which differs from EIA's "implied flow" in weeks with reclassifications.
- Nowcasts for weeks still in progress use forecast weather, so they are less certain than the ranges suggest.
- Weather is not the only driver: production, LNG exports, pipeline exports to Mexico and outages also matter, and are not in the model yet.
