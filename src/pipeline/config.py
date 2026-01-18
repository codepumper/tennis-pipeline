from __future__ import annotations

from pathlib import Path

# SofaScore keys to internal metric suffixes used in the baseline dataset.
SOFASCORE_TO_BASELINE = {
    "aces": "aces",
    "doubleFaults": "doubleFaults",
    "firstServePointsAccuracy": "firstServePointsAccuracy",
    "secondServePointsAccuracy": "secondServePointsAccuracy",
    "breakPointsSaved": "breakPointsSaved",
}

DEFAULT_BASELINE_PATH = Path("data/out.csv")

# P-value thresholds for flagging anomalies.
P_VALUE_THRESHOLDS = {
    "error": 0.01,
    "warning": 0.05,
}
