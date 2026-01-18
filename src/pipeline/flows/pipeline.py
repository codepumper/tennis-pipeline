"""Prefect flow orchestrating the SofaScore ingestion and KDE evaluation."""

from __future__ import annotations

import datetime as _dt
from pathlib import Path
from typing import Iterable

import pandas as pd
from curl_cffi import requests
from prefect import flow, get_run_logger

from ..config import DEFAULT_BASELINE_PATH, SOFASCORE_TO_BASELINE
from ..models.tennis_models import Decision, aggregate_status
from ..stats.calculators import KDEModel, build_kde_models, evaluate_metric
from ..tasks.match_id import get_match_ids
from ..tasks.match_stats import get_match_stats


def _tracked_columns() -> list[str]:
    suffixes = set(SOFASCORE_TO_BASELINE.values())
    return [f"{prefix}_{suffix}" for suffix in sorted(suffixes) for prefix in ("w", "l")]


def _evaluate_match(
    match_id: str,
    metrics: dict[str, float],
    tracked_columns: Iterable[str],
    models: dict[str, KDEModel],
) -> dict[str, object]:
    row: dict[str, object] = {"match_id": match_id}
    statuses: list[Decision] = []

    for column in tracked_columns:
        value = metrics.get(column)
        evaluation = evaluate_metric(column, value, models)
        row[column] = evaluation.value
        row[f"{column}_p_value"] = evaluation.p_value
        row[f"{column}_status"] = evaluation.status.value
        statuses.append(evaluation.status)

    row["overall_status"] = aggregate_status(statuses).value
    return row


@flow(name="AO-2026-Truth-Engine")
def run_pipeline(
    date: str | None = None,
    baseline_path: str | Path = DEFAULT_BASELINE_PATH,
    report_path: str | Path = "AO_2026.xlsx",
) -> None:
    logger = get_run_logger()

    columns = _tracked_columns()
    models = build_kde_models(baseline_path, columns)
    if not models:
        logger.warning("No KDE models built; results will be marked NOT_EVALUATED")

    resolved_date = None
    if isinstance(date, str) and date:
        resolved_date = _dt.date.fromisoformat(date)
    else:
        resolved_date = date

    match_ids_future = get_match_ids.submit(date=resolved_date)
    match_ids = match_ids_future.result()
    if not match_ids:
        logger.info("No matches to process")
        return

    results: list[dict[str, object]] = []
    with requests.Session(impersonate="chrome120") as session:
        for match_id in match_ids:
            try:
                metrics = get_match_stats.fn(session, match_id)
            except Exception as exc:  # pragma: no cover - Prefect handles logging
                logger.warning("Skipping match %s due to fetch error: %s", match_id, exc)
                continue

            results.append(_evaluate_match(match_id, metrics, columns, models))

    if results:
        df = pd.DataFrame(results)
        df.to_excel(report_path, index=False)
        logger.info("Report written to %s", report_path)
    else:
        logger.info("No results generated; skipping report write")


if __name__ == "__main__":
    run_pipeline()