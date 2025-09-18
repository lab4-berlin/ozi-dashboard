import os
import urllib
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.sql.functions import current_date
from sqlalchemy import text

HOST = os.getenv("POSTGRES_HOST", "ozi-postgres")
PORT = os.getenv("POSTGRES_PORT", "5432")
USER = os.getenv("POSTGRES_OZI_USER", "ozi")
PASSWORD = os.getenv("POSTGRES_OZI_PASSWORD", "ozi_password")
DBNAME = os.getenv("POSTGRES_DB", "ozi_db2")

BATCH_SIZE = 1000

# Create a single engine with connection pooling
def create_engine_with_pool():
    if PASSWORD:
        encoded_password = urllib.parse.quote(str(PASSWORD))
        connection_string = (
            f"postgresql://{USER}:{encoded_password}@{HOST}:{PORT}/{DBNAME}"
        )
    else:
        connection_string = f"postgresql://{USER}@{HOST}:{PORT}/{DBNAME}"

    # Create engine with connection pooling
    engine = create_engine(
        connection_string,
        pool_size=5,        # number of connections to maintain in the pool
        max_overflow=10,    # number of connections that can be created beyond pool_size
        pool_pre_ping=True, # validates connections before use
        pool_recycle=3600   # recycle connections after 3600 seconds (1 hour)
    )
    return engine

# Create a single engine instance for the application
ENGINE = create_engine_with_pool()

def get_db_connection():
    return ENGINE.connect()


def insert_country_asns_to_db(
    country_iso2, list_of_asns, save_sql_to_file=False, load_to_database=True
):
    if not list_of_asns:
        return

    with get_db_connection() as c:
        # Fetch existing ASNs for the given country and dates
        existing_asns_query = text(
            f"""
            SELECT a_ripe_id, a_date
            FROM data.asn
            WHERE a_country_iso2 = :country_iso2
            AND a_date IN ({', '.join([f"'{item['date']}'" for item in list_of_asns])})
        """
        )

        existing_asns_result = c.execute(
            existing_asns_query, {"country_iso2": country_iso2}
        ).fetchall()
        existing_asns_set = set(
            (asn, date.strftime("%Y-%m-%d")) for asn, date in existing_asns_result
        )

        # Filter out ASNs that already exist
        new_asns_to_insert = [
            item
            for item in list_of_asns
            if (item["asn"], item["date"]) not in existing_asns_set
        ]

        if not new_asns_to_insert:
            return

    sql = "INSERT INTO data.asn(a_country_iso2, a_date, a_ripe_id, a_is_routed)\nVALUES"
    values_list = []
    for item in new_asns_to_insert:
        values_list.append(
            f"('{country_iso2}', '{item['date']}', {item['asn']}, {item['is_routed']})"
        )
    sql += ",\n".join(values_list) + ";\n"

    if save_sql_to_file:
        filename = "sql/country_asns_{}_{}.sql".format(
            country_iso2, datetime.now().strftime("%Y%m%d_%H%M%S")
        )
        with open(filename, "w") as f:
            print(sql, file=f)

    if load_to_database:
        with get_db_connection() as c:
            query = text(sql)
            c.execute(query)
            c.commit()


