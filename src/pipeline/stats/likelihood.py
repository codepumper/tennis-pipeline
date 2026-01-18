from __future__ import annotations
import numpy as np
from scipy.stats import gaussian_kde

class LikelihoodEngine:
    def __init__(self, history_data: np.ndarray | list):
        """
        Initialize with historical baseline data (e.g., all aces from 2000-2025).
        """
        # Clean and prepare data
        self.data = np.array(history_data)
        self.data = self.data[~np.isnan(self.data)] # Drop NaNs
        
        # Basic Stats
        self.mean = np.mean(self.data) if len(self.data) > 0 else 0
        self.std = np.std(self.data) if len(self.data) > 0 else 0
        self.max_val = np.max(self.data) if len(self.data) > 0 else 0
        
        # Check if data is integer-based (for bandwidth optimization)
        self.is_integer = np.all(np.mod(self.data, 1) == 0) if len(self.data) > 0 else False
        
        # Cache the KDE generator
        self._kde_func = None

    def _get_kde(self):
        """Lazy-loads the KDE function with boundary correction."""
        if self._kde_func is not None:
            return self._kde_func

        if len(self.data) < 2 or self.std == 0:
            return None

        # Bandwidth selection: Tighter (0.2) for integers (like Aces), normal for floats
        bw = 0.2 if self.is_integer else None
        
        try:
            kernel = gaussian_kde(self.data, bw_method=bw)
            
            # Boundary Correction (Reflection Method) for x >= 0
            # This ensures the curve doesn't dive at 0 for things like Double Faults
            kernel_reflected = gaussian_kde(-self.data, bw_method=bw)
            
            def combined_pdf(x):
                return kernel(x) + kernel_reflected(x)
            
            self._kde_func = combined_pdf
            return self._kde_func
        except Exception:
            return None

    def get_curve_points(self, num_points=500) -> tuple[np.ndarray, np.ndarray]:
        """Returns (x, y) arrays for plotting the yellow curve."""
        if len(self.data) == 0:
            return np.array([]), np.array([])
            
        limit = self.max_val * 1.05
        x_grid = np.linspace(0, limit, num_points)
        
        kde = self._get_kde()
        if kde:
            y_vals = kde(x_grid)
            return x_grid, y_vals
        else:
            return np.array([]), np.array([])