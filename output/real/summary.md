# Natural gas storage nowcast: results (real data)

Last EIA week in the data: **2026-10-23**. Test period: 2018-01-01 onward, 460 weeks, every forecast made using only information available before that week's release.

## Headline

- Best model: **Ridge regression**, average miss **17.4 Bcf** a week, vs **30.2 Bcf** for the 5-year average (42% smaller).
- Beat the 5-year average in **62%** of weeks.
- Called the direction of the surprise vs the 5-year average correctly in **79%** of weeks.
- The 80% range contained the real number **76%** of the time.

## All methods (whole year)

| model                     |   MAE (Bcf) |   RMSE (Bcf) |   bias (Bcf) |   beats 5-yr avg (% of weeks) |   surprise direction right (%) |   80% range covered (%) |
|:--------------------------|------------:|-------------:|-------------:|------------------------------:|-------------------------------:|------------------------:|
| Weather-adjusted 5-yr avg |        20.2 |         26.1 |         -2.9 |                          58   |                           74.7 |                    75.6 |
| Ridge regression          |        17.4 |         22.3 |         -6.9 |                          61.7 |                           79   |                    75.6 |
| Gradient boosting         |        17.9 |         24.2 |         -1.8 |                          65.7 |                           79.7 |                    75.3 |
| 5-year average            |        30.2 |         44.3 |         -0.6 |                           0   |                          nan   |                    77.6 |
| Same week last year       |        39.7 |         58.2 |         -0.1 |                          37.6 |                           51.4 |                    75.6 |
| Last week's change        |        34.8 |         52.1 |         -0.6 |                          42.8 |                           63.8 |                    76.5 |

## Nowcast for weeks EIA hasn't released yet

- Week ending **Fri Oct 30, 2026**: **+85 Bcf** (80% range +71 to +111); 5-year average +70 (5 of 7 days use forecast weather, so less certain). EIA releases it Thu Nov 05.

## Model vs analyst consensus

Not compared yet. Fill in data/consensus.csv with the survey numbers reported in the news each Wednesday to add this.

## Data checks

- unexplained change: 6

Details in quality.csv.
