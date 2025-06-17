"""
This module provides functions for loading processed ETL data into the PostgreSQL database.
It handles database connections and data insertion for various data types.

# Note: SQL queries are constructed using f-strings. While inputs are generally from
# controlled sources in this ETL, be cautious about SQL injection vulnerabilities
# if inputs could come from untrusted user-provided data.
# Parameterized queries are generally recommended for database interactions.
"""

import os
import urllib
from datetime import datetime
from sqlalchemy import create_engine, text

# from sqlalchemy.sql.functions import current_date # Not used in the current version

# Environment variable names for database connection parameters
# These are resolved at module import time.
USER_ENV_VAR = "OZI_DATABASE_USER"
PASSWORD_ENV_VAR = "OZI_DATABASE_PASSWORD"
DBNAME_ENV_VAR = "OZI_DATABASE_NAME"
PORT_ENV_VAR = "OZI_DATABASE_PORT"
HOST_ENV_VAR = "OZI_DATABASE_HOST"

USER = os.getenv(USER_ENV_VAR, "asn_stats")
PASSWORD = os.getenv(PASSWORD_ENV_VAR, None)  # Ensure PASSWORD can be None if not set
DBNAME = os.getenv(DBNAME_ENV_VAR, "asn_stats")
PORT = os.getenv(PORT_ENV_VAR, "5432")
HOST = os.getenv(HOST_ENV_VAR, "34.32.74.250")

BATCH_SIZE = 1000  # Currently unused in insertion logic, but defined.


def get_db_connection():
    """
    Establishes and returns a SQLAlchemy database connection.

    Uses environment variables for database connection parameters:
    - OZI_DATABASE_USER: Username for the database.
    - OZI_DATABASE_PASSWORD: Password for the database.
    - OZI_DATABASE_HOST: Hostname or IP address of the database server.
    - OZI_DATABASE_PORT: Port number for the database server.
    - OZI_DATABASE_NAME: Name of the database.

    The password is URL-encoded before being used in the connection string.
    If OZI_DATABASE_PASSWORD is not set, it will attempt to connect without a password
    or with a None password, behavior of which depends on database and driver.

    Returns:
        sqlalchemy.engine.Connection: A SQLAlchemy Connection object.
                                      Returns None or raises an exception if
                                      connection fails (depends on SQLAlchemy config).
    """
    if PASSWORD is None:
        # Handle case where password is not set - connect without it or raise error
        # For now, let's assume connecting with a None password might work for some local setups
        # or will be caught by create_engine if invalid.
        # Alternatively, raise an error here if password is required.
        print("Warning: OZI_DATABASE_PASSWORD environment variable is not set.")
        encoded_password = ""  # Or handle as per db requirements for no password
    else:
        encoded_password = urllib.parse.quote(PASSWORD)

    connection_string = f"postgresql://{USER}:{encoded_password}@{HOST}:{PORT}/{DBNAME}"
    engine = create_engine(connection_string)
    return engine.connect()


