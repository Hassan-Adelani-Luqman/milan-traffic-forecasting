# Figure index

Each exported figure, the report section it supports, and the table
holding the numbers that accompany it.

All figures are 300 dpi PNG in `report/figures/`.

## Exploratory Analysis

| figure | shows | numbers in |
|---|---|---|
| `01_total_distribution.png` | Histogram of per-cell totals on a log axis, beside the CCDF on log-log axes. | `distribution_stats.json` |
| `02_spatial_totals.png` | log10 total activity over the 100x100 Milano grid, study areas marked by rank. | `selected_areas.json` |
| `03_series_first_fortnight.png` | Traffic for the five study areas, 1-14 November 2013, one panel each. | `area_summary.csv` |
| `04_series_overlay_normalised.png` | The same five series scaled to their own maxima, comparing shape not volume. | `area_summary.csv` |
| `05_mstl_decomposition.png` | MSTL of square 5161 into trend, daily and weekly seasonality, and residual. | `decomposition.json` |
| `06_acf_pacf.png` | ACF and PACF to lag 1100 with confidence bands; daily and weekly lags marked. | `autocorrelation.json` |
| `07_rolling_stats.png` | Rolling mean and standard deviation over a one-day window. | `stationarity.csv` |
| `08_periodogram.png` | Spectral power against period in hours, dominant cycles annotated. | `spectral_peaks.csv` |

## Pending

Phase 6 adds: 9 actual-vs-predicted plots (3 models x 3 areas), per-area
zoom panels, error-by-hour heatmaps, residual ACF per model, and the
stress-split failure figures.

