"""Module for the Historical Baseline tab with stabilized Yearly-scaled axes."""

from __future__ import annotations
import pandas as pd
import streamlit as st
import plotly.express as px
import numpy as np
from datetime import datetime

BASELINE_PATH = "data/baseline.csv"

@st.cache_data(show_spinner="Loading Historical Data...")
def _load_baseline() -> pd.DataFrame:
    df = pd.read_csv(BASELINE_PATH)
    df['tourney_date'] = pd.to_datetime(df['tourney_date'], format='%Y%m%d')
    return df

def render_baseline_explorer() -> None:
    st.subheader("📈 Historical Baseline Explorer")
    
    try:
        base_df = _load_baseline()
    except FileNotFoundError:
        st.error(f"Baseline file not found at {BASELINE_PATH}")
        return

    # --- Header Controls ---
    numeric_cols = base_df.select_dtypes(include=['number']).columns.tolist()
    target_stat = st.selectbox(
        "Select Statistic", 
        options=numeric_cols, 
        index=numeric_cols.index("w_ace") if "w_ace" in numeric_cols else 0
    )

    # --- DYNAMIC STABILIZATION LOGIC (Per Statistic) ---
    stat_series = base_df[target_stat].dropna()
    global_min, global_max = float(stat_series.min()), float(stat_series.max())
    x_buffer = (global_max - global_min) * 0.05
    fixed_x_range = [global_min - x_buffer, global_max + x_buffer]

    # Calculate Y-axis limit based on the "Yearly Peak"
    # This prevents the "600" issue by scaling for a single year's volume
    bins = 50
    peak_bin_count = 0
    years = base_df['tourney_date'].dt.year.unique()
    
    for yr in years:
        yearly_data = base_df[base_df['tourney_date'].dt.year == yr][target_stat].dropna()
        if not yearly_data.empty:
            # We use the fixed global range so bin sizes stay consistent
            counts, _ = np.histogram(yearly_data, bins=bins, range=(global_min, global_max))
            peak_bin_count = max(peak_bin_count, counts.max())
    
    # We set the limit to the height of the most "active" year in history
    # For a 5-year window, we'll allow it to be 5x that height, or fixed to a comfortable max
    fixed_y_limit = peak_bin_count * 5.5 # Scaled for a 5-year window density
    fixed_y_range = [0, fixed_y_limit]

    # --- Mode Selection ---
    filter_mode = st.radio("Filter Mode", ["Custom Date Range", "5-Year Rolling Window"], horizontal=True)

    # --- Slider Logic ---
    if filter_mode == "Custom Date Range":
        min_date, max_date = base_df['tourney_date'].min().to_pydatetime(), base_df['tourney_date'].max().to_pydatetime()
        start_date, end_date = st.slider("Select Range", min_date, max_date, (min_date, max_date), format="YYYY-MM")
    else:
        # Rolling Window Mode
        all_years = sorted(years)
        selected_end_year = st.select_slider("Select End Year", options=all_years, value=max(all_years))
        # Logic: First year of the 5-year window
        start_date = datetime(selected_end_year - 4, 1, 1)
        end_date = datetime(selected_end_year, 12, 31)
        st.info(f"📅 Subset Period: **{start_date.year}** to **{end_date.year}**")

    # --- Filtering ---
    filtered_df = base_df[
        (base_df['tourney_date'] >= pd.Timestamp(start_date)) & 
        (base_df['tourney_date'] <= pd.Timestamp(end_date))
    ]

    # --- Visualization ---
    if filtered_df.empty:
        st.warning("No matches found for this selection.")
    else:
        st.markdown(f"### Distribution: `{target_stat}`")
        
        fig = px.histogram(
            filtered_df, 
            x=target_stat, 
            nbins=bins, 
            range_x=fixed_x_range,  # Stable horizontal
            range_y=fixed_y_range,  # Stable vertical (scaled for window)
            title=f"Baseline: {target_stat} ({start_date.year}-{end_date.year})",
            color_discrete_sequence=['#00CC96'],
            marginal="box",
            template="plotly_dark"
        )
        
        # Yellow Line: Mean of selection
        curr_mean = filtered_df[target_stat].mean()
        fig.add_vline(x=curr_mean, line_dash="dash", line_color="yellow", annotation_text=f"Mean: {curr_mean:.2f}")

        # Red Line: Absolute record for THIS stat
        fig.add_vline(x=global_max, line_dash="solid", line_color="red", annotation_text=f"Global Max: {global_max}")

        st.plotly_chart(fig, width="stretch")

        m1, m2, m3 = st.columns(3)
        m1.metric("Matches", f"{len(filtered_df):,}")
        m2.metric("Mean", f"{curr_mean:.2f}")
        m3.metric("Record", f"{global_max}")