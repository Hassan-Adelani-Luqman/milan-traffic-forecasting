# Milan Mobile Network Traffic Forecasting

A comparative study of three sequential models for **one-step-ahead** (10-minute)
forecasting of mobile internet traffic in Milan, using the Telecom Italia Big Data
Challenge call-detail-record dataset (1 November 2013 – 1 January 2014).

**Research question.** How do different sequential models compare for one-step-ahead
mobile network traffic forecasting, and how does their performance vary across
geographical areas with different traffic characteristics?

> **Status: Phase 0 (scaffold) complete.** Sections marked _pending_ are filled in as
> later phases land.

---

## The data

| Property | Value |
|---|---|
| Source | Harvard Dataverse `doi:10.7910/DVN/EGZHFV` |
| Grid geometry | `doi:10.7910/DVN/QJWLFU` (Milano Grid, GeoJSON) |
| Coverage | 2013-11-01 → 2014-01-01, 62 daily TSV files |
| Raw size | ~19–20 GB (~300–355 MB per file) |
| Spatial grid | 100 × 100 cells of 235 m, square ids 1–10000 |
| Temporal resolution | 10 minutes → 144 intervals/day → 8,928 timestamps |
| Target variable | `internet` (CDR count) |

Three properties of the raw files drive the whole design:

1. **Rows are split by country code.** A single `(square_id, time_ms)` pair appears
   many times, once per counterparty country. Traffic must be aggregated with
   `group_by(["square_id", "time_ms"]).sum()` before use — this is why a day holds
   ~7 M rows rather than 1.44 M.
2. **After aggregation the data is small.** The full `8928 × 10000` matrix is ~357 MB
   as `float32`. The memory-management problem is entirely about getting from 20 GB of
   text to that matrix without ever holding more than one day in RAM.
3. **Timestamps are epoch milliseconds in UTC; Milan runs on CET.** All conversion goes
   through `Europe/Rome`, or every diurnal pattern shifts by an hour.

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
as its per-day parquet is written**, holding peak disk near 1 GB. Per-day parquet is
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

In the first notebook cell:

```python
!git clone --depth 1 <repo-url> /kaggle/working/repo
!pip install -q -r /kaggle/working/repo/requirements-kaggle.txt
import sys; sys.path.insert(0, "/kaggle/working/repo")
```

`src.config` detects the Kaggle session automatically and layers `config/kaggle.yaml`
over the defaults, so no path edits are needed.

---

## Running the pipeline

`make` is not available on a default Windows install, so `run.py` is the canonical
entry point on both platforms. The `Makefile` mirrors the same targets for Linux.

```bash
python run.py env        # record hardware -> results/environment.json
python run.py download   # fetch the 62 daily files + grid GeoJSON
python run.py ingest     # raw text -> per-day parquet, with memory evidence
python run.py matrix     # assemble the 8928 x 10000 matrix
python run.py eda        # exploratory figures, statistics, selected series
python run.py train      # train and tune the three models
python run.py evaluate   # test-week metrics, plots and diagnostics
python run.py all        # everything above, in order
```

Any task accepts `--config` and forwards remaining arguments to its module:

```bash
python run.py ingest --config config/kaggle.yaml --limit 3
```

### Reproducing results without the 20 GB download

_Pending (Phase 7)._ `data/processed/selected_series.parquet` — the five extracted
series, a few hundred KB — is committed to this repository specifically so the
modelling and evaluation stages reproduce without touching the raw dataset.

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

## Methodology

_Pending (Phases 3–5)._ Model line-up, input representation and tuning protocol are
documented here once Phase 5 completes.

## Results

_Pending (Phase 6)._

---

## Licence and data terms

Code in this repository is released under the MIT Licence. The underlying dataset is
distributed by Harvard Dataverse under its own terms (ODbL); it is not redistributed
here, and `data/raw/` is excluded from version control.

## References

1. G. Barlacchi *et al.*, "A multi-source dataset of urban life in the city of Milan and
   the Province of Trentino," *Scientific Data*, vol. 2, 150055, 2015.
   doi:10.1038/sdata.2015.55
