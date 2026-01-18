import pandas as pd
import random
import time
from typing import Dict, Any
from curl_cffi import requests
from prefect import flow, task, get_run_logger

# Internal Imports
from src.pipeline.models.tennis_models import AOIntegrityRecord
from src.pipeline.stats.calculators import calculate_historical_baseline
from src.pipeline.tasks.match_id import get_match_ids
from src.pipeline.tasks.match_stats import get_match_stats

# --- 1. Mapping Configuration ---
# Maps SofaScore descriptive keys to your Baseline CSV keys
STAT_CONFIG = {
    "aces": "ace",
    "doubleFaults": "df",
    "firstServeAccuracy": "1stIn",
    "firstServePointsAccuracy": "1stWon",
    "secondServePointsAccuracy": "2ndWon",
    "breakPointsSaved": "bpSaved",
    "serviceGamesTotal": "SvGms"
}

# --- 2. Logic Functions ---



@task(name="Enrich Match Data")
def enrich_match_data(match_id: str, extracted_stats: dict, baseline: dict) -> Dict[str, Any]:
    """Applies historical baseline to SofaScore stats and pivots to an Excel row."""
    row = {"match_id": match_id}
    anomalies = []

    for sofa_key, value in extracted_stats.items():
        # 1. Resolve which baseline key to use
        # Strip w_ or l_ and look up the mapping in STAT_CONFIG
        clean_sofa_name = sofa_key.replace("w_", "").replace("l_", "").replace("_total", "")
        baseline_key = STAT_CONFIG.get(clean_sofa_name)
        
        stat_baseline = baseline.get(baseline_key, {})

        # 2. Pydantic Validation & Z-Score Calculation
        record = AOIntegrityRecord(
            match_id=match_id,
            stat=sofa_key,
            value=float(value),
            historical_mu=stat_baseline.get("mean"),
            historical_sigma=stat_baseline.get("std")
        )

        # 3. Build Row
        row.update({
            sofa_key: record.value,
            f"{sofa_key}_zscore": round(record.z_score, 2) if record.z_score else None,
            f"{sofa_key}_status": record.status.value
        })

        if record.z_score and abs(record.z_score) > 3.5:
            anomalies.append(f"EXTREME_{sofa_key}")

    row["integrity_flags"] = ", ".join(anomalies) if anomalies else "CLEAN"
    return row

# --- 3. Orchestration Flow ---

@flow(name="AO-2026-Truth-Engine")
def run_pipeline():
    logger = get_run_logger()
    
    # Setup resources
    match_ids = get_match_ids()[:2] # Filters for AO 2026 Men's Singles
    baseline = calculate_historical_baseline("data/historical/sackmann_atp.csv")
    final_output = []

    # Use a persistent session to keep the connection 'warm' (Human-Realistic)
    with requests.Session(impersonate="chrome120") as session:
        for m_id in match_ids:
            try:
                # Step 1: get_stats
                stats = get_match_stats(session, m_id)
                
                # Step 3: Enrich (Prefect Task)
                if stats:
                    row = enrich_match_data(m_id, stats, baseline)
                    final_output.append(row)
                
                # Random Jitter between matches
                time.sleep(random.uniform(4, 9))
                
            except Exception as e:
                logger.error(f"Skipping match {m_id} due to error: {e}")
                continue

    # Final Export
    if final_output:
        df = pd.DataFrame(final_output)
        # Reorder: Metadata first, then alphabetical stats
        cols = ["match_id", "integrity_flags"] + sorted([c for c in df.columns if c not in ["match_id", "integrity_flags"]])
        df[cols].to_excel("AO_2026_Truth_Report.xlsx", index=False)
        logger.info(f"Report Generated: {len(final_output)} matches processed.")

if __name__ == "__main__":
    run_pipeline()