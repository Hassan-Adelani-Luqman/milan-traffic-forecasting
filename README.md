# Milan Mobile Network Traffic Forecasting

A comparative study of three sequential models for **one-step-ahead** (10-minute)
forecasting of mobile internet traffic in Milan, using the Telecom Italia Big Data
Challenge call-detail-record dataset (1 November 2013 – 1 January 2014).

**Research question.** How do different sequential models compare for one-step-ahead
mobile network traffic forecasting, and how does their performance vary across
geographical areas with different traffic characteristics?

> **Status: data stage complete** (download, ingest, matrix assembly, memory evidence).
> Sections marked _pending_ are filled in as later phases land.

---

## The data

| Property | Value |
|---|---|
| Source | Harvard Dataverse `doi:10.7910/DVN/EGZHFV` |
| Grid geometry | `doi:10.7910/DVN/QJWLFU` (Milano Grid, GeoJSON) |
| Coverage | 2013-11-01 → 2014-01-01, 62 daily TSV files |
| Raw size | 19.38 GiB (20,804,803,507 B), 265–359 MiB per file |
| Spatial grid | 100 × 100 cells of 235 m, square ids 1–10000 |
| Temporal resolution | 10 minutes → 144 intervals/day → 8,928 timestamps |
| Target variable | `internet` (normalised CDR activity, not an integer count) |

Three properties of the raw files drive the whole design:

1. **Rows are split by country code.** A single `(square_id, time_ms)` pair appears
   many times, once per counterparty country. Traffic must be aggregated with
   `group_by(["square_id", "time_ms"]).sum()` before use — this is why a day holds
   ~5.16 M rows rather than 1.44 M (3.6 country rows per cell on average, at most 36).
2. **After aggregation the data is small.** The full `8928 × 10000` matrix is 340.6 MiB
   as `float32`. The memory-management problem is entirely about getting from 20 GB of
   text to that matrix without ever holding more than one day in RAM.
3. **Timestamps are epoch milliseconds in UTC, but files are aligned to *local*
   midnight.** The first record of the 1 November file is `1383260400000` =
   `2013-10-31 23:00 UTC` = `2013-11-01 00:00` CET. All conversion goes through
   `Europe/Rome`, or every diurnal pattern shifts by an hour.

---

## Where things run

This project is **hybrid** by design:

- **Locally** (Windows, Python 3.12): `src/`, `config/` and `tests/` are developed and
  version-controlled. Tests run in seconds without a GPU.
- **On Kaggle** (Linux, P100/T4): ingest, exploratory analysis and all model training.
  Notebooks `git clone` this repo and import from `src/` — they contain no model or
  preprocessing logic of their own.

Kaggle's disk budget shapes the ingest: `/kaggle/working` is ~20 GB and persisted,
while everything else is ~60 GB of scratch that is discarded at session end. The 20 GB
of raw text therefore streams into `/kaggle/temp/raw` and each file is **deleted as soon
as its per-day block is written**, holding peak disk near one file. Blocks are
checkpointed into `/kaggle/working` so a 12-hour session timeout resumes rather than
restarts.

---

## Setup

### Local

```bash
git clone <repo-url>
cd milan-traffic-forecasting

py -V:3.12 -m venv .venv                       # Windows
.venv\Scripts\pip install -r requirements-local.txt

# Verify the scaffold and record your hardware
.venv\Scripts\python run.py test
.venv\Scripts\python run.py env
```

On macOS/Linux substitute `python3.12 -m venv .venv` and `.venv/bin/pip`.

### Kaggle

`notebooks/00_kaggle_ingest.ipynb` runs the whole data stage. Upload it to Kaggle, then:

1. **Settings -> Internet -> On** (requires a phone-verified account).
2. **Add-ons -> Secrets**: add `DATAVERSE_GB_NAME`, `DATAVERSE_GB_EMAIL`,
   `DATAVERSE_GB_INSTITUTION`, `DATAVERSE_GB_POSITION`. Harvard Dataverse gates this
   dataset behind a Guestbook and records one response per download request, so these
   must be real details.
3. **Accelerator -> None.** This stage is I/O-bound; save the GPU quota for modelling.
4. Edit `REPO_URL` in the settings cell to point at this repository.
5. **Save Version -> Save & Run All (Commit).** `/kaggle/working` is only persisted by a
   committed version.
6. On the finished version: **Output -> New Dataset**. Later notebooks attach that
   dataset and never need the raw data or internet again.

`src.config` detects the Kaggle session automatically and layers `config/kaggle.yaml`
over the defaults, so no path edits are needed.

The notebook is generated from `notebooks/build_kaggle_notebook.py` rather than edited
by hand, which keeps it thin and keeps it honest: `tests/test_notebook.py` asserts that
every `src` symbol it imports still exists and that it defines no functions or classes
of its own.

#### Why the ingest streams

`/kaggle/temp` is scratch discarded at session end and sessions are capped at 12 hours.
Downloading all 62 files and then ingesting would, on a timeout at hour 11, lose every
raw file and leave nothing behind. `src/pipeline.py` interleaves instead: download one
day, convert it to a dense block, write the block to `/kaggle/working`, delete the raw
text, repeat. Peak disk stays near one file (~350 MB) rather than 19.4 GiB, and every
finished day is a durable artefact a resumed run skips.

