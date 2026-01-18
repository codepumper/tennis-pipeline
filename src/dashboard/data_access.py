"""Data loaders for Streamlit dashboards."""

from __future__ import annotations

from pathlib import Path
from typing import Final

import pandas as pd

_DEFAULT_REPORT_PATH: Final[Path] = Path("AO_2026.xlsx")


def load_report(report_path: str | Path | None = None) -> pd.DataFrame:
    """Return the integrity report as a DataFrame."""

    resolved_path = Path(report_path) if report_path else _DEFAULT_REPORT_PATH
    if not resolved_path.exists():
        raise FileNotFoundError(f"Report not found: {resolved_path}")

    return pd.read_excel(resolved_path)
