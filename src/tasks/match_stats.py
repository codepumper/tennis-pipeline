import random
import time
from curl_cffi import requests
from prefect import task, get_run_logger
from prefect.concurrency.sync import rate_limit
from prefect.cache_policies import NO_CACHE

@task(name="fetch_sofascore_stats", retries=3, retry_delay_seconds=15, cache_policy=NO_CACHE)
def get_match_stats(session: requests.Session, match_id: str) -> dict:
    """
    Fetches raw statistics for a specific match from SofaScore.
    
    Args:
        session: The persistent curl_cffi session with TLS impersonation.
        match_id: The SofaScore match ID.
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
    time.sleep(random.uniform(4.0, 8.0))
    
    try:
        resp = session.get(url, headers=headers, timeout=30)
        
        if resp.status_code == 403:
            logger.critical(f"🛑 403 Forbidden on {match_id}. IP might be flagged.")
            resp.raise_for_status() # Trigger Prefect retry logic
            
        resp.raise_for_status()
        return resp.json()

    except Exception as exc:
        logger.error(f"Failed to fetch stats for {match_id}: {exc}")
        raise