from __future__ import annotations
from enum import Enum
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, model_validator

# --- 1. Configuration & Constants ---

class Plausibility(str, Enum):
    CLEAN = "CLEAN"
    WARNING = "WARNING"
    OUTLIER = "OUTLIER"
    CRITICAL_ERROR = "CRITICAL_ERROR"  # For deterministic failures
    NOT_EVALUATED = "NOT_EVALUATED"

# Sample structure of your historical baseline (normally loaded from JSON)
GS_BASELINE = {
    "w_ace": {"mean": 10.13, "std": 7.01},
    # "double_faults": {"mean": 3.45, "std": 2.10},
    # "first_serve_pct": {"mean": 0.62, "std": 0.07},
    # Add other stats here...
}

class AOIntegrityRecord(BaseModel):
    match_id: str
    # match_time_utc: datetime
    # player: str
    # opponent: str
    stat: str  # e.g., "aces", "duration_min", "first_serve_pct"
    value: float
    
    # Contextual fields for cross-validation
    total_serve_points: Optional[int] = None
    first_serve_in: Optional[int] = None
    match_duration_min: Optional[int] = None
    surface: str = "Outdoor Hard"
    
    # Statistical Metadata
    historical_mu: Optional[float] = None
    historical_sigma: Optional[float] = None
    z_score: Optional[float] = None
    status: Plausibility = Plausibility.NOT_EVALUATED

    @model_validator(mode='after')
    def perform_integrity_audit(self) -> 'AOIntegrityRecord':
        """
        Executes the two-tier validation strategy:
        1. Deterministic (Physical & Logic)
        2. Probabilistic (Statistical Z-Score)
        """
        
        # --- A. DETERMINISTIC CHECKS (Common Sense) ---
        
        # Surface Check
        if self.surface != "Outdoor Hard":
            self.status = Plausibility.CRITICAL_ERROR
            return self

        # Serve Logic: 1st In <= Total Points
        if self.first_serve_in and self.total_serve_points:
            if self.first_serve_in > self.total_serve_points:
                self.status = Plausibility.CRITICAL_ERROR
                return self

        # Duration Check (Grand Slam Best of 5)
        if self.stat == "duration_min":
            if not (45 <= self.value <= 480):
                self.status = Plausibility.CRITICAL_ERROR
                return self

        # Percentage Bound Check
        if "_pct" in self.stat or "accuracy" in self.stat.lower():
            if not (0 <= self.value <= 1.05): # Allowing 5% buffer for rounding
                self.status = Plausibility.CRITICAL_ERROR
                return self

        # --- B. PROBABILISTIC CHECKS (Statistical Logic) ---
        
        # Lookup baseline if not already provided
        baseline = GS_BASELINE.get(self.stat)
        if baseline and self.historical_mu is None:
            self.historical_mu = baseline["mean"]
            self.historical_sigma = baseline["std"]

        # Calculate Z-Score
        if self.historical_mu is not None and self.historical_sigma:
            # Formula: Z = (x - mu) / sigma
            self.z_score = (self.value - self.historical_mu) / self.historical_sigma
            abs_z = abs(self.z_score)

            if abs_z > 3.0:
                self.status = Plausibility.OUTLIER
            elif abs_z > 1.5:
                self.status = Plausibility.WARNING
            else:
                self.status = Plausibility.CLEAN

        return self