def insert_country_stats_to_db(
    country_iso2, resolution, stats, save_sql_to_file=False, load_to_database=True
):
    if not stats:
        return

    with get_db_connection() as c:
        # Fetch existing stats for the given country, resolution, and timestamps
        existing_stats_query = text(
            f"""
            SELECT cs_stats_timestamp
            FROM data.country_stat
            WHERE cs_country_iso2 = :country_iso2
            AND cs_stats_resolution = :resolution
            AND cs_stats_timestamp IN ({', '.join([f"'{item['timeline'][0]['starttime']}'" for item in stats])})
        """
        )

        existing_stats_result = c.execute(
            existing_stats_query,
            {"country_iso2": country_iso2, "resolution": resolution},
        ).fetchall()
        existing_stats_set = set(
            timestamp.strftime("%Y-%m-%d %H:%M:%S+00:00")
            for timestamp, in existing_stats_result
        )

        # Filter out stats that already exist
        new_stats_to_insert = []
        for item in stats:
            timestamp = item["timeline"][0]["starttime"]
            try:
                item_timestamp_dt = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S%z")
            except ValueError:
                item_timestamp_dt = datetime.strptime(
                    timestamp.replace("Z", ""), "%Y-%m-%dT%H:%M:%S"
                )

            item_timestamp_formatted = item_timestamp_dt.strftime(
                "%Y-%m-%d %H:%M:%S+00:00"
            )

            if item_timestamp_formatted not in existing_stats_set:
                new_stats_to_insert.append(item)

        if not new_stats_to_insert:
            return

    sql = (
        "INSERT INTO data.country_stat(cs_country_iso2, cs_stats_timestamp, cs_stats_resolution, cs_v4_prefixes_ris,"
        " cs_v6_prefixes_ris, cs_asns_ris, cs_v4_prefixes_stats, cs_v6_prefixes_stats, cs_asns_stats )\nVALUES "
    )
    values_list = []
    for item in new_stats_to_insert:
        v4_ris = (
            item["v4_prefixes_ris"] if item["v4_prefixes_ris"] is not None else "NULL"
        )
        v6_ris = (
            item["v6_prefixes_ris"] if item["v6_prefixes_ris"] is not None else "NULL"
        )
        asns_ris = item["asns_ris"] if item["asns_ris"] is not None else "NULL"
        v4_stats = (
            item["v4_prefixes_stats"]
            if item["v4_prefixes_stats"] is not None
            else "NULL"
        )
        v6_stats = (
            item["v6_prefixes_stats"]
            if item["v6_prefixes_stats"] is not None
            else "NULL"
        )
        asns_stats = item["asns_stats"] if item["asns_stats"] is not None else "NULL"

        values_list.append(
            f"('{country_iso2}', '{item['timeline'][0]['starttime']}', '{resolution}', "
            f"{v4_ris}, "
            f"{v6_ris}, "
            f"{asns_ris}, "
            f"{v4_stats}, "
            f"{v6_stats}, "
            f"{asns_stats} "
            ")"
        )
    sql += ",\n".join(values_list) + ";"

    if save_sql_to_file:
        filename = "sql/country_stats_{}_{}.sql".format(
            country_iso2, datetime.now().strftime("%Y%m%d_%H%M%S")
        )
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "w") as f:
            print(sql, file=f)

    if load_to_database:
        with get_db_connection() as c:
            query = text(sql)
            c.execute(query)
            c.commit()


def insert_country_asn_neighbours_to_db(
    country_iso2, neighbours, save_sql_to_file=False, load_to_database=True
):
    if not neighbours:
        return

    with get_db_connection() as c:
        # Fetch existing ASN neighbours for the given country and dates
        existing_neighbours_query = text(
            f"""
            SELECT an_asn, an_neighbour, an_date, an_type
            FROM data.asn_neighbour
            WHERE an_date IN ({', '.join([f"'{item['date']}'" for item in neighbours])})
        """
        )

        existing_neighbours_result = c.execute(existing_neighbours_query).fetchall()
        existing_neighbours_set = set(
            (asn, neighbour, date.strftime("%Y-%m-%d"), type)
            for asn, neighbour, date, type in existing_neighbours_result
        )

        # Filter out neighbours that already exist
        new_neighbours_to_insert = [
            item
            for item in neighbours
            if (item["asn_req"], item["asn"], item["date"], item["type"])
            not in existing_neighbours_set
        ]

        if not new_neighbours_to_insert:
            return

    sql = "INSERT INTO data.asn_neighbour (an_asn, an_neighbour, an_date, an_type, an_power, an_v4_peers, an_v6_peers)\n VALUES "
    values_list = []
    for item in new_neighbours_to_insert:
        values_list.append(
            f"({item['asn_req']}, {item['asn']}, '{item['date']}', '{item['type']}', {item['power']}, {item['v4_peers']}, {item['v6_peers']})"
        )
    sql += ",\n".join(values_list) + ";"

    if save_sql_to_file:
        filename = f"sql/asn_neighbours_{country_iso2}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
        with open(filename, "w") as f:
            print(sql, file=f)

    if load_to_database:
        with get_db_connection() as c:
            query = text(sql)
            c.execute(query)
            c.commit()


