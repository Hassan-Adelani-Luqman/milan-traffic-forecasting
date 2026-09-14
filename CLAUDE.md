# Project brief

Forecasting mobile internet traffic in Milan (Telecom Italia CDR, Nov 2013 - Jan 2014),
one step ahead (10 min), evaluated on 16-22 Dec 2013 across three areas.

## Where things run

Hybrid. `src/`, `config/` and `tests/` are developed and version-controlled locally;
ingest, EDA and model training run on Kaggle via thin notebooks that `git clone` this
repo and import from `src/`. Notebooks never define model or preprocessing logic.

Kaggle disk budget: `/kaggle/working` is ~20 GB and persisted; everything else is
~60 GB of scratch that vanishes at session end. The 20 GB of raw text therefore goes
to `/kaggle/temp/raw` and is deleted file-by-file as it is converted to parquet.
Session cap is 12 h, so the ingest checkpoints per day and resumes.

## Non-negotiables

- Logic in `src/`, notebooks only render figures.
- All config in `config/default.yaml` (+ `config/kaggle.yaml` overrides); no hardcoded
  paths, dates, or hyperparameters anywhere in `src/`.
- Fit scalers and transforms on the training split ONLY.
- Every experiment appends a row to `results/experiments.csv` with a non-empty
  `rationale_for_next_change`.
- Never commit `data/raw/` or `data/interim/`. Always commit
  `data/processed/selected_series.parquet`.
- Timestamps are epoch-ms UTC; always convert to Europe/Rome.
- Rows are split by country code - always aggregate before use.
- Report metrics in original units, after inverse-transforming.
- Persistence and seasonal-naive baselines appear in every results table.
- `walk_forward` with true observed history is the only inference path used for
  reported results. Not a recursive rollout.

## Resolved decisions

- Python 3.12 (3.14 lacks reliable wheels for torch/lightgbm/geopandas).
- Forecasting areas: {top-1 by total traffic, 4159, 4556}. Top-2/top-3 in an appendix.
- Model line-up: dynamic harmonic regression (SARIMAX + Fourier), LSTM, LightGBM.
- Native 10-minute resolution, univariate, per-area models.
- Dec 23 - Jan 1 is a held-out stress split, never tuned on.

## Stop and ask

- Before changing the model line-up.
- Before changing split dates or the evaluation protocol.
- If any data gap falls inside the test week.
- Before writing any report narrative prose.
