# Implementation Plan — `milan-traffic-forecasting`

**Audience:** Claude Code (agentic implementation)
**Human owner:** must review at every `CHECKPOINT` before the next phase starts.

---

## Status

| Phase | State | Commit |
|---|---|---|
| 0 — Scaffold | ✅ complete | `41baefd` |
| 1 — Download | ✅ complete | `6134e20`, `c8020ba`, `8e97e62` |
| 2 — Ingest and memory evidence | ✅ complete | `8935f90`, `bb8a2e1`, `b5dd29b`, `1a83913` |
| 3 — Exploratory analysis | ✅ complete | `f64da2d`, `8cc9bd1`, `9e780f3` |
| 4 — Forecasting framework | ⬜ next | |
| 5 — Models and experimentation | ⬜ | |
| 6 — Evaluation and failure analysis | ⬜ | |
| 7 — Reproducibility and repo polish | ⬜ | |
| 8 — Report support artefacts | 🟡 partial — evidence pack scaffolded | |

**236 tests passing.** Full dataset ingested; `data/processed/` holds the
`8928 × 10000` matrix. Study areas resolved: **{5161, 4159, 4556}**.

---

## 0. Context you need before writing any code

### The task
Comparative study of three sequential models for **one-step-ahead** (10 minutes ahead)
forecasting of mobile internet traffic in Milan, evaluated on the week
**16–22 December 2013**, across three geographical areas.

### The dataset
- Source: Harvard Dataverse, `doi:10.7910/DVN/EGZHFV` ("Telecommunications - SMS, Call, Internet - MI").
- Grid: `doi:10.7910/DVN/QJWLFU` ("Milano Grid", GeoJSON of the 10,000 cells).
- **62 plain-text TSV files**, one per day, `sms-call-internet-mi-2013-MM-DD.txt`,
  covering **2013-11-01 to 2014-01-01**.
- Each file is ~265–359 MiB. Total **19.38 GiB** (20,804,803,507 bytes).
- Milan is a 100×100 grid of 235 m square cells; square ids run 1–10000.
- Sampling interval: 10 minutes → 144 intervals/day → **8,928 timestamps total**.

### Columns (tab-separated, no header)

| # | Name | Notes |
|---|---|---|
| 0 | `square_id` | 1–10000 |
| 1 | `time_ms` | start of interval, **epoch milliseconds, UTC** |
| 2 | `country_code` | phone country code of the counterparty nation |
| 3 | `sms_in` | may be empty |
| 4 | `sms_out` | may be empty |
| 5 | `call_in` | may be empty |
| 6 | `call_out` | may be empty |
| 7 | `internet` | **the target variable** |

### Facts that drive the whole design

1. **Rows are split by `country_code`.** One `(square_id, time_ms)` pair has many rows.
   You **must** `groupby(["square_id","time_ms"]).sum()` on `internet` to get the area's
   total. *Measured: ~4.8 M rows/day, about 3.4 country rows per cell, up to 246.*
2. **After aggregation the data is small.** `8928 × 10000` as `float32` is **340.58 MiB**.
   The entire memory-management deliverable is getting from 19.38 GiB of text to that
   matrix while never holding more than one day in RAM.
3. **Timestamps are UTC; Milan is CET.** Convert to `Europe/Rome`.
   *Measured: files are aligned to **local** midnight — the 1 Nov file opens at
   `2013-10-31T23:00Z`.* No DST transition falls inside the window (Italy switched
   2013-10-27 and 2014-03-30), so every local day is exactly 144 intervals.
4. *(Discovered)* **`internet` is normalised activity, not an integer CDR count** —
   values like `11.028366381681026`. The report must not call it a count.
5. *(Discovered)* **The dataset has a Dataverse Guestbook** (`guestbookId` 96). A plain
   `GET` returns HTTP 400; a `POST` carrying a guestbook response returns a signed URL.
   No API token needed.

---

## 1. Ground rules — apply to every phase

- **Never commit raw data.** `.gitignore` excludes `data/raw/` and `data/interim/`.
  **Do** commit the small processed artefacts so results reproduce without the download.
