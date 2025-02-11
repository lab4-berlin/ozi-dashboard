from dagster import op, job
from etl.main import get_stats_for_country, insert_country_stats_to_db

@op
def etl_load_stats_1d(iso2: str, date_from: str, date_to: str):
    """Dagster op to load daily stats for a country."""
    stats = get_stats_for_country(iso2, date_from, date_to, '1d')
    if stats:
        insert_country_stats_to_db(iso2, '1d', stats, True)
    return f"Loaded stats for {iso2} from {date_from} to {date_to}"

@job
def etl_job():
    """A Dagster job to run the ETL task."""
    etl_load_stats_1d()
