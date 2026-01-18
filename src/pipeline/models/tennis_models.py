from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class Decision(str, Enum):
    CLEAN = "CLEAN"
    WARNING = "WARNING"
    ERROR = "ERROR"
    NOT_EVALUATED = "NOT_EVALUATED"


@dataclass(slots=True)
class MetricEvaluation:
    value: float | None
    p_value: float | None
    status: Decision


def aggregate_status(statuses: Iterable[Decision]) -> Decision:
    statuses = list(statuses)
    if not statuses:
        return Decision.NOT_EVALUATED
    if any(status == Decision.ERROR for status in statuses):
        return Decision.ERROR
    if any(status == Decision.WARNING for status in statuses):
        return Decision.WARNING
    if any(status == Decision.CLEAN for status in statuses):
        return Decision.CLEAN
    return Decision.NOT_EVALUATED