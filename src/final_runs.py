"""Final fits on train plus validation, evaluated on the test week.

Once hyperparameters are selected, the validation split has done its job and
withholding it from the fit would discard a week of data the model is entitled
to learn from. The final fit therefore uses train plus validation, and the test
week is never touched until prediction.

That creates a problem for the two models that stop early, because there is no
longer a held-out set to stop on. Refitting with early stopping against the test
week would be leakage; refitting without any stopping rule would overfit. The
resolution is to carry the *complexity* found during tuning rather than the
stopping rule: the LSTM trains for the epoch count that was best on validation,
and LightGBM uses the tree count early stopping chose. Both numbers were decided
before the final fit and without seeing the test data.

Neural results are reported over three seeds with a standard deviation, because
a single seed reports one draw from a distribution and the spread is often
comparable to the difference between models.
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from src.config import Config, load_config
from src.eda import SelectedAreas
from src.evaluate import load_area_series
from src.metrics import Metrics, evaluate
from src.models.base import Forecaster
from src.models.baselines import Persistence, SeasonalNaive
from src.models.gbm import GBMConfig, GBMForecaster
from src.models.harmonic_arima import HarmonicARIMA
from src.models.lstm import LSTMConfig, LSTMForecaster
from src.splits import SplitSet, make_splits

__all__ = ["FinalResult", "run_final", "build_model"]


@dataclass
class FinalResult:
    """One model on one area, across however many seeds it was run with."""

    square_id: int
    model: str
    split: str
    metrics: list[Metrics] = field(default_factory=list)
    predictions: list[np.ndarray] = field(default_factory=list)
    train_wall_s: list[float] = field(default_factory=list)
    inference_wall_s: list[float] = field(default_factory=list)
    n_params: int = 0
    lag1_copy_ratio: float = float("nan")
    device: str = "cpu"
    extra: dict[str, Any] = field(default_factory=dict)

    def _spread(self, attribute: str) -> tuple[float, float]:
        values = [getattr(m, attribute) for m in self.metrics]
        mean = statistics.fmean(values)
        std = statistics.stdev(values) if len(values) > 1 else 0.0
        return mean, std

    def to_row(self) -> dict[str, Any]:
        mae, mae_std = self._spread("mae")
        rmse, rmse_std = self._spread("rmse")
        mape, _ = self._spread("mape")
        smape, _ = self._spread("smape")
        mase, mase_std = self._spread("mase")
        r2, _ = self._spread("r2")
        bias, _ = self._spread("bias")

        return {
            "square_id": self.square_id,
            "model": self.model,
            "split": self.split,
            "n_seeds": len(self.metrics),
            "mae": round(mae, 4),
            "mae_std": round(mae_std, 4),
            "rmse": round(rmse, 4),
            "rmse_std": round(rmse_std, 4),
            "mape": round(mape, 4),
            "smape": round(smape, 4),
            "mase": round(mase, 5),
            "mase_std": round(mase_std, 5),
            "r2": round(r2, 5),
            "bias": round(bias, 4),
            "n_params": self.n_params,
            # Training times are not comparable across devices, so the device is
            # carried into the table rather than left to a caption.
            "device": self.device,
            "lag1_copy_ratio": round(self.lag1_copy_ratio, 4),
            "train_wall_s": round(statistics.fmean(self.train_wall_s), 3)
            if self.train_wall_s
            else 0.0,
            "train_wall_std": round(statistics.stdev(self.train_wall_s), 3)
            if len(self.train_wall_s) > 1
            else 0.0,
            "inference_wall_s": round(statistics.fmean(self.inference_wall_s), 4),
            "inference_ms_per_step": round(
                1000 * statistics.fmean(self.inference_wall_s) / max(self.metrics[0].n, 1), 4
            ),
        }

    @property
    def mean_predictions(self) -> np.ndarray:
        """Seed-averaged forecasts, which is what the plots show."""
        return np.mean(np.vstack(self.predictions), axis=0)


def build_model(name: str, hyperparams: dict[str, Any], config: Config, seed: int) -> Forecaster:
    """Instantiate one model from its stored configuration.

    Args:
        name: Model identifier.
        hyperparams: The block written by the tuning stage.
        config: Study configuration, for the seasonal periods.
        seed: Random seed for models that use one.

    Raises:
        KeyError: If the model name is not recognised.
    """
    if name == "harmonic_arima":
        return HarmonicARIMA(
            daily_period=config.dataset.daily_period,
            weekly_period=config.dataset.weekly_period,
            k_daily=int(hyperparams["k_daily"]),
            k_weekly=int(hyperparams["k_weekly"]),
            order=tuple(hyperparams["order"]),
        )
    if name == "lstm":
        fields = set(LSTMConfig.__dataclass_fields__)
        return LSTMForecaster(
            LSTMConfig(**{k: v for k, v in hyperparams.items() if k in fields}), seed=seed
        )
    if name == "lightgbm":
        fields = set(GBMConfig.__dataclass_fields__)
        return GBMForecaster(
            GBMConfig(**{k: v for k, v in hyperparams.items() if k in fields}), seed=seed
        )
    raise KeyError(f"unknown model {name!r}")


def _fit_final(
    model: Forecaster, splits: SplitSet, name: str, hyperparams: dict[str, Any]
) -> float:
    """Fit on train plus validation, carrying the tuned complexity.

    Early stopping is disabled here because there is no held-out set left; the
    epoch or tree count selected during tuning is used instead.
    """
    values, times = splits.fit_values, splits.fit_times

    if name == "lstm":
        best_epoch = int(hyperparams.get("best_epoch", -1))
        if best_epoch >= 0:
            model.config.max_epochs = best_epoch + 1
            model.config.patience = model.config.max_epochs + 1  # never triggers
    elif name == "lightgbm":
        best_iteration = int(hyperparams.get("best_iteration", 0))
        if best_iteration > 0:
            model.config.n_estimators = best_iteration
            model.config.early_stopping_rounds = 0

    started = time.perf_counter()
    model.fit(values, train_times=times)
    return time.perf_counter() - started


def _lag1_copy_ratio(predictions: np.ndarray, series: np.ndarray, start: int, stop: int) -> float:
    """How far the forecasts sit from simply repeating the last observation.

    Near zero means the model has collapsed to persistence. With a lag-1
    autocorrelation of 0.987 that is a live risk for every model here, not only
    the neural one.
    """
    values = np.asarray(series, dtype=np.float64)
    persistence = values[start - 1 : stop - 1]
    movement = float(np.mean(np.abs(np.diff(values[start - 1 : stop]))))
    if movement == 0:
        return float("nan")
    return float(np.mean(np.abs(predictions - persistence)) / movement)


def run_final(
    config: Config,
    *,
    split_name: str = "test",
    seeds: tuple[int, ...] | None = None,
) -> list[FinalResult]:
    """Fit and evaluate every model on every study area.

    Args:
        config: Study configuration.
        split_name: Split to report on. The test week by default.
        seeds: Seeds for stochastic models. Defaults to ``config.seeds``.

    Returns:
        One :class:`FinalResult` per (area, model).
    """
    seeds = seeds or config.seeds
    selected_path = config.paths.tables / "selected_hyperparameters.json"
    if not selected_path.exists():
        raise FileNotFoundError(
            f"{selected_path} not found. Run `python run.py train` to select "
            "hyperparameters before the final runs."
        )
    selected = json.loads(selected_path.read_text(encoding="utf-8"))
    areas = SelectedAreas.load(config.paths.tables / "selected_areas.json")

    # Models whose result varies with the seed are run over all of them.
    seeds_for = {"harmonic_arima": (seeds[0],), "lightgbm": (seeds[0],), "lstm": seeds}
    results: list[FinalResult] = []

    for square_id in areas.forecast:
        values, times = load_area_series(config, square_id)
        splits = make_splits(values, times, config)
        split = splits[split_name]
        print(f"\n=== square {square_id}, {split_name} split ===")

        for baseline in (Persistence(), SeasonalNaive(config.dataset.daily_period)):
            started = time.perf_counter()
            predictions = baseline.walk_forward(
                splits.series, split.start, split.stop, times=splits.times
            )
            wall = time.perf_counter() - started
            metrics = evaluate(
                split.values,
                predictions,
                y_train=splits.train.values,
                seasonal_period=config.evaluation.seasonal_period,
                mape_threshold=config.evaluation.mape_zero_threshold,
            )
            result = FinalResult(
                square_id=square_id,
                model=baseline.name,
                split=split_name,
                metrics=[metrics],
                predictions=[predictions],
                inference_wall_s=[wall],
                lag1_copy_ratio=_lag1_copy_ratio(
                    predictions, splits.series, split.start, split.stop
                ),
            )
            results.append(result)
            print(f"  {baseline.name:<16} {metrics.summary()}")

        for name in ("harmonic_arima", "lstm", "lightgbm"):
            hyperparams = selected.get(name)
            if hyperparams is None:
                continue

            result = FinalResult(square_id=square_id, model=name, split=split_name)
            for seed in seeds_for[name]:
                model = build_model(name, hyperparams, config, seed)
                train_wall = _fit_final(model, splits, name, hyperparams)

                started = time.perf_counter()
                predictions = model.walk_forward(
                    splits.series, split.start, split.stop, times=splits.times
                )
                inference_wall = time.perf_counter() - started

                result.metrics.append(
                    evaluate(
                        split.values,
                        predictions,
                        y_train=splits.train.values,
                        seasonal_period=config.evaluation.seasonal_period,
                        mape_threshold=config.evaluation.mape_zero_threshold,
                    )
                )
                result.predictions.append(predictions)
                result.train_wall_s.append(train_wall)
                result.inference_wall_s.append(inference_wall)
                result.n_params = model.n_params()
                if hasattr(model, "describe"):
                    result.extra = model.describe()
                    result.device = str(result.extra.get("device", "cpu"))

            result.lag1_copy_ratio = _lag1_copy_ratio(
                result.mean_predictions, splits.series, split.start, split.stop
            )
            results.append(result)

            row = result.to_row()
            spread = f" +/- {row['mae_std']:.2f}" if row["n_seeds"] > 1 else ""
            print(
                f"  {name:<16} MAE {row['mae']:>8.2f}{spread}  "
                f"MASE {row['mase']:.3f}  R2 {row['r2']:.4f}  "
                f"copy {row['lag1_copy_ratio']:.2f}  "
                f"({row['train_wall_s']:.0f}s train)"
            )

        _save_predictions(results, splits, split, config, square_id, split_name)

    _write_tables(results, config, split_name)
    return results


def _save_predictions(
    results: list[FinalResult],
    splits: SplitSet,
    split: Any,
    config: Config,
    square_id: int,
    split_name: str,
) -> Path:
    """Persist observed and predicted series for the plots in Phase 6."""
    import polars as pl

    columns: dict[str, Any] = {
        "local": splits.times[split.start : split.stop],
        "observed": split.values,
    }
    for result in results:
        if result.square_id == square_id and result.split == split_name:
            columns[result.model] = result.mean_predictions

    path = config.paths.predictions / f"{split_name}_area_{square_id}.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    pl.DataFrame(columns).write_parquet(path, compression="zstd")
    return path


def _write_tables(results: list[FinalResult], config: Config, split_name: str) -> list[Path]:
    """Write per-area metric tables and a combined one."""
    written: list[Path] = []
    rows = [r.to_row() for r in results]

    by_area: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        by_area.setdefault(row["square_id"], []).append(row)

    for square_id, area_rows in by_area.items():
        path = config.paths.tables / f"final_metrics_area_{square_id}_{split_name}.csv"
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(area_rows[0]))
            writer.writeheader()
            writer.writerows(sorted(area_rows, key=lambda r: r["mase"]))
        written.append(path)

    path = config.paths.tables / f"final_metrics_all_{split_name}.csv"
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    written.append(path)

    timing = [
        {
            "model": row["model"],
            "square_id": row["square_id"],
            "device": row["device"],
            "n_seeds": row["n_seeds"],
            "train_wall_s": row["train_wall_s"],
            "train_wall_std": row["train_wall_std"],
            "inference_wall_s": row["inference_wall_s"],
            "inference_ms_per_step": row["inference_ms_per_step"],
            "n_params": row["n_params"],
        }
        for row in rows
    ]
    path = config.paths.tables / f"timing_{split_name}.csv"
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(timing[0]))
        writer.writeheader()
        writer.writerows(timing)
    written.append(path)

    return written


def build_parser() -> argparse.ArgumentParser:
    """Construct the argument parser for this entry point."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", default=None, help="Path to a config YAML.")
    parser.add_argument(
        "--split",
        default="test",
        choices=("test", "stress"),
        help="Split to report on. Reported results use the test week.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the final fits and write the result tables."""
    args = build_parser().parse_args(argv)
    config = load_config(args.config)
    config.paths.mkdirs()
    run_final(config, split_name=args.split)
    print(f"\nwrote tables to {config.paths.tables}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
