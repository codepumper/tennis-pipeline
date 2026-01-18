import pandas as pd
from curl_cffi import requests
from prefect import flow, task, get_run_logger

from src.models.tennis_models import AOIntegrityRecord
from src.stats.calculators import calculate_historical_baseline
from src.tasks.match_id import get_match_ids
from src.tasks.match_stats import get_match_stats

# --- Extraction Logic ---

def extract_stats(data: dict) -> dict:
    """Extracts raw JSON into a winner/loser mapped dictionary."""
    try:
        stats_all = data["statistics"][0]
    except (KeyError, IndexError):
        return {}

    # 1. Determine Winner (w_) and Loser (l_) based on gamesWon
    stats_lookup = {
        item["key"]: (item["homeValue"], item["awayValue"])
        for group in stats_all["groups"]
        for item in group["statisticsItems"]
    }

    home_games, away_games = stats_lookup.get("gamesWon", (0, 0))
    is_home_winner = home_games > away_games
    w, l = ("home", "away") if is_home_winner else ("away", "home")

    # 2. Map Statistics (Dictionary-based for simplicity)
    # Key: SofaScore key | Value: Our internal suffix
    stat_map = {
        "aces": "ace",
        "doubleFaults": "df",
        "firstServeAccuracy": "1stIn",
        "firstServePointsAccuracy": "1stWon",
        "secondServePointsAccuracy": "2ndWon",
        "breakPointsSaved": "bpSaved",
        "serviceGamesTotal": "SvGms"
    }

    extracted = {}
    for group in stats_all["groups"]:
        for item in group["statisticsItems"]:
            key = item["key"]
            if key in stat_map:
                clean_key = stat_map[key]
                extracted[f"w_{clean_key}"] = item[f"{w}Value"]
                extracted[f"l_{clean_key}"] = item[f"{l}Value"]
                
                # Handle cases with 'Total' fields (like serve points or break points)
                if "Total" in item:
                    extracted[f"w_{clean_key}tot"] = item[f"{w}Total"]
                    extracted[f"l_{clean_key}tot"] = item[f"{l}Total"]

    return extracted

@task
def enrich_and_pivot_match(extracted_stats: dict, match_id: str, baseline: dict):
    # This dictionary will become our single Excel row
    match_row = {
        "match_id": match_id,
    }
    
    anomalies = []

    for key, value in extracted_stats.items():
        is_winner_stat = key.startswith("w_")
        # Strip 'w_' or 'l_' to find the baseline key (e.g., 'aces')
        base_stat = key[2:] if len(key) > 2 else key
        stat_baseline = baseline.get(base_stat, {})

        # 1. Validate via Pydantic
        record = AOIntegrityRecord(
            match_id=match_id,
            # match_time_utc=match_metadata["match_time"],
            # player=match_metadata["winner_name"] if is_winner_stat else match_metadata["loser_name"],
            # opponent=match_metadata["loser_name"] if is_winner_stat else match_metadata["winner_name"],
            stat=key,
            value=float(value),
            historical_mu=stat_baseline.get("mean"),
            historical_sigma=stat_baseline.get("std")
        )

        # 2. Add the value and its Z-score/Status to the row
        match_row[key] = record.value
        match_row[f"{key}_zscore"] = round(record.z_score, 2) if record.z_score else None
        match_row[f"{key}_status"] = record.status.value


    # 3. Add a summary of any flags found in this match
    match_row["integrity_flags"] = ", ".join(anomalies) if anomalies else "CLEAN"
    
    return match_row

@flow(name="AO-2026-Truth-Engine")
def run_pipeline():
    logger = get_run_logger()
    
    # Setup
    match_ids = get_match_ids()[:2]
    baseline = calculate_historical_baseline("data/historical/sackmann_atp.csv")
    final_rows = []

    # Initialize the Human-Realistic Session
    with requests.Session(impersonate="chrome120") as session:
        for m_id in match_ids:
            try:
                # 1. Fetch (The new task)
                raw_data = get_match_stats(session, m_id)
                
                # 2. Extract & Map
                extracted = extract_stats(raw_data)
                
                # 3. Enrich & Pivot
                if extracted:
                    row = enrich_and_pivot_match(extracted, m_id, baseline)
                    final_rows.append(row)
                
            except Exception as e:
                logger.warning(f"Skipping match {m_id} due to persistent error.")
                continue

    if final_rows:
        pd.DataFrame(final_rows).to_excel("AO_2026_Report.xlsx", index=False)

if __name__ == "__main__":
    run_pipeline()