def insert_country_asns_to_db(
    country_iso2, list_of_asns, save_sql_to_file=False, load_to_database=True
):
    """
    Inserts a list of ASN data for a specific country into the 'data.asn' table.

    Args:
        country_iso2 (str): The ISO2 code of the country for these ASNs.
        list_of_asns (list[dict]): A list of dictionaries, where each dictionary
                                   represents an ASN record. Expected keys:
                                   - 'date' (str): The date of the record (e.g., 'YYYY-MM-DD').
                                   - 'asn' (str or int): The ASN identifier (e.g., 'AS123' or 123).
                                   - 'is_routed' (bool): Boolean indicating if the ASN is routed.
        save_sql_to_file (bool): If True, saves the generated SQL query to a file.
        load_to_database (bool): If True, executes the SQL query against the database.
    """
    if not list_of_asns:
        print(f"No ASN data provided for {country_iso2}, skipping database insertion.")
        return

    sql_base = (
        "INSERT INTO data.asn(a_country_iso2, a_date, a_ripe_id, a_is_routed)\nVALUES"
    )
    values_list = []
    for item in list_of_asns:
        # Basic validation or sanitization could be added here if needed
        date_val = item.get(
            "date", "NULL"
        )  # Handle missing keys gracefully if possible
        asn_val = item.get("asn", "NULL")
        is_routed_val = item.get("is_routed", False)  # Default to False if missing
        values_list.append(
            f"('{country_iso2}', '{date_val}', {asn_val}, {is_routed_val})"
        )

    if (
        not values_list
    ):  # Should not happen if list_of_asns was not empty, but as a safe guard
        print(f"No valid ASN data to insert for {country_iso2}.")
        return

    sql = sql_base + "\n" + ",\n".join(values_list) + ";"

    if save_sql_to_file:
        # Ensure sql directory exists
        os.makedirs("sql", exist_ok=True)
        filename = f"sql/country_asns_{country_iso2}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
        with open(filename, "w") as f:
            f.write(sql)  # Use f.write for direct string writing
        print(f"SQL query saved to {filename}")

    if load_to_database:
        conn = None
        try:
            conn = get_db_connection()
            query = text(sql)
            conn.execute(query)
            conn.commit()
            print(f"Successfully loaded ASN data for {country_iso2} to database.")
        except Exception as e:
            print(f"Error loading ASN data for {country_iso2} to database: {e}")
            # Optionally rollback or handle transaction state if conn was established
            if conn:
                # conn.rollback() # Depending on desired error handling
                pass
        finally:
            if conn:
                conn.close()


def insert_country_stats_to_db(
    country_iso2, resolution, stats, save_sql_to_file=False, load_to_database=True
):
    """
    Inserts country resource statistics into the 'data.country_stat' table.

    Args:
        country_iso2 (str): The ISO2 code of the country.
        resolution (str): The resolution of the statistics (e.g., "1d").
        stats (list[dict]): A list of dictionaries, each representing a statistics record.
                            Expected keys in each dict:
                            - 'timeline' (list[dict]): List containing at least one dict with 'starttime'.
                            - 'v4_prefixes_ris' (int/None): Count of IPv4 prefixes (RIS).
                            - 'v6_prefixes_ris' (int/None): Count of IPv6 prefixes (RIS).
                            - 'asns_ris' (int/None): Count of ASNs (RIS).
                            - 'v4_prefixes_stats' (int/None): Count of IPv4 prefixes (Stats).
                            - 'v6_prefixes_stats' (int/None): Count of IPv6 prefixes (Stats).
                            - 'asns_stats' (int/None): Count of ASNs (Stats).
        save_sql_to_file (bool): If True, saves the SQL query to a file.
        load_to_database (bool): If True, executes the query against the database.
    """
    if not stats:
        print(
            f"No stats data provided for {country_iso2}, skipping database insertion."
        )
        return

    sql_base = (
        "INSERT INTO data.country_stat(cs_country_iso2, cs_stats_timestamp, cs_stats_resolution, "
        "cs_v4_prefixes_ris, cs_v6_prefixes_ris, cs_asns_ris, "
        "cs_v4_prefixes_stats, cs_v6_prefixes_stats, cs_asns_stats)\nVALUES"
    )
    values_list = []
    for item in stats:
        ts = item.get("timeline", [{}])[0].get(
            "starttime", "NULL"
        )  # Safely access nested 'starttime'
        v4_ris = item.get("v4_prefixes_ris", "NULL")
        v6_ris = item.get("v6_prefixes_ris", "NULL")
        asns_ris_val = item.get("asns_ris", "NULL")
        v4_stats = item.get("v4_prefixes_stats", "NULL")
        v6_stats = item.get("v6_prefixes_stats", "NULL")
        asns_stats_val = item.get("asns_stats", "NULL")

        # Ensure NULLs are actual SQL NULLs, not quoted strings 'NULL' for numeric types
        def sql_null_or_val(val):
            return "NULL" if val is None or str(val).upper() == "NULL" else val

        values_list.append(
            f"('{country_iso2}', '{ts}', '{resolution}', "
            f"{sql_null_or_val(v4_ris)}, {sql_null_or_val(v6_ris)}, {sql_null_or_val(asns_ris_val)}, "
            f"{sql_null_or_val(v4_stats)}, {sql_null_or_val(v6_stats)}, {sql_null_or_val(asns_stats_val)})"
        )

    if not values_list:
        print(f"No valid stats data to insert for {country_iso2}.")
        return

    sql = sql_base + "\n" + ",\n".join(values_list) + ";"

    if save_sql_to_file:
        os.makedirs("sql", exist_ok=True)
        filename = f"sql/country_stats_{country_iso2}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
        with open(filename, "w") as f:
            f.write(sql)
        print(f"SQL query saved to {filename}")

    if load_to_database:
        conn = None
        try:
            conn = get_db_connection()
            query = text(sql)
            conn.execute(query)
            conn.commit()
            print(f"Successfully loaded country stats for {country_iso2} to database.")
        except Exception as e:
            print(f"Error loading country stats for {country_iso2} to database: {e}")
            if conn:
                pass  # conn.rollback()
        finally:
            if conn:
                conn.close()