---

## Running the pipeline

`make` is not available on a default Windows install, so `run.py` is the canonical
entry point on both platforms. The `Makefile` mirrors the same targets for Linux.

```bash
python run.py env        # record hardware -> results/environment.json
python run.py download   # fetch the 62 daily files + grid GeoJSON
python run.py ingest     # raw text -> per-day blocks, with memory evidence
python run.py pipeline   # stream download -> ingest -> delete (what Kaggle runs)
python run.py benchmark  # compare ingest strategies in isolated processes
python run.py matrix     # assemble the 8928 x 10000 matrix
python run.py eda        # exploratory figures, statistics, selected series
python run.py train      # tune the three models (--models to select a subset)
python run.py final      # refit on train+validation, evaluate on the test week
python run.py results    # evaluation figures, diagnostics, failure analysis
python run.py evaluate   # baseline metrics for any split
python run.py all        # everything above, in order
```

Any task accepts `--config` and forwards remaining arguments to its module:

```bash
python run.py ingest --config config/kaggle.yaml --limit 3
```

### Reproducing results without the 20 GB download

Four artefacts are committed so that everything after ingest reproduces from a clean
clone: `data/processed/selected_series.parquet` (the extracted series, 283 KB),
`results/tables/selected_areas.json`, `results/tables/selected_hyperparameters.json`,
and `results/predictions/*.parquet` (the forecasts, 312 KB).

```bash
git clone <this repo> && cd milan-traffic-forecasting
python -m venv .venv && .venv/Scripts/activate      # source .venv/bin/activate on Linux
pip install -r requirements.txt

python run.py test                     # 458 tests, ~7 min
python run.py evaluate --split test    # baseline metrics from the committed series
python run.py results --split test     # 28 figures + 6 tables from the committed forecasts
python run.py results --split stress   # the same for the holiday split
```

Verified end to end: a fresh clone into an empty virtualenv reproduces every reported
metric **exactly**, not merely to 3 significant figures.

What this path cannot do, and why:

| Stage | Needs | Why it is excluded |
|---|---|---|
| `download`, `ingest`, `matrix` | 19.4 GiB of raw CDR text | Not redistributable; `data/raw/` is gitignored |
| parts of `eda` | `traffic_matrix.npy` (341 MB) | Derived from the raw text, too large to commit |
| `final` (LSTM rows) | a CUDA device | On CPU the nine LSTM fits take roughly 31 hours |

The committed prediction series exist precisely because of that last row: the LSTM
columns cannot be regenerated on a CPU in reasonable time, so without them the figures
could not be redrawn from a clean clone.

---

## Configuration

`config/default.yaml` is the single source of truth for paths, dates, split boundaries
and preprocessing defaults; `config/kaggle.yaml` overrides only what the Kaggle
environment changes. Nothing in `src/` hardcodes a path, date or hyperparameter.

Loading is strict — an unknown key is an error, not a silently ignored typo — and the
splits are validated as contiguous, non-overlapping and inside the observation period:

| Split | Dates (inclusive, `Europe/Rome`) | Points | Purpose |
|---|---|---|---|
| train | 2013-11-01 → 2013-12-08 | 5,472 | Model fitting; all transforms fit here only |
| validation | 2013-12-09 → 2013-12-15 | 1,008 | Hyperparameter selection |
| test | 2013-12-16 → 2013-12-22 | 1,008 | Reported results (the week the brief fixes) |
| stress | 2013-12-23 → 2014-01-01 | 1,440 | Failure analysis only; never tuned on |

---

## Repository layout

```
├── config/           default.yaml + kaggle.yaml overrides
├── src/              all logic: ingest, features, models, evaluation
│   └── models/       baselines, harmonic ARIMA, LSTM, LightGBM
├── notebooks/        thin: import from src/, render figures only
├── tests/            leakage, scaler, split and metric correctness
├── results/          experiments.csv, figures, tables, predictions
├── report/           figures and tables exported for the write-up
├── run.py            cross-platform task runner
└── Makefile          equivalent targets for Linux/Kaggle
```

---

## Data handling and memory

Measured on the hardware recorded in `results/environment.json`, one process per
measurement (see `results/tables/memory_report.csv`):

| strategy | resident/day | peak RSS | wall/day | scales with days |
|---|---:|---:|---:|---|
| naive pandas | 295.6 MiB | 633.1 MiB | 5.56 s | yes |
| chunked pandas | 5.5 MiB | 172.6 MiB | 5.86 s | no |
| Polars lazy | 5.5 MiB | 552.2 MiB | 0.95 s | no |

The headline is scaling rather than peak: holding all 62 days the naive way needs
**17.90 GiB** resident, while both optimised paths hold one 5.49 MiB block at a time
regardless of dataset size, producing a **340.58 MiB** final matrix.

