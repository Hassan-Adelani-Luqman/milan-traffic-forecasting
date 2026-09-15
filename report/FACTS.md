# Fact registry

Every figure the report may cite, computed from the artefacts and named.
Quote a fact by its key so that a change in measurement propagates by
regeneration rather than by recollection.

Regenerate with `python -m src.facts`.

## Dataset

| key | value | unit | source | description |
|---|---|---|---|---|
| `absent_cells` | 34,682 | cells | `matrix_report.json` | Cells with no record at all |
| `absent_cells_pct` | 0.0388 | % | `derived` | Absent cells as a share of the grid |
| `distinct_country_codes_per_file` | 246 | codes | `measured on 2013-11-01` | Distinct country codes in one daily file -- NOT rows per cell |
| `grid_cells_total` | 89,280,000 | cells | `derived` | Timestamps x squares |
| `matrix_mib` | 340.58 | MiB | `derived` | Assembled matrix as float32 |
| `max_rows_per_cell` | 36 | rows | `measured on 2013-11-01` | Most country-split records for a single (square, time) pair |
| `mean_rows_per_cell` | 3.6 | rows | `derived` | Mean country-split records per occupied cell |
| `mean_rows_per_day` | 5.16 M | rows | `derived` | Mean records per day over the period |
| `missing_intervals` | 0 | intervals | `matrix_report.json` | Timestamps absent from the grid |
| `n_days` | 62 | days | `config` | Observation period length |
| `n_squares` | 10,000 | cells | `config` | Grid cells in Milan |
| `n_timestamps` | 8,928 | intervals | `config` | 10-minute intervals in the period |
| `nan_after_policy` | 0 | cells | `matrix_report.json` | NaN remaining after the missing-data policy |
| `raw_bytes` | 20,804,803,507 | bytes | `Dataverse file listing` | Total published dataset size |
| `raw_gib` | 19.38 | GiB | `Dataverse file listing` | Total published dataset size |
| `total_internet` | 5,552,894,187.94 | activity | `matrix_report.json` | Total internet activity over the period |
| `total_raw_rows` | 319,896,289 | rows | `ingest_summary.json` | Records parsed across all days |

## Timing

| key | value | unit | source | description |
|---|---|---|---|---|
| `download_mbit_per_s` | 469 | Mbit/s | `derived` | Sustained throughput in decimal megabits, not mebibits |
| `download_mean_s` | 5.73 | s | `ingest_summary.json` | Mean download time per day |
| `download_mib_per_s` | 55.9 | MiB/s | `derived` | Sustained download throughput |
| `download_std_s` | 0.64 | s | `ingest_summary.json` | Standard deviation of download time per day |
| `download_total_min` | 5.92 | min | `ingest_summary.json` | Total download time |
| `ingest_mean_s` | 1.49 | s | `ingest_summary.json` | Mean ingest time per day |
| `ingest_std_s` | 0.10 | s | `ingest_summary.json` | Standard deviation of ingest time per day |
| `ingest_total_min` | 1.54 | min | `ingest_summary.json` | Total ingest time |
| `peak_rss_max_mib` | 574 | MiB | `ingest_summary.json` | Peak RSS during the streaming run |

## Memory

| key | value | unit | source | description |
|---|---|---|---|---|
| `naive_pandas_peak_mib` | 633.06 | MiB | `memory_report.csv` | Mean peak RSS for naive_pandas, one process per measurement |
| `naive_pandas_resident_mib` | 295.57 | MiB | `memory_report.csv` | Data resident after naive_pandas completes |
| `naive_pandas_wall_s` | 5.56 | s | `memory_report.csv` | Mean wall time per day for naive_pandas |
| `naive_projected_gib` | 17.90 | GiB | `derived, extrapolated` | Holding all 62 days the naive way; not executed |
| `pandas_chunked_peak_mib` | 172.55 | MiB | `memory_report.csv` | Mean peak RSS for pandas_chunked, one process per measurement |
| `pandas_chunked_resident_mib` | 5.49 | MiB | `memory_report.csv` | Data resident after pandas_chunked completes |
| `pandas_chunked_wall_s` | 5.86 | s | `memory_report.csv` | Mean wall time per day for pandas_chunked |
| `polars_lazy_peak_mib` | 552.22 | MiB | `memory_report.csv` | Mean peak RSS for polars_lazy, one process per measurement |
| `polars_lazy_resident_mib` | 5.49 | MiB | `memory_report.csv` | Data resident after polars_lazy completes |
| `polars_lazy_wall_s` | 0.95 | s | `memory_report.csv` | Mean wall time per day for polars_lazy |