- **Logic lives in `src/`.** Notebooks import from `src/` and produce figures only.
- **All configuration in `config/default.yaml`.** No magic numbers, dates or paths in
  `src/`. Every script takes `--config`.
- **Determinism.** Seeds for `random`, `numpy` and the DL framework; library versions
  logged to `results/environment.json`.
- **Every experiment appends one row to `results/experiments.csv`.** Never overwrite.
- **Fit every transform on training data only.** Any leakage is a defect.
- **Type hints and docstrings on every public function.** Functions under ~50 lines.
- **Stop at each `CHECKPOINT`** and summarise. Do not proceed unprompted.

### Ground rules added during execution

- **Hybrid local/Kaggle split.** `src/`, `config/` and `tests/` are developed locally;
  ingest and training run on Kaggle. Notebooks `git clone` the repo and import from
  `src/`. Justified by measurement: Kaggle's link is **127× faster** (5.9 min vs an
  estimated 12.6 h for the 19.38 GiB download), and the laptop has no CUDA GPU.
- **Notebooks are generated, not hand-edited.** `notebooks/build_*_notebook.py` are the
  source; the `.ipynb` files are output. `tests/test_notebook.py` asserts every `src`
  symbol they import still exists, that they define no functions or classes, and that
  they import no private names.
- **Measurement methodology is itself a deliverable.** Benchmarks run one process per
  measurement; conditions (available RAM) travel with each row.

---

## 2. Repository layout

```
milan-traffic-forecasting/
├── README.md
├── CLAUDE.md                    # agent brief, see Appendix A
├── Plan.md                      # this file
├── requirements.txt             # + requirements-local.txt / requirements-kaggle.txt
├── run.py                       # cross-platform task runner (make is absent on Windows)
├── Makefile                     # mirrors run.py for Linux/Kaggle
├── .gitignore
├── config/
│   ├── default.yaml
│   └── kaggle.yaml              # overlay, always merged over default
├── data/
│   ├── raw/                     # gitignored, except grid/milano-grid.geojson
│   ├── interim/                 # gitignored, per-day blocks
│   └── processed/               # matrix gitignored; small artefacts COMMITTED
├── src/
│   ├── config.py                # yaml loader -> frozen dataclasses, strict
│   ├── download.py              # Dataverse client, guestbook, resume, md5
│   ├── pipeline.py              # streaming download -> ingest -> delete
│   ├── ingest.py                # three strategies, per-day blocks
│   ├── build_matrix.py          # assembly, timezone, missing-data policy
│   ├── memory_profiling.py      # measure(): peak RSS via sampler thread
│   ├── memory_report.py         # benchmark, one process per measurement
│   ├── run_log.py               # parse executed notebook -> run tables
│   ├── eda.py                   # distribution, Gini, areas, summaries
│   ├── tsanalysis.py            # MSTL, ADF/KPSS, ACF/PACF, spectrum, anomalies
│   ├── plots.py                 # figures, separate from statistics
│   ├── holidays_it.py           # Italian + Milanese holidays
│   ├── run_eda.py               # orchestrates every exploratory artefact
│   ├── export_report.py         # evidence pack for the write-up
│   ├── seeding.py, timing.py, notebook.py, env_report.py
│   ├── features.py              # Phase 4
│   ├── splits.py, metrics.py, experiments.py   # Phase 4
│   ├── models/                  # Phase 5
│   ├── train.py, evaluate.py    # Phase 5-6
├── notebooks/
│   ├── build_kaggle_notebook.py → 00_kaggle_ingest.ipynb
│   ├── build_eda_notebook.py    → 02_eda.ipynb
│   └── runs/                    # executed notebooks, kept as evidence
├── results/{figures,tables,predictions}/, environment.json, experiments.csv
├── report/                      # figures, tables, RESULTS_SUMMARY.md, FIGURE_INDEX.md
└── tests/
```

---

## 3. `config/default.yaml` — authoritative values

