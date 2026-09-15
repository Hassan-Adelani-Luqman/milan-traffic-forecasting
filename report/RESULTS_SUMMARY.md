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

- Flagged: **152** intervals of 8,928 (**1.70%**) at z > 4, scale estimated per position in the daily cycle
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

_Pending: Phase 4 (forecasting framework) and Phase 5 (models and tuning)._

## Results and Discussion

_Pending: Phase 5 (experiments) and Phase 6 (evaluation and failure analysis)._

## Conclusion and Future Work

_Pending: depends on the results above._

