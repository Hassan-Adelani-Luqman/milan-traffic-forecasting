# Results summary

Every measured number, grouped by report section, each traceable to the
artefact it came from. Facts only: no interpretation, because the
interpretation is the author's work.

Regenerate with `python -m src.export_report`.

---

## Dataset and Data Preparation

### Ingest run (source: `ingest_summary.json`, `ingest_log.csv`)

- Days processed: **62** (2013-11-01 to 2014-01-01)
- Raw rows parsed: **319,896,289**
- Download: **5.92 min** total, 5.73 s/day +/- 0.64
- Ingest: **1.54 min** total, 1.49 s/day +/- 0.1
- Peak RSS: 574 MiB max, 325.8 MiB mean
- Absent cells: **34,682** total, 559.4/day mean, max 2267 on 2013-12-26

### Memory strategies (source: `memory_report.csv`)

| strategy | day | resident | peak RSS | wall | extrapolated |
|---|---|---|---|---|---|
| naive_pandas | 2013-11-01 | 295.57 MiB | 633.06 MiB | 5.56 s | True |
| pandas_chunked | 2013-11-01 | 5.49 MiB | 166.99 MiB | 5.82 s | False |
| polars_lazy | 2013-11-01 | 5.49 MiB | 559.74 MiB | 0.86 s | False |
| pandas_chunked | 2013-11-02 | 5.49 MiB | 177.52 MiB | 6.05 s | False |
| polars_lazy | 2013-11-02 | 5.49 MiB | 548.94 MiB | 0.88 s | False |
| pandas_chunked | 2013-11-03 | 5.49 MiB | 173.12 MiB | 5.71 s | False |
| polars_lazy | 2013-11-03 | 5.49 MiB | 547.97 MiB | 1.11 s | False |

- Holding all 62 days the naive way: **17.90 GiB** resident (extrapolated from one day, not executed).
- Both optimised paths hold one 5.49 MiB block at a time, independent of the number of days.
- Final matrix: 8928 x 10000 float32 = **340.58 MiB**.

### Assembled matrix (source: `data/processed/matrix_report.json`)

- Shape: **(8928, 10000)**, 62 days
- Local range: 2013-11-01T00:00:00.000000000 to 2014-01-01T23:50:00.000000000 (Europe/Rome)
- UTC range: 2013-10-31T23:00:00.000000000 to 2014-01-01T22:50:00.000000000
- Missing intervals: **0**; interpolated: 0; left as NaN: 0
- NaN after policy: **0**
- Total activity: 5,552,894,187.94

---

## Exploratory Analysis

### Distribution across the grid (source: `distribution_stats.json`)

- Cells: 10,000; total activity 5,552,894,188
- Mean 555,289; median 277,871; max/median **45.8x**
- Skewness 4.26; kurtosis 25.50
- Gini **0.608**
- Top 1% hold **11.0%**, top 5% 33.6%, top 10% 48.4%; bottom 50% 11.6%
- Cells with zero total: 0
- Lognormal fit: mu=12.496, sigma=1.211, KS=0.0232, p=4.26e-05
  - KS critical value at n=10,000, alpha=0.05 is 0.0136, so the statistic is 1.7x the threshold. log(x) has skewness +0.023 and kurtosis +0.013.

### Study areas (source: `selected_areas.json`)

- Top three by total: **[5161, 5059, 5259]**
- Highest-traffic area: **5161**
- Fixed by the brief: [4159, 4556]
- Forecast in Section 4: **[5161, 4159, 4556]**

| square | rank | total |
|---|---|---|
| 5161 | 1 | 12,740,060 |
| 5059 | 2 | 11,170,854 |
| 5259 | 3 | 10,485,779 |
| 4159 | 424 | 2,454,134 |
| 4556 | 109 | 4,574,671 |

- Squares 5161, 5059 and 5259 lie within **470 m** of one another; the top ten fit inside a 3.05 x 2.35 km box (grid rows 48-60, columns 54-63).

### Per-area characteristics (source: `area_summary.csv`)