Split boundaries are **inclusive of both endpoints at day granularity in `Europe/Rome`**,
i.e. test runs `2013-12-16 00:00` through `2013-12-22 23:50`.

| Split | Dates | Points | Purpose |
|---|---|---|---|
| train | 2013-11-01 → 2013-12-08 | 5,472 | Fitting; all transforms fit here only |
| validation | 2013-12-09 → 2013-12-15 | 1,008 | Hyperparameter selection |
| test | 2013-12-16 → 2013-12-22 | 1,008 | Reported results |
| stress | 2013-12-23 → 2014-01-01 | 1,440 | Failure analysis only; never tuned on |

Other authoritative values: `timezone: Europe/Rome`, `interval_minutes: 10`,
`n_squares: 10000`, `daily_period: 144`, `weekly_period: 1008`,
`transform: log1p`, `scaler: standard`, `sequence_length: 144`, `seeds: [0, 1, 2]`.

`config/kaggle.yaml` overrides only paths and `delete_raw_after_ingest`. It is an
**overlay**: `load_config` always uses `default.yaml` as the base layer.

---

## Phase 0 — Scaffold ✅

Config loader into frozen dataclasses with strict validation (unknown keys rejected;
splits checked contiguous, non-overlapping, inside the observation period).
`measure()` sampling peak RSS on a background thread at 50 ms. `time_it()` with warmup
and repeats. `record_hardware()`.

**Delivered beyond plan:** `run.py` (no `make` on Windows), three-way requirements
split, `src/seeding.py`, `src/notebook.py`.

**Two bugs the tests caught:** `_RSSSampler` shadowed `threading.Thread._stop`, making
every `measure()` block raise; and `WindowsPath("/kaggle/temp/raw").is_absolute()` is
`False`, which silently rewrote the Kaggle paths under the project root.

> **CHECKPOINT 0** ✅ — 53 tests. Hardware: i7-10510U 4c/8t, 31.8 GB RAM, **no CUDA GPU**.

---

## Phase 1 — Download ✅

Discovers the file list from the Dataverse API rather than hardcoding names; streams to
a `.part` sidecar, renamed only after MD5 matches; resumes via HTTP `Range`; exponential
backoff; `manifest.json`; disk-space guard; `--dry-run`.

**Three things the API did not do as assumed:**
1. **Guestbook gate** — a `POST` with a guestbook response returns a per-file signed URL.
   Identity comes from `--gb-*` flags, `DATAVERSE_GB_*` env vars or a gitignored `.env`,
   and is never defaulted to a placeholder: Dataverse records one response per download.
2. **Harvard's WAF rejects `python-requests`** with HTTP 403. `headers.setdefault` cannot
   fix it because `requests.Session` populates the header itself.
3. **Signed URLs 303-redirect to S3**, which advertises `Accept-Ranges` — so resume
   genuinely works. A server ignoring `Range` returns 200 with the whole body, which must
   truncate and restart rather than append.

> **CHECKPOINT 1** ✅ — 62 files, 19.38 GiB. Verified live: fresh download, skip on
> re-run (3.3 s), and resume from 99.4% producing a byte-identical file.
> **Local throughput 0.44 MiB/s → 12.6 h for the full dataset.**

---

## Phase 2 — Ingest and memory evidence ✅

Three strategies, all measured: `load_day_naive` (the deliberate "before"),
`ingest_day_pandas_chunked`, `ingest_day_polars`. Per-day blocks checkpointed so a
timed-out session resumes. `build_matrix.py` stacks into a pre-allocated array, verifies
the timestamp grid, and applies the missing-data policy.

### Measured trade-off — the plan's assumption was wrong

| strategy | resident/day | peak RSS | wall/day | scales with days |
|---|---:|---:|---:|---|
| naive pandas | 295.57 MiB | 633.06 MiB | 5.56 s | **yes** |
| chunked pandas | 5.49 MiB | 172.55 MiB | 5.86 s | no |
| Polars lazy | 5.49 MiB | 552.22 MiB | 0.95 s | no |