def insert_country_asn_neighbours_to_db(
    country_iso2, neighbours, save_sql_to_file=False, load_to_database=True
):
    """
    Inserts ASN neighbours data into the 'data.asn_neighbour' table.

    Args:
        country_iso2 (str): ISO2 code of the country this data relates to (used for filename).
        neighbours (list[dict]): A list of dictionaries, each representing an ASN neighbour relationship.
                                 Expected keys: 'asn_req' (requesting ASN), 'asn' (neighbour ASN),
                                 'date', 'type', 'power', 'v4_peers', 'v6_peers'.
        save_sql_to_file (bool): If True, saves the SQL query to a file.
        load_to_database (bool): If True, executes the query against the database.
    """
    if not neighbours:
        print(
            f"No ASN neighbours data provided (country: {country_iso2}), skipping database insertion."
        )
        return

    sql_base = (
        "INSERT INTO data.asn_neighbour (an_asn, an_neighbour, an_date, an_type, "
        "an_power, an_v4_peers, an_v6_peers)\nVALUES"
    )
    values_list = []
    for item in neighbours:
        # Example of safer access and potential type conversion/validation
        asn_req = item.get("asn_req", "NULL")
        asn = item.get("asn", "NULL")
        date_val = item.get("date", "NULL")
        type_val = item.get("type", "")  # Assuming type is a string, empty if missing
        power_val = item.get("power", "NULL")
        v4_peers_val = item.get("v4_peers", "NULL")
        v6_peers_val = item.get("v6_peers", "NULL")
        values_list.append(
            f"({asn_req}, {asn}, '{date_val}', '{type_val}', {power_val}, "
            f"{v4_peers_val}, {v6_peers_val})"
        )

    if not values_list:
        print(f"No valid ASN neighbours data to insert for {country_iso2}.")
        return

    sql = sql_base + "\n" + ",\n".join(values_list) + ";"

    if save_sql_to_file:
        os.makedirs("sql", exist_ok=True)
        filename = f"sql/asn_neighbours_{country_iso2}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
        with open(filename, "w") as f:
            f.write(sql)
        print(f"SQL query saved to {filename}")

    if load_to_database:
        conn = None
        try:
            conn = get_db_connection()
            query = text(sql)
            conn.execute(query)
            conn.commit()
            print(f"Successfully loaded ASN neighbours for {country_iso2} to database.")
        except Exception as e:
            print(f"Error loading ASN neighbours for {country_iso2} to database: {e}")
            if conn:
                pass  # conn.rollback()
        finally:
            if conn:
                conn.close()