## Distribution

| key | value | unit | source | description |
|---|---|---|---|---|
| `bottom_50pct_share` | 11.6% | % | `distribution_stats.json` | bottom 50pct share |
| `gini` | 0.608 |  | `distribution_stats.json` | Gini coefficient of cell totals |
| `kurtosis` | 25.50 |  | `distribution_stats.json` | Excess kurtosis of cell totals |
| `lognormal_ks_stat` | 0.0232 |  | `distribution_stats.json` | KS statistic against the lognormal fit |
| `lognormal_mu` | 12.496 |  | `distribution_stats.json` | Fitted lognormal mu |
| `lognormal_sigma` | 1.211 |  | `distribution_stats.json` | Fitted lognormal sigma |
| `max_over_median` | 45.8 | x | `distribution_stats.json` | Busiest cell relative to the median |
| `n_zero_cells` | 0 | cells | `distribution_stats.json` | Cells with no activity at all |
| `skewness` | 4.26 |  | `distribution_stats.json` | Skewness of cell totals |
| `top_10pct_share` | 48.4% | % | `distribution_stats.json` | top 10pct share |
| `top_1pct_share` | 11.0% | % | `distribution_stats.json` | top 1pct share |
| `top_5pct_share` | 33.6% | % | `distribution_stats.json` | top 5pct share |

## Areas

| key | value | unit | source | description |
|---|---|---|---|---|
| `cv_4159` | 0.660 |  | `area_summary.csv` | cv for square 4159 |
| `cv_4556` | 0.485 |  | `area_summary.csv` | cv for square 4556 |
| `cv_5059` | 0.768 |  | `area_summary.csv` | cv for square 5059 |
| `cv_5161` | 0.968 |  | `area_summary.csv` | cv for square 5161 |
| `cv_5259` | 0.939 |  | `area_summary.csv` | cv for square 5259 |
| `forecast_squares` | 5161, 4159, 4556 |  | `selected_areas.json` | Cells modelled in Section 4 |
| `nearest_4159` | Universita Bocconi |  | `area_summary.csv` | Nearest reference point to square 4159 |
| `nearest_4556` | Navigli |  | `area_summary.csv` | Nearest reference point to square 4556 |
| `nearest_5059` | Duomo |  | `area_summary.csv` | Nearest reference point to square 5059 |
| `nearest_5161` | Galleria Vittorio Emanuele II |  | `area_summary.csv` | Nearest reference point to square 5161 |
| `nearest_5259` | Teatro alla Scala |  | `area_summary.csv` | Nearest reference point to square 5259 |
| `nearest_m_4159` | 365 | m | `area_summary.csv` | Distance from square 4159 |
| `nearest_m_4556` | 273 | m | `area_summary.csv` | Distance from square 4556 |
| `nearest_m_5059` | 226 | m | `area_summary.csv` | Distance from square 5059 |
| `nearest_m_5161` | 276 | m | `area_summary.csv` | Distance from square 5161 |
| `nearest_m_5259` | 167 | m | `area_summary.csv` | Distance from square 5259 |
| `night_floor_over_mean_4159` | 0.489 |  | `area_summary.csv` | night floor over mean for square 4159 |
| `night_floor_over_mean_4556` | 0.534 |  | `area_summary.csv` | night floor over mean for square 4556 |
| `night_floor_over_mean_5059` | 0.235 |  | `area_summary.csv` | night floor over mean for square 5059 |
| `night_floor_over_mean_5161` | 0.130 |  | `area_summary.csv` | night floor over mean for square 5161 |
| `night_floor_over_mean_5259` | 0.333 |  | `area_summary.csv` | night floor over mean for square 5259 |
| `peak_to_trough_4159` | 14.942 |  | `area_summary.csv` | peak to trough for square 4159 |
| `peak_to_trough_4556` | 16.981 |  | `area_summary.csv` | peak to trough for square 4556 |
| `peak_to_trough_5059` | 30.943 |  | `area_summary.csv` | peak to trough for square 5059 |
| `peak_to_trough_5161` | 99.387 |  | `area_summary.csv` | peak to trough for square 5161 |
| `peak_to_trough_5259` | 46.964 |  | `area_summary.csv` | peak to trough for square 5259 |
| `rank_4159` | 424 |  | `selected_areas.json` | Rank of square 4159 by total activity |
| `rank_4556` | 109 |  | `selected_areas.json` | Rank of square 4556 by total activity |
| `rank_5059` | 2 |  | `selected_areas.json` | Rank of square 5059 by total activity |
| `rank_5161` | 1 |  | `selected_areas.json` | Rank of square 5161 by total activity |
| `rank_5259` | 3 |  | `selected_areas.json` | Rank of square 5259 by total activity |
| `top_three_squares` | 5161, 5059, 5259 |  | `selected_areas.json` | Three highest-traffic cells |
| `top_traffic_square` | 5,161 |  | `selected_areas.json` | Highest-traffic cell |
| `weekend_over_weekday_4159` | 0.587 |  | `area_summary.csv` | weekend over weekday for square 4159 |
| `weekend_over_weekday_4556` | 1.140 |  | `area_summary.csv` | weekend over weekday for square 4556 |
| `weekend_over_weekday_5059` | 0.861 |  | `area_summary.csv` | weekend over weekday for square 5059 |
| `weekend_over_weekday_5161` | 1.384 |  | `area_summary.csv` | weekend over weekday for square 5161 |
| `weekend_over_weekday_5259` | 0.425 |  | `area_summary.csv` | weekend over weekday for square 5259 |