Polars is ~6× faster but peaks **3.2× higher**, because its CSV reader holds the whole
file. `low_memory=True` (559 MiB) and `read_csv_batched` (697–862 MiB) were measured and
both made it worse. Neither strategy dominates, so `--strategy` selects.

**The headline is scaling, not peak:** holding all 62 days the naive way needs
**17.90 GiB**; both optimised paths hold one 5.49 MiB block regardless of dataset size.

**Methodology fix:** measuring three strategies in one process reported 544/184/384 MiB
for identical work, because freed arenas are not returned to the OS. Each measurement now
runs in its own subprocess; repeats then agree to ~2%.

**Deviations:** per-day blocks are `.npy` + JSON sidecar, not Parquet — a 144×10000 dense
float32 array in Parquet needs 10,000 column chunks whose metadata costs more than the
compression saves, and `.npy` memory-maps. `src/pipeline.py` added to interleave download
and ingest, because `/kaggle/temp` is discarded at session end.

> **CHECKPOINT 2** ✅ — matrix `(8928, 10000)`, 62 days,
> `2013-11-01 00:00 → 2014-01-01 23:50` CET.
> **0 missing intervals, 0 interpolated, 0 NaN** — the grid is complete and the
> interpolation policy never fired. 34,682 absent cells (0.0388%).
> Kaggle run: **5.92 min download (55.9 MiB/s), 1.54 min ingest, 7.7 min wall.**

---

## Phase 3 — Exploratory analysis ✅

### 3a. Distribution across the 10,000 areas

Gini **0.608**; top 1% hold **11.0%**, top 10% **48.4%**, bottom 50% **11.6%**.
Skewness 4.26, kurtosis 25.50, max/median 45.8×.

**Lognormal fit:** KS rejects at p = 4.3e-05, but that is a sample-size effect — the
statistic is 0.0232 against a critical value of 0.0136 at n = 10,000, and `log(x)` has
skewness +0.023 and kurtosis +0.013. Quoting the rejection alone would misrepresent it.

### 3b. Areas and the five series

| square | rank | mean | CV | peak/trough | night/mean | wknd/wkday |
|---|---:|---:|---:|---:|---:|---:|
| 5161 | 1 | 1,427 | 0.968 | 99.4 | 0.130 | 1.384 |
| 5059 | 2 | 1,251 | 0.768 | 30.9 | 0.235 | 0.861 |
| 5259 | 3 | 1,174 | 0.939 | 47.0 | 0.333 | 0.425 |
| 4159 | 424 | 275 | 0.660 | 14.9 | 0.489 | 0.587 |
| 4556 | 109 | 512 | 0.485 | 17.0 | 0.534 | 1.140 |

**The top three cells are neighbours, not independent areas** — 5161, 5059 and 5259 lie
within **470 m** of one another, and the top ten fit inside a 3.05 × 2.35 km box. This
settles Appendix B Q1 with evidence: forecasting the top three would compare three cells
of the same place. The chosen set spans ranks 1, 424 and 109.

### 3c. Two additional analyses on the top area (5161)

**MSTL** (144, 1008): daily **82.9%** of variance (strength 0.959), weekly **10.0%**
(0.746), trend 2.8%, residual 3.6%. Residual std is **19%** of observed.

**Autocorrelation and stationarity:** lag-1 ACF **0.987**; ACF 0.878 at 144 and 0.838 at
1008; local maxima at 144, 288, 432, 720, 864, 1008. ADF and KPSS both call the raw
series and both differences stationary — but that means *no stochastic trend only*.
Neither tests whether the mean varies by time of day, which it does strongly.

**Supporting:** periodogram peaks at **24.00 h**, a **12.00 h harmonic**, and ~168 h.
Seasonal-naive anomalies: 152 intervals (1.73%); holidays are 12.9% of days but carry
**23.0%** of flags — 1.78× enrichment, binomial **p = 4.3e-04**.

**Bug fixed:** the anomaly detector first flagged 12.7% of all points. The residual's
spread varies **25× by hour of day**, so a global MAD scale is set by the quiet hours and
flags every busy one. Scale is now estimated per position in the daily cycle. `log1p` was
measured as an alternative and rejected (2.85% flagged; the study reports absolute-error
metrics, so the absolute scale is the right one to judge deviations on).

