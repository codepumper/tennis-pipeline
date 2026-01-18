"""Module for the Historical Baseline tab with Likelihood Distribution."""
from __future__ import annotations
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from src.pipeline.stats.likelihood import LikelihoodEngine  # <--- IMPORT THE ENGINE

BASELINE_PATH = "data/out.csv"

@st.cache_data(show_spinner="Loading Historical Data...")
def _load_baseline() -> pd.DataFrame:
    try:
        df = pd.read_csv(BASELINE_PATH)
        return df
    except FileNotFoundError:
        return pd.DataFrame()

def render_baseline() -> None:
    
    df = _load_baseline()
    if df.empty:
        st.error("Baseline file missing.")
        return

    # --- Controls ---
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    numeric_cols = [c for c in numeric_cols if not (c.startswith('Unnamed') or 'tourney_date' in c.lower() or 'id' in c.lower())]
    
    target_stat = st.selectbox("Select Statistic", options=numeric_cols, index=1)

    # --- USE THE ENGINE ---
    # 1. Initialize the Brain with column data
    data_series = df[target_stat].dropna()
    engine = LikelihoodEngine(data_series.values)
    
    # 2. Get Plotting Data from Brain
    x_curve, y_curve = engine.get_curve_points()

    # --- Visualization ---
    fig = px.histogram(
        df, x=target_stat,
        histnorm='probability density',
        title=f"Likelihood Distribution: {target_stat}",
        color_discrete_sequence=['#00CC96'],
        template="plotly_dark"
    )

    # Add the Yellow Curve if engine returned data
    if len(x_curve) > 0:
        fig.add_trace(go.Scatter(
            x=x_curve, y=y_curve,
            mode='lines',
            name='Likelihood (KDE)',
            line=dict(color='#FFFF00', width=3)
        ))

    st.plotly_chart(fig, use_container_width=True)
    
    # Interactive "What If" Checker (Bonus)
    st.divider()
    test_val = st.number_input(f"Test a hypothetical {target_stat} value:", value=engine.mean)
    decision = engine.evaluate(test_val)
    
    if decision.status == "CLEAN":
        st.success(f"✅ {decision.message}")
    elif decision.status == "WARNING":
        st.warning(f"⚠️ {decision.message}")
    else:
        st.error(f"🚨 {decision.message}")