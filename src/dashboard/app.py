"""Streamlit app visualising AO integrity reports."""
from __future__ import annotations
from pathlib import Path
import pandas as pd
import streamlit as st

from src.dashboard.tabs.historical_baseline import render_baseline_explorer
from src.dashboard.tabs.baseline import render_baseline

@st.cache_data(show_spinner="Running AO Integrity Audit...")
def _load_dataframe(path: str | Path | None) -> pd.DataFrame:
    """
    Loads the report and intelligently finds the header row if it's displaced.
    """
    path_str = str(path)
    
    try:
        # 1. Initial Load attempt
        if path_str.endswith(".csv"):
             df = pd.read_csv(path_str)
        else:
             df = pd.read_excel(path_str)
        
        # 2. Header Validation Logic
        # If 'match_id' is not in the columns, we likely loaded the header as data.
        if "match_id" not in df.columns:
            # Look for the row that contains "match_id"
            # We search the first 5 rows to be safe
            for i, row in df.head(5).iterrows():
                # Check if any value in this row matches our expected primary key
                if row.astype(str).str.contains("match_id", case=False).any():
                    # Set this row as the header
                    df.columns = row
                    # Drop this row and all rows above it
                    df = df.iloc[i+1:].reset_index(drop=True)
                    break
        
        # 3. Cleanup: Ensure columns are strings and stripped of whitespace
        df.columns = df.columns.astype(str).str.strip()
        
        # 4. Final Safety Check
        if "match_id" not in df.columns:
            st.error(f"❌ Could not find 'match_id' header in {path}. Please check the file format.")
            return pd.DataFrame()

        return df

    except Exception as e:
        st.error(f"Error loading file: {e}")
        return pd.DataFrame()

def _get_status_color(status: str) -> str:
    """
    Maps status labels to background colors.
    """
    # Normalize status to handle potential casing issues
    s = str(status).upper().strip()
    
    colors = {
        "CLEAN": "transparent",
        "WARNING": "rgba(255, 165, 0, 0.3)",      # Alert Orange
        "ERROR": "rgba(255, 0, 0, 0.4)",        # Alert Red
        "CRITICAL": "rgba(139, 0, 0, 0.6)",       # Deep Dark Red
        "NOT_EVALUATED": "rgba(128, 128, 128, 0.1)" 
    }
    return f"background-color: {colors.get(s, 'transparent')}"

def page_integrity_audit():
    st.title("Integrity Audit")
    
    # Access session path or default
    report_path = st.session_state.get("report_path", "AO_2026.xlsx")
    
    df = _load_dataframe(report_path)
    
    if df.empty:
        st.info(f"⏳ Awaiting Pipeline Report ({report_path})...")
        return
    
    # 1. Identify "Value" columns (Exclude metadata, p-values, and status columns)
    all_cols = df.columns.tolist()
    
    # We only want to display the actual stats (e.g. 'w_aces'), not the helper columns
    display_cols = [
        c for c in all_cols 
        if not c.endswith(("_p_value", "_status", "_prob")) 
        and c not in ["match_id", "overall_status", "integrity_flags", "integrity_summary"]
    ]
    
    # 2. Styling Logic: Look at neighbor columns for color
    def _apply_integrity_style(row):
        styles = []
        for col in row.index:
            # If this is a display column (e.g., 'w_aces')
            if col in display_cols:
                # Look for its status sibling (e.g., 'w_aces_status')
                status_col = f"{col}_status"
                if status_col in all_cols:
                    styles.append(_get_status_color(row[status_col]))
                else:
                    styles.append("") # No status found, clear
            else:
                styles.append("") # Not a display column, clear
        return styles

    # 3. Apply Style & Render
    # We strip the index to make it look like a clean dashboard table
    try:
        styled_df = df.style.apply(_apply_integrity_style, axis=1)
        
        # Format numbers to 1 decimal place for cleaner reading
        styled_df = styled_df.format(precision=1, na_rep="-")
        
        st.dataframe(
            styled_df, 
            column_order=["match_id"] + display_cols, # Put ID first, then stats
            use_container_width=True, 
            hide_index=True,
            height=600
        )
    except Exception as e:
        st.error(f"Visualization Error: {e}")
    
    # Legend
    st.markdown("""
    <div style="font-size: 0.85rem; color: #666; margin-top: 10px; padding: 10px; background-color: #f0f2f6; border-radius: 5px;">
        <strong>Integrity Legend:</strong> 
        <span style="color: #FFA500; font-weight:bold;">🟧 Warning (Z > 3.0)</span> | 
        <span style="color: #FF0000; font-weight:bold;">🟥 Critical (Record / Z > 4.0)</span>
    </div>
    """, unsafe_allow_html=True)

def page_historical():
    st.title("Historical Baseline")
    render_baseline_explorer()

def page_final():
    st.title("Final Baseline Explorer")
    render_baseline()

def main():
    st.set_page_config(page_title="AO Truth Engine", layout="wide", page_icon="🎾")

    pg = st.navigation([
        st.Page(page_integrity_audit, title="Integrity Audit"),
        st.Page(page_historical, title="Historical Viewer"),
        st.Page(page_final, title="Baseline"),
    ])
    
    pg.run()

if __name__ == "__main__":
    main()