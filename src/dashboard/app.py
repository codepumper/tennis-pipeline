"""Streamlit app visualising AO integrity reports."""

from __future__ import annotations
from pathlib import Path
import pandas as pd
import streamlit as st

from src.dashboard.data_access import load_report
from src.dashboard.tabs.baseline import render_baseline_explorer # New Import

@st.cache_data(show_spinner="Running Integrity Audit...")
def _load_dataframe(path: str | Path | None) -> pd.DataFrame:
    return load_report(path)

def _get_status_color(status: str) -> str:
    colors = {
        "CLEAN": "transparent",
        "WARNING": "rgba(255, 165, 0, 0.3)",
        "OUTLIER": "rgba(255, 69, 0, 0.4)",
        "CRITICAL_ERROR": "rgba(255, 0, 0, 0.6)",
        "NOT_EVALUATED": "rgba(128, 128, 128, 0.1)" 
    }
    return f"background-color: {colors.get(status, 'transparent')}"

def _render_integrity_tab(df: pd.DataFrame) -> None:
    st.subheader("🛡️ Integrity Heatmap")
    all_cols = df.columns.tolist()
    display_cols = [c for c in all_cols if not (c.endswith("_zscore") or c.endswith("_status") or c == "integrity_flags")]
    
    def _apply_integrity_style(row):
        styles = []
        for col in row.index:
            if col in display_cols:
                status_col = f"{col}_status"
                if status_col in all_cols:
                    styles.append(_get_status_color(row[status_col]))
                else:
                    styles.append("")
            else:
                styles.append("")
        return styles

    styled_df = df.style.apply(_apply_integrity_style, axis=1)
    st.dataframe(styled_df, column_order=display_cols, width="stretch", hide_index=True)
    st.caption("Legend: 🟧 Warning | 🟥 Outlier/Critical (Z-Score > 3.0)")

def main() -> None:
    st.set_page_config(page_title="AO Truth Engine", layout="wide", page_icon="🎾")
    st.title("🎾 AO Truth Engine Dashboard")

    report_path = st.sidebar.text_input("Report Source", value="AO_2026.xlsx")
    st.sidebar.divider()

    # --- Tab Logic ---
    tab_audit, tab_baseline = st.tabs(["🔍 Integrity Audit", "📊 Historical Baseline"])

    with tab_audit:
        try:
            df = _load_dataframe(report_path or None)
            _render_integrity_tab(df)
        except FileNotFoundError:
            st.info("Awaiting pipeline generation...")
        except Exception as exc:
            st.error(f"Logic Error: {exc}")

    with tab_baseline:
        render_baseline_explorer() # Function call from the new file

if __name__ == "__main__":
    main()