def insert_traffic_for_country_to_db(
    country_iso2, traffic, save_sql_to_file=False, load_to_database=True
):
    if not traffic or not traffic["timestamps"]:
        return

    with get_db_connection() as c:
        # Fetch existing traffic dates for the given country
        existing_traffic_query = text(
            f"""
            SELECT cr_date
            FROM data.country_traffic
            WHERE cr_country_iso2 = :country_iso2
            AND cr_date IN ({', '.join([f"'{ts}'" for ts in traffic['timestamps']])})
        """
        )

        existing_traffic_result = c.execute(
            existing_traffic_query, {"country_iso2": country_iso2}
        ).fetchall()
        existing_traffic_set = set(
            date.strftime("%Y-%m-%d %H:%M:%S+00:00")
            for date, in existing_traffic_result
        )

        new_traffic_to_insert = []

        for timestamp, value in zip(traffic["timestamps"], traffic["values"]):
            try:
                item_timestamp_dt = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                item_timestamp_dt = datetime.strptime(
                    timestamp.replace("Z", ""), "%Y-%m-%dT%H:%M:%S"
                )

            item_timestamp_formatted = item_timestamp_dt.strftime(
                "%Y-%m-%d %H:%M:%S+00:00"
            )

            if item_timestamp_formatted not in existing_traffic_set:
                new_traffic_to_insert.append({"timestamp": timestamp, "value": value})

        if not new_traffic_to_insert:
            return

    sql = (
        "INSERT INTO data.country_traffic(cr_country_iso2, cr_date, cr_traffic)\nVALUES"
    )
    values_list = []
    for item in new_traffic_to_insert:
        values_list.append(
            f"('{country_iso2}', '{item['timestamp']}', {item['value']})"
        )
    sql += ",\n".join(values_list) + ";"

    if save_sql_to_file:
        filename = "sql/country_traffic_{}_{}.sql".format(
            country_iso2, datetime.now().strftime("%Y%m%d_%H%M%S")
        )
        with open(filename, "w") as f:
            print(sql, file=f)

    if load_to_database:
        with get_db_connection() as c:
            query = text(sql)
            c.execute(query)
            c.commit()


def insert_internet_quality_for_country_to_db(
    country_iso2, internet_quality, save_sql_to_file=False, load_to_database=True
):
    if not internet_quality or not internet_quality["timestamps"]:
        return

    with get_db_connection() as c:
        # Fetch existing internet quality dates for the given country
        existing_quality_query = text(
            f"""
            SELECT ci_date
            FROM data.country_internet_quality
            WHERE ci_country_iso2 = :country_iso2
            AND ci_date IN ({', '.join([f"'{ts}'" for ts in internet_quality['timestamps']])})
        """
        )

        existing_quality_result = c.execute(
            existing_quality_query, {"country_iso2": country_iso2}
        ).fetchall()
        existing_quality_set = set(
            date.strftime("%Y-%m-%d %H:%M:%S+00:00")
            for date, in existing_quality_result
        )

        new_quality_to_insert = []

        for timestamp, p75, p50, p25 in zip(
            internet_quality["timestamps"],
            internet_quality["p75"],
            internet_quality["p50"],
            internet_quality["p25"],
        ):
            try:
                item_timestamp_dt = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                item_timestamp_dt = datetime.strptime(
                    timestamp.replace("Z", ""), "%Y-%m-%dT%H:%M:%S"
                )

            item_timestamp_formatted = item_timestamp_dt.strftime(
                "%Y-%m-%d %H:%M:%S+00:00"
            )

            if item_timestamp_formatted not in existing_quality_set:
                new_quality_to_insert.append(
                    {"timestamp": timestamp, "p75": p75, "p50": p50, "p25": p25}
                )

        if not new_quality_to_insert:
            return

    sql = "INSERT INTO data.country_internet_quality(ci_country_iso2, ci_date, ci_p75, ci_p50, ci_p25)\nVALUES"
    values_list = []
    for item in new_quality_to_insert:
        values_list.append(
            f"('{country_iso2}', '{item['timestamp']}', {item['p75']}, {item['p50']}, {item['p25']})"
        )
    sql += ",\n".join(values_list) + ";"

    if save_sql_to_file:
        filename = "sql/country_internet_quality_{}_{}.sql".format(
            country_iso2, datetime.now().strftime("%Y%m%d_%H%M%S")
        )
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "w") as f:
            print(sql, file=f)

    if load_to_database:
        with get_db_connection() as c:
            query = text(sql)
            c.execute(query)
            c.commit()
