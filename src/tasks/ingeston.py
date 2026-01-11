from prefect import task, get_run_logger
import pandas as pd
from src.models.tennis_models import TennisMatch

@task
def scrape_live_2026():
    logger = get_run_logger()
    logger.info("Fetching 2026 AO Live Scores...")
    # Mocked API response
    return [
        {"match_id": "2026-AO-101", "player_name": "Novak Djokovic", "ace_count": 14, "df_count": 1, "1st_in_pct": 0.72},
        {"match_id": "2026-AO-102", "player_name": "Qualifier X", "ace_count": 2, "df_count": 12, "1st_in_pct": 0.38}
    ]

@task
def enrich_data(raw_matches, stats):
    enriched = []
    for m in raw_matches:
        m.update({"hist_mu": stats["avg_1st_in"], "hist_sigma": stats["std_1st_in"]})
        validated = TennisMatch(**m)
        enriched.append(validated.model_dump())
    return enriched

@task
def save_to_storage(data, path):
    df = pd.DataFrame(data)
    df.to_parquet(path)
    return path