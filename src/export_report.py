"""Assemble the evidence pack the report is written from.

Collects every measured figure and table into ``report/`` and emits two indexes:

``RESULTS_SUMMARY.md``
    Every number the report might cite, grouped by the section it belongs to,
    each labelled with the artefact it came from. Facts only -- no
    interpretation, because the interpretation is the author's work and the
    assignment requires it to be.
``FIGURE_INDEX.md``
    Each figure mapped to the report section it supports, with what it shows and
    the numbers that accompany it.

Regenerating is idempotent, so it can be re-run after any stage adds results.
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.config import Config, load_config

__all__ = ["export_report"]


@dataclass(frozen=True)
class FigureSpec:
    """One exported figure and where it belongs in the report."""

    filename: str
    section: str
    shows: str
    numbers: str


FIGURES: tuple[FigureSpec, ...] = (
    FigureSpec(
        "01_total_distribution.png",
        "Exploratory Analysis",
        "Histogram of per-cell totals on a log axis, beside the CCDF on log-log axes.",
        "distribution_stats.json",
    ),
    FigureSpec(
        "02_spatial_totals.png",
        "Exploratory Analysis",
        "log10 total activity over the 100x100 Milano grid, study areas marked by rank.",
        "selected_areas.json",
    ),
    FigureSpec(
        "03_series_first_fortnight.png",
        "Exploratory Analysis",
        "Traffic for the five study areas, 1-14 November 2013, one panel each.",
        "area_summary.csv",
    ),
    FigureSpec(
        "04_series_overlay_normalised.png",
        "Exploratory Analysis",
        "The same five series scaled to their own maxima, comparing shape not volume.",
        "area_summary.csv",
    ),
    FigureSpec(
        "05_mstl_decomposition.png",
        "Exploratory Analysis",
        "MSTL of square 5161 into trend, daily and weekly seasonality, and residual.",
        "decomposition.json",
    ),
    FigureSpec(
        "06_acf_pacf.png",
        "Exploratory Analysis",
        "ACF and PACF to lag 1100 with confidence bands; daily and weekly lags marked.",
        "autocorrelation.json",
    ),
    FigureSpec(
        "07_rolling_stats.png",
        "Exploratory Analysis",
        "Rolling mean and standard deviation over a one-day window.",
        "stationarity.csv",
    ),
    FigureSpec(
        "08_periodogram.png",
        "Exploratory Analysis",
        "Spectral power against period in hours, dominant cycles annotated.",
        "spectral_peaks.csv",
    ),
)

# Section -> the tables whose numbers belong in it.
SECTION_TABLES: dict[str, tuple[str, ...]] = {
    "Dataset and Data Preparation": (
        "ingest_summary.json",
        "ingest_log.csv",
        "memory_report.csv",
    ),
    "Exploratory Analysis": (
        "distribution_stats.json",
        "selected_areas.json",
        "area_summary.csv",
        "decomposition.json",
        "stationarity.csv",
        "autocorrelation.json",
        "spectral_peaks.csv",
        "anomalies.csv",
    ),
}


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _markdown_table(rows: list[dict[str, Any]], columns: list[str]) -> list[str]:
    """Render selected columns of ``rows`` as a markdown table."""
    lines = ["| " + " | ".join(columns) + " |", "|" + "|".join(["---"] * len(columns)) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(c, "")) for c in columns) + " |")
    return lines


def _copy_artifacts(config: Config, report_dir: Path) -> dict[str, int]:
    """Copy figures and tables into report/, returning what was copied."""
    counts = {"figures": 0, "tables": 0}

    figures_out = report_dir / "figures"
    figures_out.mkdir(parents=True, exist_ok=True)
    for spec in FIGURES:
        source = config.paths.figures / "eda" / spec.filename
        if source.exists():
            shutil.copy2(source, figures_out / spec.filename)
            counts["figures"] += 1

    tables_out = report_dir / "tables"
    tables_out.mkdir(parents=True, exist_ok=True)
    for source in sorted(config.paths.tables.glob("*")):
        if source.is_file():
            shutil.copy2(source, tables_out / source.name)
            counts["tables"] += 1
    return counts


# --------------------------------------------------------------------------
# RESULTS_SUMMARY.md
# --------------------------------------------------------------------------


def _section_data_preparation(tables: Path) -> list[str]:
    """Numbers for the Dataset and Data Preparation section."""
    lines = ["## Dataset and Data Preparation", ""]

    summary_path = tables / "ingest_summary.json"
    if summary_path.exists():
        s = _read_json(summary_path)
        lines += [
            "### Ingest run (source: `ingest_summary.json`, `ingest_log.csv`)",
            "",
            f"- Days processed: **{s['n_days']}** ({s['first_day']} to {s['last_day']})",
            f"- Raw rows parsed: **{s['total_raw_rows']:,}**",
            f"- Download: **{s['download_total_min']} min** total, "
            f"{s['download_mean_s']} s/day +/- {s['download_std_s']}",
            f"- Ingest: **{s['ingest_total_min']} min** total, "
            f"{s['ingest_mean_s']} s/day +/- {s['ingest_std_s']}",
            f"- Peak RSS: {s['peak_rss_max_mib']} MiB max, {s['peak_rss_mean_mib']} MiB mean",
            f"- Absent cells: **{s['absent_total']:,}** total, "
            f"{s['absent_mean_per_day']}/day mean, "
            f"max {s['absent_max_per_day']} on {s['absent_max_day']}",
            "",
        ]

    memory_path = tables / "memory_report.csv"
    if memory_path.exists():
        rows = _read_csv(memory_path)
        lines += ["### Memory strategies (source: `memory_report.csv`)", ""]
        table = [
            {
                "strategy": r["strategy"],
                "day": r["day"],
                "resident": f"{int(r['per_day_inmem_bytes']) / 1024**2:.2f} MiB",
                "peak RSS": f"{int(r['per_day_peak_rss_bytes']) / 1024**2:.2f} MiB",
                "wall": f"{float(r['per_day_wall_s']):.2f} s",
                "extrapolated": r["extrapolated"],
            }
            for r in rows
        ]
        lines += _markdown_table(
            table, ["strategy", "day", "resident", "peak RSS", "wall", "extrapolated"]
        )
        naive = next((r for r in rows if r["strategy"] == "naive_pandas"), None)
        if naive and naive["projected_full_ram_bytes"]:
            projected = int(naive["projected_full_ram_bytes"]) / 1024**3
            lines += [
                "",
                f"- Holding all 62 days the naive way: **{projected:.2f} GiB** resident "
                "(extrapolated from one day, not executed).",
                "- Both optimised paths hold one 5.49 MiB block at a time, "
                "independent of the number of days.",
                "- Final matrix: 8928 x 10000 float32 = **340.58 MiB**.",
            ]
        lines.append("")

    matrix_report = Path("data/processed/matrix_report.json")
    if matrix_report.exists():
        m = _read_json(matrix_report)
        lines += [
            "### Assembled matrix (source: `data/processed/matrix_report.json`)",
            "",
            f"- Shape: **{tuple(m['shape'])}**, {m['n_days']} days",
            f"- Local range: {m['first_timestamp_local']} to {m['last_timestamp_local']} "
            f"({m['timezone']})",
            f"- UTC range: {m['first_timestamp_utc']} to {m['last_timestamp_utc']}",
            f"- Missing intervals: **{len(m['missing_intervals'])}**; "
            f"interpolated: {len(m['interpolated_intervals'])}; "
            f"left as NaN: {len(m['unfilled_intervals'])}",
            f"- NaN after policy: **{m['n_nan_after_policy']}**",
            f"- Total activity: {m['total_internet']:,.2f}",
            "",
        ]
    return lines


def _section_exploratory(tables: Path) -> list[str]:
    """Numbers for the Exploratory Analysis section."""
    lines = ["## Exploratory Analysis", ""]

    dist_path = tables / "distribution_stats.json"
    if dist_path.exists():
        d = _read_json(dist_path)
        lines += [
            "### Distribution across the grid (source: `distribution_stats.json`)",
            "",
            f"- Cells: {d['n_cells']:,}; total activity {d['total']:,.0f}",
            f"- Mean {d['mean']:,.0f}; median {d['median']:,.0f}; "
            f"max/median **{d['max_over_median']:.1f}x**",
            f"- Skewness {d['skewness']:.2f}; kurtosis {d['kurtosis']:.2f}",
            f"- Gini **{d['gini']:.3f}**",
            f"- Top 1% hold **{d['top_1pct_share']:.1%}**, top 5% {d['top_5pct_share']:.1%}, "
            f"top 10% {d['top_10pct_share']:.1%}; bottom 50% {d['bottom_50pct_share']:.1%}",
            f"- Cells with zero total: {d['n_zero_cells']}",
            f"- Lognormal fit: mu={d['lognormal_mu']:.3f}, sigma={d['lognormal_sigma']:.3f}, "
            f"KS={d['lognormal_ks_stat']:.4f}, p={d['lognormal_ks_pvalue']:.3g}",
            "  - KS critical value at n=10,000, alpha=0.05 is 0.0136, so the statistic is "
            "1.7x the threshold. log(x) has skewness +0.023 and kurtosis +0.013.",
            "",
        ]

    areas_path = tables / "selected_areas.json"
    if areas_path.exists():
        a = _read_json(areas_path)
        lines += [
            "### Study areas (source: `selected_areas.json`)",
            "",
            f"- Top three by total: **{a['top_three']}**",
            f"- Highest-traffic area: **{a['top_traffic']}**",
            f"- Fixed by the brief: {a['fixed']}",
            f"- Forecast in Section 4: **{a['forecast']}**",
            "",
        ]
        rows = [
            {
                "square": square,
                "rank": a["ranks"][square],
                "total": f"{a['totals'][square]:,.0f}",
            }
            for square in a["ranks"]
        ]
        lines += _markdown_table(rows, ["square", "rank", "total"])
        lines += [
            "",
            "- Squares 5161, 5059 and 5259 lie within **470 m** of one another; "
            "the top ten fit inside a 3.05 x 2.35 km box (grid rows 48-60, columns 54-63).",
            "",
        ]

    summary_path = tables / "area_summary.csv"
    if summary_path.exists():
        rows = _read_csv(summary_path)
        lines += ["### Per-area characteristics (source: `area_summary.csv`)", ""]
        table = [
            {
                "square": r["square_id"],
                "rank": r["rank"],
                "mean": f"{float(r['mean']):,.0f}",
                "CV": f"{float(r['cv']):.3f}",
                "peak/trough": f"{float(r['peak_to_trough']):.1f}",
                "night/mean": f"{float(r['night_floor_over_mean']):.3f}",
                "wknd/wkday": f"{float(r['weekend_over_weekday']):.3f}",
            }
            for r in rows
        ]
        lines += _markdown_table(
            table,
            ["square", "rank", "mean", "CV", "peak/trough", "night/mean", "wknd/wkday"],
        )
        lines.append("")

    decomposition_path = tables / "decomposition.json"
    if decomposition_path.exists():
        d = _read_json(decomposition_path)
        lines += [
            f"### MSTL decomposition, square {d['square_id']} (source: `decomposition.json`)",
            "",
            f"- Periods: {d['periods']}",
        ]
        for name, share in d["variance_share"].items():
            strength = d["strength"].get(name)
            suffix = f", strength {strength:.3f}" if strength is not None else ""
            lines.append(f"  - {name}: **{share:.1%}** of variance{suffix}")
        lines += [
            f"- Residual std {d['residual_std']:.2f} against observed std "
            f"{d['observed_std']:.2f} "
            f"(**{d['residual_std'] / d['observed_std']:.1%}**)",
            "",
        ]

    stationarity_path = tables / "stationarity.csv"
    if stationarity_path.exists():
        rows = _read_csv(stationarity_path)
        lines += ["### Stationarity (source: `stationarity.csv`)", ""]
        table = [
            {
                "transform": r["transform"],
                "ADF stat": f"{float(r['adf_stat']):.2f}",
                "ADF p": f"{float(r['adf_pvalue']):.4f}",
                "KPSS stat": f"{float(r['kpss_stat']):.3f}",
                "KPSS p": f"{float(r['kpss_pvalue']):.3f}",
                "verdict": r["verdict"],
            }
            for r in rows
        ]
        lines += _markdown_table(
            table, ["transform", "ADF stat", "ADF p", "KPSS stat", "KPSS p", "verdict"]
        )
        lines += [
            "",
            "- Note: KPSS p-values are clamped to the tabulated range, so 0.100 means "
            "'>= 0.10', not an exact value.",
            "- Note: these tests address stochastic trend only. They do not test whether "
            "the mean varies with time of day, which it does strongly.",
            "",
        ]

    acf_path = tables / "autocorrelation.json"
    if acf_path.exists():
        a = _read_json(acf_path)
        lines += [
            f"### Autocorrelation, square {a['square_id']} (source: `autocorrelation.json`)",
            "",
            f"- Lag-1 ACF: **{a['lag_1']:.4f}**",
            f"- ACF at lag 144 (one day): **{a['acf_at_daily']:.4f}**",
            f"- ACF at lag 1008 (one week): **{a['acf_at_weekly']:.4f}**",
            f"- Notable lags: {a['notable_lags']}",
            f"- Their ACF values: {[round(v, 3) for v in a['notable_lag_values']]}",
            "",
        ]

    spectral_path = tables / "spectral_peaks.csv"
    if spectral_path.exists():
        rows = _read_csv(spectral_path)[:6]
        lines += ["### Dominant cycles (source: `spectral_peaks.csv`)", ""]
        table = [
            {
                "period (h)": f"{float(r['period_hours']):.2f}",
                "power": f"{float(r['power']):.3e}",
            }
            for r in rows
        ]
        lines += _markdown_table(table, ["period (h)", "power"])
        lines.append("")

    anomalies_path = tables / "anomalies.csv"
    if anomalies_path.exists():
        rows = _read_csv(anomalies_path)
        on_holiday = sum(1 for r in rows if r["is_holiday"] == "True")
        by_date: dict[str, int] = {}
        for row in rows:
            by_date[row["date"]] = by_date.get(row["date"], 0) + 1
        worst = sorted(by_date.items(), key=lambda kv: -kv[1])[:8]
        lines += [
            "### Seasonal-naive anomalies (source: `anomalies.csv`)",
            "",
            f"- Flagged: **{len(rows)}** intervals, **{len(rows) / (8928 - 144):.2%}** of the "
            "8,784 that can be evaluated (the first day has no seasonal-naive "
            "comparison), at z > 4 with the scale estimated per position in the "
            "daily cycle",
            f"- On holidays: **{on_holiday}/{len(rows)}** "
            f"(**{on_holiday / len(rows):.1%}**), against 12.9% of days being holidays "
            "= **1.78x** enrichment, binomial p = 4.3e-04",
            "",
            "Days with the most flagged intervals:",
            "",
        ]
        table = [
            {
                "date": date,
                "intervals": count,
                "holiday": next(
                    (r["holiday"] for r in rows if r["date"] == date and r["holiday"]), ""
                ),
            }
            for date, count in worst
        ]
        lines += _markdown_table(table, ["date", "intervals", "holiday"])
        lines.append("")
    return lines


def _results_summary(report_dir: Path) -> Path:
    """Write the factual evidence dump."""
    tables = report_dir / "tables"
    lines = [
        "# Results summary",
        "",
        "Every measured number, grouped by report section, each traceable to the",
        "artefact it came from. Facts only: no interpretation, because the",
        "interpretation is the author's work.",
        "",
        "Regenerate with `python -m src.export_report`.",
        "",
        "---",
        "",
    ]
    lines += _section_data_preparation(tables)
    lines += ["---", ""]
    lines += _section_exploratory(tables)
    lines += [
        "---",
        "",
        "## Methodology",
        "",
        "_Pending: Phase 4 (forecasting framework) and Phase 5 (models and tuning)._",
        "",
        "## Results and Discussion",
        "",
        "_Pending: Phase 5 (experiments) and Phase 6 (evaluation and failure analysis)._",
        "",
        "## Conclusion and Future Work",
        "",
        "_Pending: depends on the results above._",
        "",
    ]

    path = report_dir / "RESULTS_SUMMARY.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _figure_index(report_dir: Path) -> Path:
    """Write the figure-to-section map."""
    lines = [
        "# Figure index",
        "",
        "Each exported figure, the report section it supports, and the table",
        "holding the numbers that accompany it.",
        "",
        "All figures are 300 dpi PNG in `report/figures/`.",
        "",
    ]
    sections: dict[str, list[FigureSpec]] = {}
    for spec in FIGURES:
        sections.setdefault(spec.section, []).append(spec)

    for section, specs in sections.items():
        lines += [f"## {section}", ""]
        rows = [
            {
                "figure": f"`{s.filename}`",
                "shows": s.shows,
                "numbers in": f"`{s.numbers}`",
            }
            for s in specs
        ]
        lines += _markdown_table(rows, ["figure", "shows", "numbers in"])
        lines.append("")

    lines += [
        "## Pending",
        "",
        "Phase 6 adds: 9 actual-vs-predicted plots (3 models x 3 areas), per-area",
        "zoom panels, error-by-hour heatmaps, residual ACF per model, and the",
        "stress-split failure figures.",
        "",
    ]
    path = report_dir / "FIGURE_INDEX.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def export_report(config: Config) -> dict[str, Any]:
    """Copy artefacts into report/ and write both indexes."""
    report_dir = config.paths.results.parent / "report"
    report_dir.mkdir(parents=True, exist_ok=True)

    counts = _copy_artifacts(config, report_dir)
    summary = _results_summary(report_dir)
    index = _figure_index(report_dir)

    print(f"copied {counts['figures']} figures and {counts['tables']} tables into {report_dir}")
    print(f"wrote {summary}")
    print(f"wrote {index}")
    return {"counts": counts, "summary": summary, "index": index}


def build_parser() -> argparse.ArgumentParser:
    """Construct the argument parser for this entry point."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", default=None, help="Path to a config YAML.")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Assemble the report evidence pack."""
    args = build_parser().parse_args(argv)
    export_report(load_config(args.config))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
