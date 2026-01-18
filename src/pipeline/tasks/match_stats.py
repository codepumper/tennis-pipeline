import random
import time
from typing import Dict, Any
from curl_cffi import requests
from prefect import task, get_run_logger
from prefect.concurrency.sync import rate_limit
from prefect.cache_policies import NO_CACHE

# --- Configuration ---
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

@task(
    name="fetch_sofascore_stats", 
    retries=3, 
    retry_delay_seconds=15, 
    cache_policy=NO_CACHE
)
def get_match_stats(session: requests.Session, match_id: str) -> dict:
    """
    Fetches raw statistics for a specific match from SofaScore.
    """
    logger = get_run_logger()
    url = f"https://api.sofascore.com/api/v1/event/{match_id}/statistics"
    
    # 1. Apply Prefect Rate Limit (Ensures Docker-wide safety)
    rate_limit("sofascore-api")
    
    # 2. Human-Realistic Headers
    headers = {
        "Referer": f"https://www.sofascore.com/event/{match_id}",
        "Accept": "application/json, text/plain, */*",
        "Connection": "keep-alive"
    }
    
    # 3. Random Jitter (Human click-speed simulation)
    # Increased slightly to be safer during high-traffic AO rounds
    time.sleep(random.uniform(5.0, 9.0))
    
    try:
        resp = session.get(url, headers=headers, timeout=30)
        
        if resp.status_code == 403:
            logger.critical(f"🛑 403 Forbidden on {match_id}. TLS/IP block likely.")
            resp.raise_for_status() 
            
        resp.raise_for_status()
        raw_json = resp.json()

        # 4. Extract and Map immediately
        return extract_stats(raw_json)

    except Exception as exc:
        logger.error(f"Failed to fetch stats for {match_id}: {exc}")
        raise

def extract_stats(data: dict) -> dict:
    """
    Flatten SofaScore JSON and map home/away values to winner/loser.
    This is a pure function for easier unit testing.
    """
    try:
        # Navigate to the correct statistics object
        # SofaScore usually puts 'ALL' stats at index 0
        stats_all = data["statistics"][0]
    except (KeyError, IndexError, TypeError):
        return {}

    # Flatten nested groups into a single searchable dictionary O(1)
    raw_map = {
        item["key"]: item 
        for group in stats_all["groups"] 
        for item in group["statisticsItems"]
    }

    # Determine Winner/Loser based on 'gamesWon'
    # Default to 0,0 if not found to prevent crashes on abandoned matches
    h_won, a_won = raw_map.get("gamesWon", {}).get("homeValue", 0), raw_map.get("gamesWon", {}).get("awayValue", 0)
    
    # Prefix mapping
    w_prefix, l_prefix = ("home", "away") if h_won > a_won else ("away", "home")

    extracted = {}
    for sofa_key in STAT_CONFIG.keys():
        if item := raw_map.get(sofa_key):
            # Maintain the descriptive SofaScore key names
            extracted[f"w_{sofa_key}"] = item.get(f"{w_prefix}Value")
            extracted[f"l_{sofa_key}"] = item.get(f"{l_prefix}Value")
            
            # Map 'Total' fields for percentage-based analysis (e.g. Serve Accuracy)
            if "Total" in item:
                extracted[f"w_{sofa_key}_total"] = item.get(f"{w_prefix}Total")
                extracted[f"l_{sofa_key}_total"] = item.get(f"{l_prefix}Total")

    return extracted