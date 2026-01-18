import numpy as np
import pandas as pd
from scipy.stats import gaussian_kde

def get_kde_metadata(value: float, baseline_data: pd.Series):
    """
    Calculates anomaly status using Bounded Kernel Density Estimation.
    Uses 'Reflection' to correct for the 0-boundary (e.g., for Aces).
    """
    if value is None or np.isnan(value) or baseline_data.empty:
        return {"density": None, "threshold": None, "status": "NOT_EVALUATED"}

    # 1. Boundary Correction (Reflection at 0)
    # We mirror the positive data across the y-axis to fix the 0-leakage
    data = baseline_data.dropna().values
    reflected_data = np.concatenate([data, -data])
    
    # 2. Fit the KDE
    # gaussian_kde handles bandwidth automatically via Silverman's Rule
    kde = gaussian_kde(reflected_data)
    
    # 3. Calculate Density (Corrected)
    # Since we mirrored the data, we must multiply the density by 2 
    # to maintain an integral of 1 in the positive domain.
    point_density = kde.evaluate([value])[0] * 2
    
    # 4. Determine Dynamic Thresholds (Percentile-based)
    # We check how likely the known historical values are
    baseline_densities = kde.evaluate(data) * 2
    
    # Thresholds: Bottom 0.5% for Outliers, Bottom 5% for Warnings
    critical_thresh = np.percentile(baseline_densities, 0.5)
    warning_thresh = np.percentile(baseline_densities, 5.0)
    
    # 5. Determine Status
    status = "CLEAN"
    if point_density < critical_thresh:
        status = "OUTLIER"
    elif point_density < warning_thresh:
        status = "WARNING"
        
    return {
        "density": round(float(point_density), 5),
        "threshold": round(float(critical_thresh), 5),
        "status": status,
        "method": "KDE-Reflective"
    }