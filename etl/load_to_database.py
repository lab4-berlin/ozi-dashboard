import os
import urllib
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.sql.functions import current_date
from sqlalchemy import text

USER = os.getenv("OZI_DATABASE_USER", 'asn_stats')
PASSWORD = os.getenv("OZI_DATABASE_PASSWORD", None)
DBNAME = os.getenv("OZI_DATABASE_NAME", 'asn_stats')
PORT = os.getenv("OZI_DATABASE_PORT", '5432')
HOST = os.getenv("OZI_DATABASE_HOST", '34.32.74.250')

BATCH_SIZE = 1000

def get_db_connection():
    encoded_password = urllib.parse.quote(str(PASSWORD)) if PASSWORD else ''
    connection_string = f"postgresql://{USER}:{encoded_password}@{HOST}:{PORT}/{DBNAME}"
    engine = create_engine(connection_string)
    return engine.connect()

def insert_country_asns_to_db(country_iso2, list_of_asns, save_sql_to_file=False, load_to_database=True):
    sql= "INSERT INTO data.asn(a_country_iso2, a_date, a_ripe_id, a_is_routed)\nVALUES"

    for item in list_of_asns:
        sql += f"\n('{country_iso2}', '{item['date']}', {item['asn']}, {item['is_routed']}),"
    sql = sql[:-1] + ";\n"

    if save_sql_to_file:
        filename = "sql/country_asns_{}_{}.sql".format(country_iso2, datetime.now().strftime('%Y%m%d_%H%M%S'))
        with open(filename, 'w') as f:
            print(sql, file=f)

    if load_to_database:
        with get_db_connection() as c:
            query = text(sql)
            c.execute(query)
            c.commit()


def insert_country_stats_to_db(country_iso2, resolution, stats, save_sql_to_file=False, load_to_database=True):
    sql= ("INSERT INTO data.country_stat(cs_country_iso2, cs_stats_timestamp, cs_stats_resolution, cs_v4_prefixes_ris,"
          " cs_v6_prefixes_ris, cs_asns_ris, cs_v4_prefixes_stats, cs_v6_prefixes_stats, cs_asns_stats )\nVALUES ")
    for item in stats:
        sql +=  (f"\n('{country_iso2}', '{item['timeline'][0]['starttime']}', '{resolution}', "
                f"{item['v4_prefixes_ris'] if item['v4_prefixes_ris'] else 'NULL'}, "
                f"{item['v6_prefixes_ris'] if item['v6_prefixes_ris'] else 'NULL'}, "
                f"{item['asns_ris'] if item['asns_ris'] else 'NULL'}, "
                f"{item['v4_prefixes_stats'] if item['v4_prefixes_stats'] else 'NULL'}, "
                f"{item['v6_prefixes_stats'] if item['v6_prefixes_stats'] else 'NULL'}, "
                f"{item['asns_stats'] if item['asns_stats'] else 'NULL'} ),")
    sql = sql[:-1] + ";"

    if save_sql_to_file:
        filename = "sql/country_stats_{}_{}.sql".format(
            country_iso2, datetime.now().strftime('%Y%m%d_%H%M%S')
        )
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, 'w') as f:
            print(sql, file=f)


    if load_to_database:
        with get_db_connection() as c:
            query = text(sql)
            c.execute(query)
            c.commit()

def insert_country_asn_neighbours_to_db(country_iso2, neighbours, save_sql_to_file=False, load_to_database=True):
    # connection = get_db_connection(PASSWORD)
    sql = "INSERT INTO data.asn_neighbour (an_asn, an_neighbour, an_date, an_type, an_power, an_v4_peers, an_v6_peers)\n VALUES "
    for item in neighbours:
        sql += f"\n({item['asn_req']}, {item['asn']}, '{item['date']}', '{item['type']}', {item['power']}, {item['v4_peers']}, {item['v6_peers']}),"
    sql = sql[:-1] + ";"

    if save_sql_to_file:
        filename = f"sql/asn_neighbours_{country_iso2}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
        with open(filename, 'w') as f:
            print(sql, file=f)

    if load_to_database:
        # print(f'Loading data to the database', end='...')
        with get_db_connection() as c:
            query = text(sql)
            c.execute(query)
            c.commit()
        # print(f'Done')

def insert_traffic_for_country_to_db(country_iso2, traffic, save_sql_to_file=False, load_to_database=True):
    # connection = get_db_connection(PASSWORD)
    sql= "INSERT INTO data.country_traffic(cr_country_iso2, cr_date, cr_traffic)\nVALUES"
    for timestamp, value in zip(traffic['timestamps'], traffic['values']):
        sql += f"\n('{country_iso2}', '{timestamp}', {value}),"
    sql = sql[:-1] + ";"

    if save_sql_to_file:
        filename = "sql/country_traffic_{}_{}.sql".format(country_iso2, datetime.now().strftime('%Y%m%d_%H%M%S'))
        with open(filename, 'w') as f:
            print(sql, file=f)
    if load_to_database:
        with get_db_connection() as c:
            query = text(sql)
            c.execute(query)
            c.commit()

def insert_internet_quality_for_country_to_db(country_iso2, internet_quality, save_sql_to_file=False, load_to_database=True):
    # connection = get_db_connection(PASSWORD)
    sql= "INSERT INTO data.country_internet_quality(ci_country_iso2, ci_date, ci_p75, ci_p50, ci_p25)\nVALUES"
    for timestamp, p75, p50, p25 in (
            zip(internet_quality['timestamps'], internet_quality['p75'], internet_quality['p50'], internet_quality['p25'])):
        sql += f"\n('{country_iso2}', '{timestamp}', {p75}, {p50}, {p25}),"
    sql = sql[:-1] + ";"

    if save_sql_to_file:
        filename = "sql/country_internet_quality_{}_{}.sql".format(country_iso2, datetime.now().strftime('%Y%m%d_%H%M%S'))
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, 'w') as f:
            print(sql, file=f)
    if load_to_database:
        with get_db_connection() as c:
            query = text(sql)
            c.execute(query)
            c.commit()
