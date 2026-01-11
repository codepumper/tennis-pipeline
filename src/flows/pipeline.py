from prefect import flow
from datetime import datetime
from src.stats.calculators import calculate_historical_baseline
from src.tasks.ingestion import scrape_live_2026, enrich_data, save_to_storage

@flow(log_prints=True)
def run_ao_pipeline():
    # 1. Load History
    stats = calculate_historical_baseline("data/historical/sackmann_2021_2025.csv")
    
    # 2. Get Live Data
    live_data = scrape_live_2026()
    
    # 3. Enrich & Validate
    final_data = enrich_data(live_data, stats)
    
    # 4. Save
    date_str = datetime.now().strftime("%Y-%m-%d")
    output_path = f"data/processed/ao_stats_{date_str}.parquet"
    save_to_storage(final_data, output_path)
    
    print(f"Success! Enriched data saved to {output_path}")

if __name__ == "__main__":
    run_ao_pipeline()