## Decomposition

| key | value | unit | source | description |
|---|---|---|---|---|
| `residual_over_observed_std` | 19.0% |  | `derived` | Residual standard deviation as a share of observed |
| `strength_seasonal_1008` | 0.746 |  | `decomposition.json` | Strength of the seasonal_1008 component |
| `strength_seasonal_144` | 0.959 |  | `decomposition.json` | Strength of the seasonal_144 component |
| `strength_trend` | 0.451 |  | `decomposition.json` | Strength of the trend component |
| `variance_residual` | 3.6% | % | `decomposition.json` | Variance share of the residual component |
| `variance_seasonal_1008` | 10.0% | % | `decomposition.json` | Variance share of the seasonal_1008 component |
| `variance_seasonal_144` | 82.9% | % | `decomposition.json` | Variance share of the seasonal_144 component |
| `variance_trend` | 2.8% | % | `decomposition.json` | Variance share of the trend component |

## Autocorrelation

| key | value | unit | source | description |
|---|---|---|---|---|
| `acf_at_daily` | 0.878 |  | `autocorrelation.json` | Autocorrelation at the daily lag |
| `acf_at_weekly` | 0.838 |  | `autocorrelation.json` | Autocorrelation at the weekly lag |
| `lag_1` | 0.987 |  | `autocorrelation.json` | Lag-1 autocorrelation |
| `notable_lags` | 144, 1008, 864, 288, 432, 720 |  | `autocorrelation.json` | Local ACF maxima |

## Spectrum

| key | value | unit | source | description |
|---|---|---|---|---|
| `spectral_peak_1_hours` | 24.00 | h | `spectral_peaks.csv` | Dominant cycle 1 |
| `spectral_peak_2_hours` | 12.00 | h | `spectral_peaks.csv` | Dominant cycle 2 |
| `spectral_peak_3_hours` | 165.33 | h | `spectral_peaks.csv` | Dominant cycle 3 |

## Anomalies

| key | value | unit | source | description |
|---|---|---|---|---|
| `anomalies_evaluable` | 8,784 | intervals | `derived` | Intervals the detector can assess; the first day cannot be |
| `anomalies_flagged` | 152 | intervals | `anomalies.csv` | Intervals flagged against a seasonal-naive predictor |
| `anomalies_holiday_share` | 23.0% | % | `derived` | Share of flags on holidays |
| `anomalies_on_holidays` | 35 | intervals | `anomalies.csv` | Flagged intervals falling on a holiday |
| `anomalies_rate` | 1.73% | % | `derived` | Flagged share of evaluable intervals |