| square | rank | mean | CV | peak/trough | night/mean | wknd/wkday |
|---|---|---|---|---|---|---|
| 5161 | 1 | 1,427 | 0.968 | 99.4 | 0.130 | 1.384 |
| 5059 | 2 | 1,251 | 0.768 | 30.9 | 0.235 | 0.861 |
| 5259 | 3 | 1,174 | 0.939 | 47.0 | 0.333 | 0.425 |
| 4159 | 424 | 275 | 0.660 | 14.9 | 0.489 | 0.587 |
| 4556 | 109 | 512 | 0.485 | 17.0 | 0.534 | 1.140 |

### MSTL decomposition, square 5161 (source: `decomposition.json`)

- Periods: [144, 1008]
  - trend: **2.8%** of variance, strength 0.451
  - seasonal_144: **82.9%** of variance, strength 0.959
  - seasonal_1008: **10.0%** of variance, strength 0.746
  - residual: **3.6%** of variance
- Residual std 262.23 against observed std 1381.57 (**19.0%**)

### Stationarity (source: `stationarity.csv`)

| transform | ADF stat | ADF p | KPSS stat | KPSS p | verdict |
|---|---|---|---|---|---|
| raw | -19.03 | 0.0000 | 0.237 | 0.100 | stationary (both agree) |
| first difference | -15.16 | 0.0000 | 0.003 | 0.100 | stationary (both agree) |
| seasonal difference (lag 144) | -11.83 | 0.0000 | 0.069 | 0.100 | stationary (both agree) |

- Note: KPSS p-values are clamped to the tabulated range, so 0.100 means '>= 0.10', not an exact value.
- Note: these tests address stochastic trend only. They do not test whether the mean varies with time of day, which it does strongly.

### Autocorrelation, square 5161 (source: `autocorrelation.json`)

- Lag-1 ACF: **0.9871**
- ACF at lag 144 (one day): **0.8783**
- ACF at lag 1008 (one week): **0.8377**
- Notable lags: [144, 1008, 864, 288, 432, 720, 576]
- Their ACF values: [0.878, 0.838, 0.798, 0.77, 0.741, 0.733, 0.73]

### Dominant cycles (source: `spectral_peaks.csv`)

| period (h) | power |
|---|---|
| 24.00 | 2.097e+09 |
| 12.00 | 1.392e+08 |
| 165.33 | 6.539e+07 |
| 20.96 | 5.535e+07 |
| 28.08 | 4.317e+07 |
| 1488.00 | 3.259e+07 |

### Seasonal-naive anomalies (source: `anomalies.csv`)

- Flagged: **152** intervals, **1.73%** of the 8,784 that can be evaluated (the first day has no seasonal-naive comparison), at z > 4 with the scale estimated per position in the daily cycle
- On holidays: **35/152** (**23.0%**), against 12.9% of days being holidays = **1.78x** enrichment, binomial p = 4.3e-04

Days with the most flagged intervals:

| date | intervals | holiday |
|---|---|---|
| 2013-12-02 | 17 |  |
| 2014-01-01 | 13 | Capodanno (New Year's Day) |
| 2013-12-25 | 9 | Natale (Christmas Day) |
| 2013-11-03 | 8 |  |
| 2013-11-16 | 8 |  |
| 2013-11-25 | 7 |  |
| 2013-11-15 | 6 |  |
| 2013-11-18 | 6 |  |

---

## Methodology

### Protocol

- One-step-ahead (10 minutes), univariate, one model per area, native resolution.
- Inference is `walk_forward` with true observed history, never a recursive rollout.
- Tuning ran on square 5161 only, selecting on validation MAE.
- Transforms are fitted on the training split alone; `LogStandardScaler` raises
  `LeakageError` if asked to refit.
- Final fits use train + validation; the test week is untouched until prediction.

### Selected hyperparameters

| Model | Selection | Value |
|---|---|---|
| harmonic ARIMA | Fourier orders (AICc) | K1=6, K2=2 |
| harmonic ARIMA | ARIMA order (validation MAE) | (3, 0, 1) |
| harmonic ARIMA | AICc | -6096.6 |
| LightGBM | num_leaves | 68 |
| LightGBM | learning_rate | 0.03449 |
| LightGBM | trees after early stopping | 320 of 2000 ceiling |
| LSTM | sequence_length | 144 |
| LSTM | hidden_size x layers | 128 x 2 |
| LSTM | batch_size, learning_rate | 32, 0.001 |
| LSTM | dropout, weight_decay | 0.0, 0.0001 |
| LSTM | best epoch on validation | 10 |

---

## Results

### Test week (16-22 Dec 2013), MASE by area

MASE is the comparable metric: the areas differ by an order of magnitude in
volume, so raw MAE cannot be compared across them. Lower is better.

| model | 5161 | 4159 | 4556 | mean | worst |
|---|---:|---:|---:|---:|---:|
| harmonic_arima | 0.24076 | 0.16643 | 0.23039 | 0.21253 | 0.24076 |
| lightgbm | 0.24926 | 0.18586 | 0.26659 | 0.2339 | 0.26659 |
| persistence | 0.26714 | 0.19497 | 0.25705 | 0.23972 | 0.26714 |
| lstm_ensemble | 0.23257 | 0.25262 | 0.24903 | 0.24474 | 0.25262 |
| lstm | 0.26485 | 0.25856 | 0.25694 | 0.26012 | 0.26485 |
| seasonal_naive | 0.97467 | 0.6256 | 0.6799 | 0.76006 | 0.97467 |

### Square 5161, test week

| model | mae | mae_std | rmse | mape | smape | mase | r2 | n_seeds |
|---|---|---|---|---|---|---|---|---|
| lstm_ensemble | 80.7949 | 0.0 | 124.4857 | 7.6062 | 7.5706 | 0.23257 | 0.99165 | 3 |
| harmonic_arima | 83.6387 | 0.0 | 128.247 | 7.7983 | 7.6727 | 0.24076 | 0.99113 | 1 |
| lightgbm | 86.59 | 0.0 | 130.8902 | 7.9732 | 7.8059 | 0.24926 | 0.99077 | 1 |
| lstm | 92.0057 | 3.0315 | 142.6728 | 8.4759 | 8.4375 | 0.26485 | 0.98899 | 3 |
| persistence | 92.8019 | 0.0 | 134.8778 | 9.1943 | 9.0965 | 0.26714 | 0.99019 | 1 |
| seasonal_naive | 338.5937 | 0.0 | 619.04 | 25.9398 | 22.8281 | 0.97467 | 0.79345 | 1 |

### Square 4159, test week

| model | mae | mae_std | rmse | mape | smape | mase | r2 | n_seeds |
|---|---|---|---|---|---|---|---|---|
| harmonic_arima | 13.6178 | 0.0 | 18.6399 | 6.0572 | 5.9784 | 0.16643 | 0.97662 | 1 |
| lightgbm | 15.2078 | 0.0 | 21.0027 | 6.5535 | 6.3762 | 0.18586 | 0.97032 | 1 |
| persistence | 15.9525 | 0.0 | 21.5444 | 6.9823 | 6.9425 | 0.19497 | 0.96877 | 1 |
| lstm_ensemble | 20.6696 | 0.0 | 29.7422 | 7.8756 | 7.5644 | 0.25262 | 0.94048 | 3 |
| lstm | 21.1556 | 4.5892 | 30.2529 | 8.1101 | 7.7821 | 0.25856 | 0.93637 | 3 |
| seasonal_naive | 51.1873 | 0.0 | 84.6429 | 21.8043 | 20.4862 | 0.6256 | 0.51794 | 1 |

### Square 4556, test week

| model | mae | mae_std | rmse | mape | smape | mase | r2 | n_seeds |
|---|---|---|---|---|---|---|---|---|
| harmonic_arima | 25.8683 | 0.0 | 34.6999 | 5.9343 | 5.8209 | 0.23039 | 0.95454 | 1 |
| lstm_ensemble | 27.9605 | 0.0 | 37.1904 | 6.4238 | 6.2292 | 0.24903 | 0.94778 | 3 |
| lstm | 28.849 | 1.7879 | 37.9591 | 6.7114 | 6.5109 | 0.25694 | 0.94553 | 3 |
| persistence | 28.8616 | 0.0 | 39.621 | 6.5998 | 6.5533 | 0.25705 | 0.94073 | 1 |
| lightgbm | 29.9319 | 0.0 | 39.6601 | 6.9832 | 6.7557 | 0.26659 | 0.94061 | 1 |
| seasonal_naive | 76.3384 | 0.0 | 108.3514 | 17.4582 | 15.8698 | 0.6799 | 0.55675 | 1 |

### Computational cost (square 5161, 1,008 forecasts)

Training times are **not comparable across devices**; the device column says
which produced each number. Hardware is recorded in
`results/environment.json` (local) and `results/environment_final_runs.json`
(the Kaggle T4 session that produced these).

| model | device | n_seeds | train_wall_s | inference_wall_s | inference_ms_per_step | n_params |
|---|---|---|---|---|---|---|
| persistence | cpu | 1 | 0.0 | 0.0002 | 0.0002 | 0 |
| seasonal_naive | cpu | 1 | 0.0 | 0.0 | 0.0 | 0 |
| harmonic_arima | cpu | 1 | 18.011 | 75.2438 | 74.6467 | 22 |
| lstm | cuda | 3 | 9.891 | 0.0412 | 0.0409 | 202369 |
| lightgbm | cpu | 1 | 5.016 | 0.0223 | 0.0221 | 19639 |
| lstm_ensemble | cuda | 3 | 29.673 | 0.1236 | 0.1226 | 607107 |

---

## Discussion and failure analysis

### Collapse-to-persistence check

The lag-1 autocorrelation of the study series is 0.987, so a model can post a
respectable error by repeating its last input. `copy_ratio` is the distance
between the forecast and persistence, divided by how far the series moves
between steps; 0.00 means the two are the same forecast.

`peak_lag` is reported but is **not** the test. A one-step forecast is built
only from data up to t-1, so it cannot contain the innovation at t and will
correlate slightly more with the previous observation than the current one; a
lag-1 peak is what a causal forecast looks like. Seasonal naive is the only
model here peaking at lag 0 and it is the worst forecaster in the study.

| square_id | model | peak_lag | lag_margin | copy_ratio | verdict |
|---|---|---|---|---|---|
| 5161 | persistence | 1 | 0.00419 | 0.0 | collapsed |
| 5161 | seasonal_naive | 0 | -0.0017 | 3.6807 | independent |
| 5161 | harmonic_arima | 1 | 0.00168 | 0.6308 | independent |
| 5161 | lightgbm | 1 | 0.00078 | 0.7845 | independent |
| 5161 | lstm | 1 | 0.00073 | 0.7102 | independent |
| 4159 | persistence | 1 | 0.01493 | 0.0 | collapsed |
| 4159 | seasonal_naive | 0 | -0.0017 | 3.2312 | independent |
| 4159 | harmonic_arima | 1 | 0.00661 | 0.5359 | near-persistence |
| 4159 | lightgbm | 1 | 0.00455 | 0.7652 | independent |
| 4159 | lstm | 1 | 0.00536 | 1.1372 | independent |
| 4556 | persistence | 1 | 0.0296 | 0.0 | collapsed |
| 4556 | seasonal_naive | -1 | -0.00537 | 2.6999 | independent |
| 4556 | harmonic_arima | 1 | 0.01163 | 0.6377 | independent |
| 4556 | lightgbm | 1 | 0.00777 | 0.9273 | independent |
| 4556 | lstm | 1 | 0.00985 | 0.8021 | independent |

### Error by day type (test week)

| square_id | model | weekday_mae | weekend_mae | weekend_penalty | n_weekend |
|---|---|---|---|---|---|
| 5161 | persistence | 88.36353874206543 | 103.89788638220892 | 1.1758004247146383 | 288 |
| 5161 | seasonal_naive | 341.42116078270806 | 331.5251055293613 | 0.9710151086398393 | 288 |
| 5161 | harmonic_arima | 74.96089379570206 | 105.33314535917995 | 1.4051746187319247 | 288 |
| 5161 | lightgbm | 82.64678722680885 | 96.4480543322399 | 1.1669909692624352 | 288 |
| 5161 | lstm | 77.26350291118595 | 89.62353381592669 | 1.1599724376844334 | 288 |
| 4159 | persistence | 17.41085607740614 | 12.306550396813286 | 0.7068320099884893 | 288 |
| 4159 | seasonal_naive | 46.68234527375963 | 62.44984255896674 | 1.337761464055451 | 288 |
| 4159 | harmonic_arima | 14.31522251624876 | 11.874290041046637 | 0.829486934455158 | 288 |
| 4159 | lightgbm | 16.196710465048678 | 12.735436428684718 | 0.7862977149691515 | 288 |
| 4159 | lstm | 24.125879157215 | 12.028895354397259 | 0.4985888918704933 | 288 |
| 4556 | persistence | 29.52984996371799 | 27.190926551818848 | 0.9207946056355562 | 288 |
| 4556 | seasonal_naive | 73.528230243259 | 83.36382558610704 | 1.133766246111299 | 288 |
| 4556 | harmonic_arima | 25.829351784634955 | 25.965509134508142 | 1.0052714195465866 | 288 |
| 4556 | lightgbm | 29.140778611210763 | 31.909785014515915 | 1.0950217027571076 | 288 |
| 4556 | lstm | 27.539813508287953 | 29.012316689753757 | 1.053468160959865 | 288 |

### Worst contiguous 6-hour windows (test week)

`ratio_to_persistence` above 1 means the baseline would have been better over
exactly that stretch.

| square_id | model | start | mae | persistence_mae | ratio_to_persistence |
|---|---|---|---|---|---|
| 4159 | lstm | 2013-12-17T10:00:00.000000000 | 52.235 | 20.505 | 2.547 |
| 4159 | lstm | 2013-12-18T09:50:00.000000000 | 60.18 | 26.374 | 2.282 |
| 4159 | lstm | 2013-12-19T09:50:00.000000000 | 53.022 | 27.003 | 1.964 |
| 4556 | lightgbm | 2013-12-22T11:50:00.000000000 | 52.23 | 30.03 | 1.739 |
| 4159 | lightgbm | 2013-12-16T10:00:00.000000000 | 33.092 | 19.259 | 1.718 |
| 4556 | lightgbm | 2013-12-16T11:40:00.000000000 | 44.552 | 28.171 | 1.581 |
| 5161 | lstm | 2013-12-17T13:20:00.000000000 | 244.117 | 171.866 | 1.42 |
| 4556 | lstm | 2013-12-21T15:00:00.000000000 | 39.068 | 29.138 | 1.341 |
| 5161 | lightgbm | 2013-12-17T13:00:00.000000000 | 229.321 | 179.992 | 1.274 |
| 5161 | harmonic_arima | 2013-12-22T14:00:00.000000000 | 253.434 | 199.088 | 1.273 |
| 4159 | lightgbm | 2013-12-17T08:50:00.000000000 | 26.318 | 20.849 | 1.262 |
| 4556 | lstm | 2013-12-22T15:10:00.000000000 | 45.461 | 36.289 | 1.253 |

### Held-out stress split (23 Dec - 1 Jan), MASE by area

Never tuned on and never used for selection. Holds four of the eight Italian
public holidays in the study period.

| model | 5161 | 4159 | 4556 | mean |
|---|---:|---:|---:|---:|
| persistence | 0.19827 | 0.12366 | 0.20603 | 0.17599 |
| harmonic_arima | 0.21609 | 0.12133 | 0.22229 | 0.18657 |
| lstm_ensemble | 0.34127 | 0.24027 | 0.41471 | 0.33208 |
| lstm | 0.35294 | 0.24211 | 0.41864 | 0.3379 |
| lightgbm | 0.33421 | 0.28823 | 0.49416 | 0.3722 |
| seasonal_naive | 1.26624 | 0.37684 | 0.50409 | 0.71572 |

