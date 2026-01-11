from enum import Enum
from typing import Dict, Optional
from pydantic import BaseModel, Field, model_validator

class Plausibility(str, Enum):
    CLEAN = "CLEAN"
    WARNING = "WARNING"
    OUTLIER = "OUTLIER"

class TennisMatch(BaseModel):
    match_id: str
    player_name: str
    ace_count: int
    df_count: int
    first_serve_in_pct: float = Field(..., alias="1st_in_pct")
    
    # Augmented Fields
    z_score: Optional[float] = None
    plausibility_flag: Plausibility = Plausibility.CLEAN

    @model_validator(mode='before')
    @classmethod
    def calculate_probabilistic_deviation(cls, data: Dict) -> Dict:
        # Context passed from the task
        mu = data.get("hist_mu", 0.60)
        sigma = data.get("hist_sigma", 0.08)
        val = data.get("1st_in_pct") or data.get("first_serve_in_pct")

        if val is not None:
            z = (val - mu) / sigma
            data["z_score"] = round(z, 3)
            
            abs_z = abs(z)
            if abs_z > 3.0:
                data["plausibility_flag"] = Plausibility.OUTLIER
            elif abs_z > 1.5:
                data["plausibility_flag"] = Plausibility.WARNING
            else:
                data["plausibility_flag"] = Plausibility.CLEAN
        
        return data