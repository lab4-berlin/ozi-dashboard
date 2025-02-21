from dagster import asset, with_resources, Config
from etl.main import get_stats_for_country
from etl.db_resource import db_connection
from sqlalchemy import text


class Stats1dConfig(Config):
    iso2: str
    date_from: str
    date_to: str


@asset( required_resource_keys={"db"})
def etl_load_stats_1d(context, config:Stats1dConfig):
    """
    Extracts daily statistics for a given country and date range,
    and loads them into the database.
    """

    context.log.info(
        f"Running ETL load_stats_1d for {config.iso2} from {config.date_from} to {config.date_to}.")

    stats = get_stats_for_country(config.iso2, config.date_from, config.date_to, '1d')
    if stats:
        insert_country_stats_to_db(config.iso2, '1d', stats, context.resources.db)
        context.log.info(
            f"Successfully loaded {len(stats)} rows for {config.iso2} from {config.date_from} to {config.date_to}.")
    else:
        context.log.warning(f"No stats found for {config.iso2} from {config.date_from} to {config.date_to}.")

#move to i/o manager
def insert_country_stats_to_db(country_iso2, resolution, stats, db_engine):
    sql = "INSERT INTO data.country_stat(cs_country_iso2, cs_stats_timestamp, cs_stats_resolution, cs_v4_prefixes_ris," \
          " cs_v6_prefixes_ris, cs_asns_ris, cs_v4_prefixes_stats, cs_v6_prefixes_stats, cs_asns_stats )\nVALUES "

    for item in stats:
        sql += (f"\n('{country_iso2}', '{item['timeline'][0]['starttime']}', '{resolution}', "
                f"{item['v4_prefixes_ris'] if item['v4_prefixes_ris'] else 'NULL'}, "
                f"{item['v6_prefixes_ris'] if item['v6_prefixes_ris'] else 'NULL'}, "
                f"{item['asns_ris'] if item['asns_ris'] else 'NULL'}, "
                f"{item['v4_prefixes_stats'] if item['v4_prefixes_stats'] else 'NULL'}, "
                f"{item['v6_prefixes_stats'] if item['v6_prefixes_stats'] else 'NULL'}, "
                f"{item['asns_stats'] if item['asns_stats'] else 'NULL'} ),")
    sql = sql[:-1] + ";"

    with db_engine.begin() as conn:
        conn.execute(text(sql))
