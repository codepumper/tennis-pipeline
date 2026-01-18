import pandas as pd
import numpy as np

def calculate_historical_baseline(file_path: str):
    """
    Computes μ and σ for AO-relevant stats from Sackmann CSVs.
    Filters for Grand Slam Hard Court matches (2021-2025).
    """
    try:
        # In production: df = pd.read_csv(file_path)
        # filtered = df[(df['tourney_level'] == 'G') & (df['surface'] == 'Hard')]
        
        # Placeholder baseline for 1st Serve %, Aces, and BP Saved
        return {
            "first_serve_pct": {"mean": 0.62, "std": 0.07},
            "aces_per_player": {"mean": 12.5, "std": 6.2},
            "first_serve_points_won_pct": {"mean": 0.72, "std": 0.08},
            "double_faults_per_player": {"mean": 3.8, "std": 2.1}
        }
    except Exception:
        return {}

def get_z_score_metadata(metric: str, value: float, thresholds: dict):
    stats = thresholds.get(metric)
    if not stats or value is None or np.isnan(value):
        return {"mu": None, "sigma": None, "z": None, "status": "NOT_EVALUATED"}

    mu, sigma = stats["mean"], stats["std"]
    z = (value - mu) / sigma
    
    status = "CLEAN"
    if abs(z) > 3.0: status = "OUTLIER"
    elif abs(z) > 1.5: status = "WARNING"
    
    return {"mu": mu, "sigma": sigma, "z": round(z, 3), "status": status}