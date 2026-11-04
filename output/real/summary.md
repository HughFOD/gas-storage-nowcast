# Natural gas storage nowcast: results (analyze data)

Last EIA week in the data: **2026-10-23**. Every forecast was made using only information available before that week's release (walk-forward). The model was chosen on 2018-2021; the headline is scored on 2022 onward, 251 weeks the model choices never saw.

## Headline

- Best model: **Ridge regression**, average miss **13.1 Bcf** a week, vs **31.4 Bcf** for the 5-year average (58% smaller).
- Beat the 5-year average in **73%** of weeks.
- Called the direction of the surprise vs the 5-year average correctly in **86%** of weeks.
- The 80% range contained the real number **80%** of the time.

## All methods, 2022 onward, 251 weeks the model choices never saw

| model                     |   MAE (Bcf) |   RMSE (Bcf) |   bias (Bcf) |   beats 5-yr avg (% of weeks) |   surprise direction right (%) |   80% range covered (%) |
|:--------------------------|------------:|-------------:|-------------:|------------------------------:|-------------------------------:|------------------------:|
| Weather-adjusted 5-yr avg |        18.3 |         23.9 |         -2.1 |                          63.7 |                           79.7 |                    76.1 |
| Ridge regression          |        13.1 |         17   |         -4.3 |                          72.5 |                           86.2 |                    80.5 |
| Gradient boosting         |        16.2 |         21.5 |         -2.8 |                          69.3 |                           82   |                    73.3 |
| 5-year average            |        31.4 |         45.5 |          0.1 |                           0   |                          nan   |                    76.5 |
| Same week last year       |        40.1 |         59.7 |          0.1 |                          39   |                           53   |                    77.7 |
| Last week's change        |        35.2 |         53.6 |         -0.4 |                          45.8 |                           64.5 |                    75.7 |

## All methods, 2018 onward

| model                     |   MAE (Bcf) |   RMSE (Bcf) |   bias (Bcf) |   beats 5-yr avg (% of weeks) |   surprise direction right (%) |   80% range covered (%) |
|:--------------------------|------------:|-------------:|-------------:|------------------------------:|-------------------------------:|------------------------:|
| Weather-adjusted 5-yr avg |        20.2 |         26.1 |         -2.9 |                          58   |                           74.7 |                    75.6 |
| Ridge regression          |        14.5 |         18.4 |         -5.3 |                          69.6 |                           85.1 |                    78.6 |
| Gradient boosting         |        17.8 |         24.2 |         -2.4 |                          65.9 |                           80.5 |                    76   |
| 5-year average            |        30.2 |         44.3 |         -0.6 |                           0   |                          nan   |                    77.6 |
| Same week last year       |        39.7 |         58.2 |         -0.1 |                          37.6 |                           51.4 |                    75.6 |
| Last week's change        |        34.8 |         52.1 |         -0.6 |                          42.8 |                           63.8 |                    76.5 |

## Nowcast for weeks EIA hasn't released yet

- Week ending **Fri Oct 30, 2026**: **+83 Bcf** (80% range +77 to +107); 5-year average +70 (1 of 7 days use forecast weather, so less certain). EIA releases it Thu Nov 05.
- Week ending **Fri Nov 06, 2026**: **+74 Bcf** (80% range +68 to +97); 5-year average +33 (7 of 7 days use forecast weather, so less certain). EIA releases it Thu Nov 12.

## Model vs analyst consensus

Not compared yet. Fill in data/consensus.csv with the survey numbers reported in the news each Wednesday to add this.

## Data checks

- unexplained change: 7

Details in quality.csv.
