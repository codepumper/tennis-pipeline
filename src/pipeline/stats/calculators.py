from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from scipy.stats import gaussian_kde

from ..config import P_VALUE_THRESHOLDS
from ..models.tennis_models import Decision, MetricEvaluation


@dataclass(slots=True)
class KDEModel:
    column: str
    grid: np.ndarray
    cdf: np.ndarray

    @classmethod
    def build(cls, column: str, samples: np.ndarray) -> KDEModel:
        samples = samples[np.isfinite(samples)]
        if samples.size == 0:
            raise ValueError(f"No finite samples available for column '{column}'")

        kde = gaussian_kde(samples)

        span = samples.std(ddof=1) if samples.size > 1 else 1.0
        if span <= 0:
            span = 1.0
        padding = span * 3
        lower = float(samples.min() - padding)
        upper = float(samples.max() + padding)

        grid = np.linspace(lower, upper, 1024)
        pdf = kde(grid)
        cdf = np.concatenate((
            [0.0],
            np.cumsum((pdf[1:] + pdf[:-1]) / 2 * np.diff(grid)),
        ))
        cdf /= cdf[-1]

        return cls(column=column, grid=grid, cdf=cdf)

    def cdf_value(self, value: float) -> float:
        return float(np.interp(value, self.grid, self.cdf, left=0.0, right=1.0))

    def p_value(self, value: float) -> float:
        cdf_val = self.cdf_value(value)
        two_tailed = 2 * min(cdf_val, 1 - cdf_val)
        return float(min(max(two_tailed, 0.0), 1.0))


def build_kde_models(
    baseline_path: str | Path,
    columns: Iterable[str],
) -> dict[str, KDEModel]:
    df = pd.read_csv(baseline_path)
    models: dict[str, KDEModel] = {}
    for column in columns:
        if column not in df:
            continue
        samples = df[column].dropna().to_numpy(dtype=float)
        if samples.size < 5:
            continue
        models[column] = KDEModel.build(column, samples)
    return models


def evaluate_metric(
    column: str,
    value: float | None,
    models: dict[str, KDEModel],
) -> MetricEvaluation:
    if value is None or not np.isfinite(value):
        return MetricEvaluation(value=None, p_value=None, status=Decision.NOT_EVALUATED)

    model = models.get(column)
    if model is None:
        return MetricEvaluation(value=value, p_value=None, status=Decision.NOT_EVALUATED)

    p_value = model.p_value(value)
    status = _categorise_p_value(p_value)
    return MetricEvaluation(value=value, p_value=p_value, status=status)


def _categorise_p_value(p_value: float) -> Decision:
    if p_value <= P_VALUE_THRESHOLDS["error"]:
        return Decision.ERROR
    if p_value <= P_VALUE_THRESHOLDS["warning"]:
        return Decision.WARNING
    return Decision.CLEAN