Polars is ~6x faster but peaks ~3.2x higher, because its CSV reader holds the whole
~322 MB file; `low_memory=True` and `read_csv_batched` were both measured and made it
worse. Neither strategy dominates, so `--strategy` selects and both are kept.

Each measurement runs in its own process. Measuring three strategies in one interpreter
reported 544, 184 and 384 MiB for identical work, because freed arenas are not returned
to the OS and whichever ran first paid for the heap growth.

## Methodology

One-step-ahead (10 minute) forecasting, univariate, one model per area, at the data's
native resolution. Inference is always `walk_forward` with true observed history — not a
recursive rollout — so each forecast uses real observations up to the step before the one
it predicts.

**Three models, each chosen for a stated reason.**

| Model | Why it is here | Params |
|---|---|---:|
| Dynamic harmonic regression | SARIMAX with Fourier terms. Plain SARIMA cannot express two seasonalities at once and s=144 is intractable. | 22 |
| LSTM | The only candidate that assumes nothing about seasonal form. | 202,369 |
| LightGBM | Gradient boosting won M5; prior work on this dataset evaluated random forests but not boosting. | 19,639 |

**Two baselines appear in every table.** With a lag-1 autocorrelation of 0.987,
persistence is not a straw man — it is the bar that decides whether complexity earned
its place.

**Tuning** ran on the highest-traffic area only, selecting on validation MAE, one axis at
a time so each decision is attributable. Harmonic order was chosen by AICc (refitting 15
candidates through walk-forward would have cost far more than an information criterion);
LightGBM used Optuna over 30 trials because tree parameters interact too strongly for a
staged sweep; the LSTM used five staged sweeps. Every candidate — 101 in total — appends a
row to `results/experiments.csv` with the reasoning that produced the next change.

**The final fit uses train + validation**, since the validation split has done its job by
then. Neither early-stopping model has a held-out set left, so each carries the
*complexity* tuning chose rather than the stopping rule: the LSTM trains for its best
epoch count with patience disabled, LightGBM uses its selected 320 trees. The LSTM is run
over three seeds and reported as mean ± standard deviation.

## Results

Test week, 16–22 Dec 2013. MASE is the comparable metric: the areas differ by an order of
magnitude in volume, so raw MAE cannot be compared across them.

| Model | 5161 | 4159 | 4556 | mean |
|---|---:|---:|---:|---:|
| **harmonic ARIMA** | 0.241 | **0.166** | **0.230** | **0.213** |
| LightGBM | 0.249 | 0.186 | 0.267 | 0.234 |
| persistence | 0.267 | 0.195 | 0.257 | 0.240 |
| LSTM (3-seed ensemble) | **0.233** | 0.253 | 0.249 | 0.245 |
| LSTM (mean of 3 seeds) | 0.265 | 0.259 | 0.257 | 0.260 |
| seasonal naive | 0.975 | 0.626 | 0.680 | 0.760 |

**The 22-parameter model wins.** Harmonic ARIMA has the best mean MASE and wins two of
three areas; a three-seed LSTM ensemble takes the third. Averaged across areas, only
harmonic ARIMA and LightGBM beat persistence — both LSTM variants do not.

**Complexity did not survive the holidays.** On the held-out stress split (23 Dec – 1 Jan,
never tuned on) persistence wins outright on two of three areas, while LightGBM degrades
by 69–140% and the LSTM by 78–103%. Harmonic ARIMA stays within 9%. This confirms a
prediction written into `src/models/gbm.py` before the split was ever run: a tree ensemble
cannot extrapolate beyond the range of its training targets, and a holiday period is
exactly where that bites.

**Cost inverts between training and inference** (square 5161, 1,008 forecasts):

| Model | Device | Train | Inference | Per step |
|---|---|---:|---:|---:|
| harmonic ARIMA | CPU | 18.0 s | 75.2 s | 74.6 ms |
| LightGBM | CPU | 5.0 s | 0.022 s | 0.022 ms |
| LSTM | GPU (T4) | 9.9 s | 0.041 s | 0.041 ms |

The cheapest model to train is by far the most expensive to serve: `append(refit=False)`
still runs a Kalman update per step, making harmonic ARIMA ~1,800× slower at inference
than the LSTM. Training times are not comparable across devices, which is why every
results and timing table carries a `device` column. On a CPU a single LSTM fit at the
tuned size took 13.8 hours against 2.6 seconds on a T4 — a 776× difference measured on
identical configuration.

**No model collapsed to persistence.** With lag-1 autocorrelation at 0.987 this was a real
risk, so it was tested two ways and reported either way; copy ratios run 0.54–1.14 against
persistence's 0.00. See `results/tables/copying_test.csv`.

---

## Licence and data terms

Code in this repository is released under the MIT Licence. The underlying dataset is
distributed by Harvard Dataverse under its own terms (ODbL); it is not redistributed
here, and `data/raw/` is excluded from version control.

## References

1. G. Barlacchi *et al.*, "A multi-source dataset of urban life in the city of Milan and
   the Province of Trentino," *Scientific Data*, vol. 2, 150055, 2015.
   doi:10.1038/sdata.2015.55
