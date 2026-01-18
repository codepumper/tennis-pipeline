"""Prefect task for retrieving simplified SofaScore statistics."""

from __future__ import annotations

import random
import time
from typing import Any

from curl_cffi import requests
from prefect import get_run_logger, task
from prefect.concurrency.sync import rate_limit
from prefect.cache_policies import NO_CACHE

from ..config import SOFASCORE_TO_BASELINE


@task(
    name="fetch_match_metrics",
    retries=3,
    retry_delay_seconds=15,
    cache_policy=NO_CACHE,
)
def get_match_stats(session: requests.Session, match_id: str) -> dict[str, float]:
    """Fetch SofaScore statistics and return winner/loser metrics we track."""

    logger = get_run_logger()
    url = f"https://api.sofascore.com/api/v1/event/{match_id}/statistics"

    rate_limit("sofascore-api")

    headers = {
        "Referer": f"https://www.sofascore.com/event/{match_id}",
        "Accept": "application/json, text/plain, */*",
        "Connection": "keep-alive",
    }

    time.sleep(random.uniform(5.0, 9.0))

    try:
        response = session.get(url, headers=headers, timeout=30)
        if response.status_code == 403:
            logger.critical("403 Forbidden when fetching %s", match_id)
            response.raise_for_status()

        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        logger.error("Failed to fetch stats for %s: %s", match_id, exc)
        raise

    return _extract_metrics(payload)


def _extract_metrics(data: dict[str, Any]) -> dict[str, float]:
    try:
        stats_all = data["statistics"][0]
    except (KeyError, IndexError, TypeError):
        return {}

    stat_lookup = {
        item["key"]: item
        for group in stats_all.get("groups", [])
        for item in group.get("statisticsItems", [])
    }

    games_item = stat_lookup.get("gamesWon")
    home_games = _as_float(games_item.get("homeValue")) if games_item else 0.0
    away_games = _as_float(games_item.get("awayValue")) if games_item else 0.0
    winner_prefix, loser_prefix = (
        ("home", "away") if home_games >= away_games else ("away", "home")
    )

    metrics: dict[str, float] = {}
    for sofa_key, baseline_suffix in SOFASCORE_TO_BASELINE.items():
        if sofa_key not in stat_lookup:
            continue

        item = stat_lookup[sofa_key]
        winner_value = _as_float(item.get(f"{winner_prefix}Value"))
        loser_value = _as_float(item.get(f"{loser_prefix}Value"))

        metrics[f"w_{baseline_suffix}"] = winner_value
        metrics[f"l_{baseline_suffix}"] = loser_value

    return metrics


def _as_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")