**Carried forward:** Monday **2 December**, 17 flagged intervals, not a holiday — the
worst single day and unexplained.

**Data-quality context:** absent cells are not uniform — ~22/day to 21 November, stepping
to 100+ around 23 November and reaching 1,463/day over Christmas. By split: 220/day
(train), 864 (test), 1,463 (stress). Raw row counts decline smoothly by 6.7% over the
same window rather than stepping, so this is quiet cells falling silent, not a collection
failure. **It does not touch the experiments: squares 5161, 4159 and 4556 contain no zero
in any split** (minima 47–172).

> **CHECKPOINT 3** ✅ — 8 figures at 300 dpi, 7 tables,
> `selected_series.parquet` (283 KB) committed.

---

## Phase 4 — Forecasting framework ⬜

**Goal:** the harness, the baselines, and a correct evaluation protocol — before any real model.

### 4a. `src/splits.py`
`make_splits(series, config)` using config dates in `Europe/Rome`. Assert exact lengths:
train 5472, validation 1008, test 1008. Fail loudly on mismatch.

### 4b. `src/features.py`
- `LogStandardScaler`: `fit(train)` stores mean/std of `log1p(x)`; guard so `fit` is
  never called on non-training data.
- `make_windows(series, L, horizon=1, exog=None)` — sliding windows, stride 1.
- `calendar_features(index)`: `sin/cos(2π·minute_of_day/1440)`, `sin/cos(2π·day_of_week/7)`,
  `is_weekend`, `is_italian_holiday` (from `src/holidays_it.py`).
- `lag_features(series, lags, rolling_windows)` for the GBM: lags
  `[1,2,3,6,12,144,145,288,1008]`, rolling mean/std over `[6,36,144]`, plus calendar.
  All causal — assert no future leakage with a unit test.

*Evidence from Phase 3:* the ACF local maxima at 144/288/432/720/864/1008 confirm this
lag set; lag-1 ACF of 0.987 means lag 1 is the single strongest feature.

### 4c. `src/models/base.py`
```python
class Forecaster(Protocol):
    name: str
    def fit(self, train, valid, **kw) -> "Forecaster": ...
    def predict_one_step(self, history) -> float: ...
    def walk_forward(self, series, start, end) -> np.ndarray: ...
    def n_params(self) -> int: ...
```
`walk_forward` is the **only** inference path used for reported results: at each step `t`
the model sees the *true* observed history up to `t` and predicts `t+1`. Correct for
one-step-ahead, and **not** a recursive rollout. Must be documented in the report.

### 4d. `src/models/baselines.py`
- `Persistence`: `x̂(t+1) = x(t)`
- `SeasonalNaive`: `x̂(t+1) = x(t+1-144)`

**Not** among the three models — the reference floor, in every results table.
*Phase 3 makes persistence a demanding baseline: lag-1 ACF is 0.987.*

### 4e. `src/metrics.py`
`evaluate(y_true, y_pred, y_train, seasonal_period=144)` returning MAE, RMSE, MAPE,
sMAPE, WAPE, R² and **MASE**. All metrics in original units **after inverse-transforming**.
MAPE must handle near-zero denominators explicitly — report the count below threshold and
the value with and without them; do not silently clip.

*Phase 3 note:* area minima are 47–172, so MAPE has no zero-denominator problem on the
three forecast areas. Report the check anyway.

### 4f. Tests
No leakage in `make_windows` and `lag_features`; scaler round-trip; `SeasonalNaive`
reproduces a synthetic periodic series exactly; split lengths; MASE equals 1.0 when
predictions equal seasonal naive.

> **CHECKPOINT 4** — report both baseline metric tables for all three areas.
> **These numbers are the bar every model must clear.**

---

## Phase 5 — Models and iterative experimentation ⬜

### The three models

