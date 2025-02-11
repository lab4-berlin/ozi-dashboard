from dagster import asset, with_resources
from etl.main import get_stats_for_country, insert_country_stats_to_db
from etl.db_resource import db_connection

@asset(required_resource_keys={"db"})
def etl_load_stats_1d(context):
    """
    Extracts daily statistics for a given country and date range,
    and loads them into the database.
    """
    iso2 = 'DE'  
    date_from = '2025-01-01'
    date_to = '2025-01-31'

    # Extract data from the API
    stats = get_stats_for_country(iso2, date_from, date_to, '1d')
    if stats:
        # Load data into the database
        insert_country_stats_to_db(iso2, '1d', stats, True, context.resources.db)
        context.log.info(f"Successfully loaded stats for {iso2} from {date_from} to {date_to}.")
    else:
        context.log.warning(f"No stats found for {iso2} from {date_from} to {date_to}.")
