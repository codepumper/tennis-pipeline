from __future__ import annotations
import datetime as _dt
from curl_cffi import requests
from prefect import get_run_logger, task

@task(name="get_ao_mens_singles_ids")
def get_match_ids(
    date: _dt.date | None = None,
    tournament_name: str = "Australian Open, Melbourne, Australia",
    gender: str = "M",
    category: str = "singles"
) -> list[str]:
    task_logger = get_run_logger()
    target_date = date or _dt.date.today()
    formatted_date = target_date.strftime("%Y-%m-%d")
    
    endpoint = f"https://www.sofascore.com/api/v1/sport/tennis/scheduled-events/{formatted_date}"

    try:
        # TLS Impersonation
        response = requests.get(endpoint, impersonate="chrome120", timeout=30)
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        task_logger.error(f"Failed to fetch data for {formatted_date}: {exc}")
        return []

    events = payload.get("events", [])
    filtered_ids = []

    for event in events:
        curr_tournament = event.get("tournament", {}).get("name")
        filters = event.get("eventFilters", {})
        genders = filters.get("gender", [])
        categories = filters.get("category", [])
        
        # 3. Apply the triple filter: AO + Male + Singles
        if (
            curr_tournament == tournament_name and 
            gender in genders and 
            category in categories
        ):
            match_id = event.get("id")
            if match_id:
                filtered_ids.append(str(match_id))

    task_logger.info(
        f"Retrieved {len(filtered_ids)} {gender} {category.upper()} "
        f"match IDs for {tournament_name} on {formatted_date}."
    )
    
    return filtered_ids