**Model 1 — Dynamic harmonic regression** (`harmonic_arima.py`). Fourier terms for period
144 (K₁ harmonics) and 1008 (K₂) as exogenous regressors in `statsmodels.SARIMAX`, with
ARIMA errors. Chosen over plain SARIMA because s=144 is intractable and cannot express two
seasonalities at once. Fit once on train+validation, then walk forward with
`results.append(new_obs, refit=False)`.
*Phase 3 evidence: the 12.00 h harmonic means K₁ ≥ 2; stationarity tests give d = 0.*

**Model 2 — LSTM** (`lstm.py`). PyTorch. Input `(L, F)`, F = 1 or 1+calendar. Stacked LSTM
→ dropout → linear head. Early stopping on validation MAE, best-checkpoint restore.

**Model 3 — LightGBM** (`gbm.py`) on the causal lag + rolling + calendar matrix. Early
stopping on validation. Feature importances should corroborate the ACF lags.

### Experiment logging
`src/experiments.py` appends one row per run to `results/experiments.csv`:
`run_id, timestamp, model, area, seed, hyperparams_json, feature_set, train_mae,
valid_mae, valid_rmse, valid_mase, train_wall_s, n_params, git_sha,
rationale_for_next_change`.

`rationale_for_next_change` is **mandatory free text** — the primary evidence for the
experimentation criterion. Never blank.

### Tuning protocol — one axis at a time, top area only, selecting on validation MAE
1. Sequence length `L ∈ {36, 72, 144, 288}`
2. Hidden size `∈ {32, 64, 128}` × layers `∈ {1, 2}`
3. Learning rate `∈ {1e-3, 3e-4}` × batch `∈ {32, 64, 128}`
4. Dropout `∈ {0.0, 0.2}` and weight decay
5. **Feature ablation:** with vs. without calendar features; report the delta

Then a small Optuna study (≤ 30 trials) over the promising region, logging every trial.

Harmonic-ARIMA: grid `K₁ ∈ {2..8}` × `K₂ ∈ {1..4}`, select by AICc, then ARIMA(p,d,q) on
the residuals. LightGBM: Optuna over `num_leaves`, `learning_rate`, `min_child_samples`,
`feature_fraction`, `bagging_fraction`; `n_estimators` by early stopping.

### Final runs
Refit the selected configuration on train+validation, evaluate on test. **Neural models:
3 seeds, report mean ± std.** Persist to `results/predictions/{model}_{area}.parquet`.

### Timing (requirement IV)
Training wall time, 3 repeats, mean ± std, including early stopping. Inference: total
seconds for 1,008 one-step forecasts, and per-step ms. Parameter count and peak memory.
Write `results/tables/timing.csv`, stating whether figures are from one area or averaged.

**Runs on Kaggle** (GPU). Needs the published dataset slug.

> **CHECKPOINT 5** — experiment log summary, chosen hyperparameters with the reasoning
> chain, validation metrics vs. baselines.

---

## Phase 6 — Evaluation, comparison, failure analysis ⬜

1. **9 actual-vs-predicted plots** (3 models × 3 areas) over the test week, plus a zoomed
   single-day panel per area so lag structure is visible.
2. **Three per-area metric tables** with all three models **and both baselines** —
   MAE, MAPE, RMSE, sMAPE, MASE.
3. **Cross-area comparison using MASE**, since the areas differ by an order of magnitude
   and raw MAE is not comparable across them.
4. **Diagnostics:** error by hour-of-day and weekday/weekend (heatmap); residual ACF per
   model; **lag-1 copying check** — cross-correlate predictions with actuals and test for
   a peak at lag 1, and compare each model against persistence. Given lag-1 ACF of 0.987,
   collapse to `x̂(t+1)≈x(t)` is a live risk. **Report it honestly if it happens.**
5. **Failure analysis:** worst contiguous windows per model; run all models on the
   **stress split** (Dec 23 – Jan 1), which holds four of the eight holidays. Expect
   seasonal naive to fail badly around Christmas. Start from the Phase 3 predictions:
   152 flagged intervals, 1.78× holiday enrichment, and 2 December unexplained.

> **CHECKPOINT 6** — full results tables and the headline comparative finding.

