# Natural gas storage nowcast: results (analyze data)

Last EIA week in the data: **2026-10-30**. Every forecast was made using only information available before that week's release (walk-forward). The model was chosen on 2018-2021; the headline is scored on 2022 onward, 252 weeks the model choices never saw.

## Headline

- Best model: **Ridge regression**, average miss **13.1 Bcf** a week, vs **31.3 Bcf** for the 5-year average (58% smaller).
- Beat the 5-year average in **73%** of weeks.
- Called the direction of the surprise vs the 5-year average correctly in **86%** of weeks.
- The 80% range contained the real number **80%** of the time.

## All methods, 2022 onward, 252 weeks the model choices never saw

| model                     |   MAE (Bcf) |   RMSE (Bcf) |   bias (Bcf) |   beats 5-yr avg (% of weeks) |   surprise direction right (%) |   80% range covered (%) |
|:--------------------------|------------:|-------------:|-------------:|------------------------------:|-------------------------------:|------------------------:|
| Weather-adjusted 5-yr avg |        18.3 |         23.9 |         -2   |                          63.5 |                           79.8 |                    75.8 |
| Ridge regression          |        13.1 |         17   |         -4.3 |                          72.6 |                           86.2 |                    80.2 |
| Gradient boosting         |        16.1 |         21.5 |         -2.8 |                          69   |                           82.1 |                    73.4 |
| 5-year average            |        31.3 |         45.4 |          0.1 |                           0   |                          nan   |                    76.6 |
| Same week last year       |        40.2 |         59.7 |         -0.1 |                          38.9 |                           52.8 |                    77.8 |
| Last week's change        |        35.1 |         53.5 |         -0.4 |                          46   |                           64.7 |                    75.8 |

## All methods, 2018 onward

| model                     |   MAE (Bcf) |   RMSE (Bcf) |   bias (Bcf) |   beats 5-yr avg (% of weeks) |   surprise direction right (%) |   80% range covered (%) |
|:--------------------------|------------:|-------------:|-------------:|------------------------------:|-------------------------------:|------------------------:|
| Weather-adjusted 5-yr avg |        20.2 |         26.1 |         -2.9 |                          57.9 |                           74.7 |                    75.4 |
| Ridge regression          |        14.5 |         18.4 |         -5.3 |                          69.6 |                           85.1 |                    78.4 |
| Gradient boosting         |        17.8 |         24.2 |         -2.3 |                          65.7 |                           80.6 |                    76.1 |
| 5-year average            |        30.1 |         44.2 |         -0.6 |                           0   |                          nan   |                    77.7 |
| Same week last year       |        39.7 |         58.2 |         -0.2 |                          37.5 |                           51.3 |                    75.6 |
| Last week's change        |        34.7 |         52   |         -0.6 |                          43   |                           63.9 |                    76.6 |

## Nowcast for weeks EIA hasn't released yet

- Week ending **Fri Nov 06, 2026**: **+72 Bcf** (80% range +65 to +95); 5-year average +33 (7 of 7 days use forecast weather, so less certain). EIA releases it Thu Nov 12.

## Model vs analyst consensus

Not compared yet. Fill in data/consensus.csv with the survey numbers reported in the news each Wednesday to add this.

## Data checks

- unexplained change: 7

Details in quality.csv.