def insert_traffic_for_country_to_db(
    country_iso2, traffic, save_sql_to_file=False, load_to_database=True
):  # Added load_to_database
    """
    Inserts country traffic data into the 'data.country_traffic' table.

    Args:
        country_iso2 (str): The ISO2 code of the country.
        traffic (dict): A dictionary containing traffic data. Expected keys:
                        'timestamps' (list): List of timestamp strings.
                        'values' (list): List of traffic values corresponding to timestamps.
        save_sql_to_file (bool): If True, saves the SQL query to a file.
        load_to_database (bool): If True, executes the query. (This param was missing)
    """
    if not traffic or not traffic.get("timestamps") or not traffic.get("values"):
        print(
            f"No or invalid traffic data provided for {country_iso2}, skipping insertion."
        )
        return
    if len(traffic["timestamps"]) != len(traffic["values"]):
        print(f"Mismatch in traffic timestamps and values length for {country_iso2}.")
        return

    sql_base = (
        "INSERT INTO data.country_traffic(cr_country_iso2, cr_date, cr_traffic)\nVALUES"
    )
    values_list = []
    for timestamp, value in zip(traffic["timestamps"], traffic["values"]):
        values_list.append(f"('{country_iso2}', '{timestamp}', {value})")

    if not values_list:
        print(f"No traffic data points to insert for {country_iso2}.")
        return

    sql = sql_base + "\n" + ",\n".join(values_list) + ";"

    if save_sql_to_file:
        os.makedirs("sql", exist_ok=True)
        filename = f"sql/country_traffic_{country_iso2}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
        with open(filename, "w") as f:
            f.write(sql)
        print(f"SQL query saved to {filename}")

    if load_to_database:  # Added actual database loading logic
        conn = None
        try:
            conn = get_db_connection()
            query = text(sql)
            conn.execute(query)
            conn.commit()
            print(f"Successfully loaded traffic data for {country_iso2} to database.")
        except Exception as e:
            print(f"Error loading traffic data for {country_iso2} to database: {e}")
            if conn:
                pass
        finally:
            if conn:
                conn.close()


def insert_internet_quality_for_country_to_db(
    country_iso2, internet_quality, save_sql_to_file=False, load_to_database=True
):  # Added load_to_database
    """
    Inserts country internet quality data into the 'data.country_internet_quality' table.

    Args:
        country_iso2 (str): The ISO2 code of the country.
        internet_quality (dict): Dictionary with internet quality data. Expected keys:
                                 'timestamps' (list), 'p75' (list), 'p50' (list), 'p25' (list).
        save_sql_to_file (bool): If True, saves the SQL query to a file.
        load_to_database (bool): If True, executes the query. (This param was missing)
    """
    required_keys = ["timestamps", "p75", "p50", "p25"]
    if not internet_quality or not all(
        key in internet_quality for key in required_keys
    ):
        print(
            f"No or invalid internet quality data provided for {country_iso2}, skipping insertion."
        )
        return

    lengths = [len(internet_quality[key]) for key in required_keys]
    if not all(l == lengths[0] for l in lengths):
        print(f"Mismatch in internet quality data arrays lengths for {country_iso2}.")
        return
    if lengths[0] == 0:
        print(f"No internet quality data points for {country_iso2}.")
        return

    sql_base = "INSERT INTO data.country_internet_quality(ci_country_iso2, ci_date, ci_p75, ci_p50, ci_p25)\nVALUES"
    values_list = []
    for timestamp, p75, p50, p25 in zip(
        internet_quality["timestamps"],
        internet_quality["p75"],
        internet_quality["p50"],
        internet_quality["p25"],
    ):
        values_list.append(f"('{country_iso2}', '{timestamp}', {p75}, {p50}, {p25})")

    sql = sql_base + "\n" + ",\n".join(values_list) + ";"

    if save_sql_to_file:
        os.makedirs("sql", exist_ok=True)
        filename = f"sql/country_internet_quality_{country_iso2}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
        with open(filename, "w") as f:
            f.write(sql)
        print(f"SQL query saved to {filename}")

    if load_to_database:  # Added actual database loading logic
        conn = None
        try:
            conn = get_db_connection()
            query = text(sql)
            conn.execute(query)
            conn.commit()
            print(
                f"Successfully loaded internet quality data for {country_iso2} to database."
            )
        except Exception as e:
            print(
                f"Error loading internet quality data for {country_iso2} to database: {e}"
            )
            if conn:
                pass
        finally:
            if conn:
                conn.close()