---

## Phase 7 — Reproducibility and repo polish ⬜

1. `README.md`: summary, hardware, setup, `run.py all` description, the
   **"reproduce without downloading 19.4 GiB"** path, expected runtimes, results inline.
2. Task runner targets complete.
3. Verify from a clean clone: fresh venv, no-download path end to end, metrics reproduce
   to 3 significant figures with fixed seeds.
4. Lint and format across `src/`.
5. `results/environment.json` finalised; MIT licence; note the dataset's ODbL terms.

---

## Phase 8 — Report support artefacts 🟡

Claude Code produces the **evidence**, not the prose. The human writes the report.

1. Every figure at 300 dpi in `report/figures/`. ✅ *(8 exported)*
2. Every table in `report/tables/` as CSV and Markdown. ✅ *(12 exported)*
3. `report/RESULTS_SUMMARY.md` — factual, uninterpreted dump of every number the report
   might cite. ✅ *(scaffolded; Methodology/Results sections pending Phases 4–6)*
4. `report/FIGURE_INDEX.md` mapping each figure to its report section. ✅

**Do not draft the report narrative.** The brief requires original analysis and warns
explicitly against AI-generated reports; reduced marks and academic-misconduct risk attach
to that, and a viva may ask the author to defend the reasoning as their own. Produce
numbers and figures; the human writes the interpretation.

---

## Appendix A — `CLAUDE.md` for the repo root

See `CLAUDE.md`. Non-negotiables: logic in `src/`; all config in YAML; fit transforms on
train only; every experiment logged with a rationale; never commit raw data; timestamps
epoch-ms UTC converted to Europe/Rome; aggregate over country code; metrics in original
units; baselines in every table. Stop and ask before changing the model line-up, the
splits or the evaluation protocol, if a gap falls in the test week, or before writing
report prose.

---

## Appendix B — Open questions, resolved

| # | Question | Resolution |
|---|---|---|
| 1 | Top-3 by traffic, or {top-1, 4159, 4556}? | **{5161, 4159, 4556}.** Confirmed by measurement: the top three are within 470 m and cannot answer the research question. |
| 2 | Native 10-minute or hourly? | **Native 10-minute.** |
| 3 | Walk-forward with true observed history? | **Yes.** Not a recursive rollout. |
| 4 | Univariate, or SMS/call/neighbours as exogenous? | **Univariate.** Multivariate listed as future work. |
| 5 | Per-area or one shared model? | **Per-area.** |
| 6 | May Dec 23 – Jan 1 be a stress set? | **Yes**, never tuned on. |
| 7 | Do naive baselines count toward the three? | **No**, they are extra. |
| 8 | May sMAPE/WAPE/MASE supplement MAPE? | **Yes.** MASE is the cross-area comparison. |
| 9 | Model 3 — LightGBM or TCN? | **LightGBM.** |

### Resolved during execution

| Question | Resolution |
|---|---|
| Python version | **3.12** — 3.14 lacks reliable wheels for torch/lightgbm/geopandas. |
| Where does work run? | **Hybrid.** `src/`+tests local; ingest and training on Kaggle. |
| Missing-data policy | Absent cell → `0.0` and counted (a row exists only where activity occurred). Whole missing intervals: interpolate ≤ 3, else NaN and report; raise if inside the test week. **Never fired — the grid is complete.** |
| Per-day storage format | `.npy` + JSON sidecar, not Parquet. |
| Ingest strategy for the full run | `polars_lazy` — Kaggle has ~30 GB RAM, so speed wins. |

---

## Appendix C — Open items for the human

- **Publish the processed Kaggle output as a Dataset** and note the slug. Phase 5 needs it
  so the training notebook attaches it rather than re-deriving the matrix.
- **`data/raw/*.txt` (1.3 GB, 4 days)** is no longer needed except to re-run the local
  memory benchmark. Keeping one file preserves that ability.
- **2 December** remains unexplained — 17 flagged intervals, the worst single day, not a
  holiday. Worth a sentence in the failure analysis either way.
