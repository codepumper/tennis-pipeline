import pandas as pd
import numpy as np
import plotly.graph_objects as go

def calculate_historical_baseline(file_path: str):
    """
    In a real scenario, this reads the CSVs:
    df = pd.read_csv(file_path)
    filtered = df[df['tourney_name'] == 'Australian Open']
    """
    # Placeholder for calculated stats from 2021-2025 data
    return {
        "avg_1st_in": 0.62,
        "std_1st_in": 0.07
    }

def analyze_kpi_distribution(df: pd.DataFrame, column_name: str, label: str, show_plot: bool = True):
    """
    Calculates μ, σ, and Z-score thresholds with an interactive Plotly visualization.
    """
    mu = df[column_name].mean()
    sigma = df[column_name].std()
    
    # Thresholds
    upper_3s = mu + (3 * sigma)
    lower_3s = mu - (3 * sigma)
    warning_upper = mu + (1.5 * sigma)

    if show_plot:
        fig = go.Figure()

        # 1. The Distribution (Histogram)
        fig.add_trace(go.Histogram(
            x=df[column_name],
            name=label,
            marker_color='#636EFA',
            opacity=0.7,
            nbinsx=20
        ))

        # 2. Shaded Region: Standard Error / 1-Sigma
        fig.add_vrect(
            x0=mu - sigma, x1=mu + sigma,
            fillcolor="rgba(128, 128, 128, 0.2)", line_width=0,
            layer="below", annotation_text="68% Confidence (1σ)", 
            annotation_position="top left"
        )

        # 3. Reference Lines
        fig.add_vline(x=mu, line_dash="dash", line_color="navy", 
                      annotation_text=f"Mean: {mu:.2f}")
        
        fig.add_vline(x=upper_3s, line_color="red", line_dash="dot", 
                      annotation_text="OUTLIER (3σ)")

        fig.update_layout(
            title=f"2026 AO Analysis: {label} Distribution",
            xaxis_title=label,
            yaxis_title="Frequency",
            template="plotly_white",
            showlegend=False
        )
        fig.show()

    return {
        "mean": mu, 
        "std": sigma, 
        "outlier_limit": upper_3s, 
        "warning_limit": warning_upper
    }