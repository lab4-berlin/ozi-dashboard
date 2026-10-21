import os
import sys
import time
import random
from datetime import datetime

# Add root directory to python path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from common.lake import get_lake_connection, lake_connection

BATCH_SIZE = 1000


def generate_load_id() -> int:
    """
    Generates a collision-safe 64-bit monotonic load_id.
    Format: 14-digit UTC timestamp (YYYYMMDDHHMMSS) + 4-digit random discriminator.
    Fits in signed 64-bit BIGINT (max 9.22e18).
    """
    return int(time.strftime("%Y%m%d%H%M%S") + f"{random.randint(0, 9999):04d}")


def record_load_start(con, load_id: int, command: str):
    """Logs the beginning of an ETL load in data.etl_load."""
    now = datetime.now()
    con.execute(
        """
        INSERT INTO data.etl_load (load_id, start_time, finish_time, command, status)
        VALUES (?, ?, NULL, ?, 'running');
        """,
        [load_id, now, command],
    )


def record_load_end(con, load_id: int, status: str = "completed"):
    """Marks an ETL load as completed or failed in data.etl_load."""
    now = datetime.now()
    con.execute(
        """
        UPDATE data.etl_load
        SET finish_time = ?, status = ?
        WHERE load_id = ?;
        """,
        [now, status, load_id],
    )


def insert_country_asns_to_lake(
    country_iso2,
    list_of_asns,
    load_id=None,
    con=None,
):
    if not list_of_asns:
        return 0

    if load_id is None:
        load_id = generate_load_id()

    close_con = False
    if con is None:
        con = get_lake_connection(role="writer", read_only=False)
        close_con = True

    try:
        # Extract unique dates for deduplication
        dates = list(set(item["date"] for item in list_of_asns))
        placeholders = ", ".join(["?"] * len(dates))

        # Check existing records in DuckLake
        query_existing = f"""
            SELECT a_ripe_id, strftime(a_date, '%Y-%m-%d')
            FROM data.asn
            WHERE a_country_iso2 = ?
              AND strftime(a_date, '%Y-%m-%d') IN ({placeholders});
        """
        existing_rows = con.execute(query_existing, [country_iso2] + dates).fetchall()
        existing_set = set((asn, dt) for asn, dt in existing_rows)

        # Filter out existing entries
        new_items = [
            item for item in list_of_asns
            if (item["asn"], item["date"]) not in existing_set
        ]

        if not new_items:
            return 0

        now = datetime.now()
        rows_to_insert = [
            (
                country_iso2,
                datetime.strptime(item["date"], "%Y-%m-%d"),
                item["asn"],
                bool(item["is_routed"]),
                load_id,
                now,
                now,
            )
            for item in new_items
        ]

        con.executemany(
            """
            INSERT INTO data.asn (
                a_country_iso2,
                a_date,
                a_ripe_id,
                a_is_routed,
                load_id,
                created,
                updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            rows_to_insert,
        )
        return len(rows_to_insert)
    finally:
        if close_con:
            con.close()


def insert_country_stats_to_lake(
    country_iso2,
    resolution,
    stats,
    load_id=None,
    con=None,
):
    if not stats:
        return 0

    if load_id is None:
        load_id = generate_load_id()

    close_con = False
    if con is None:
        con = get_lake_connection(role="writer", read_only=False)
        close_con = True

    try:
        # Parse and standardize timestamps
        formatted_items = []
        for item in stats:
            raw_ts = item["timeline"][0]["starttime"]
            try:
                dt = datetime.strptime(raw_ts, "%Y-%m-%dT%H:%M:%S%z")
            except ValueError:
                dt = datetime.strptime(raw_ts.replace("Z", ""), "%Y-%m-%dT%H:%M:%S")
            # DuckDB timestamp format
            ts_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            formatted_items.append((item, dt, ts_str))

        timestamps = list(set(ts_str for _, _, ts_str in formatted_items))
        placeholders = ", ".join(["?"] * len(timestamps))

        # Check existing stats in DuckLake
        query_existing = f"""
            SELECT strftime(cs_stats_timestamp, '%Y-%m-%d %H:%M:%S')
            FROM data.country_stat
            WHERE cs_country_iso2 = ?
              AND cs_stats_resolution = ?
              AND strftime(cs_stats_timestamp, '%Y-%m-%d %H:%M:%S') IN ({placeholders});
        """
        existing_rows = con.execute(query_existing, [country_iso2, resolution] + timestamps).fetchall()
        existing_set = set(row[0] for row in existing_rows)

        new_items = [
            (item, dt) for item, dt, ts_str in formatted_items
            if ts_str not in existing_set
        ]

        if not new_items:
            return 0

        now = datetime.now()
        rows_to_insert = [
            (
                country_iso2,
                dt,
                resolution,
                item.get("v4_prefixes_ris"),
                item.get("v6_prefixes_ris"),
                item.get("asns_ris"),
                item.get("v4_prefixes_stats"),
                item.get("v6_prefixes_stats"),
                item.get("asns_stats"),
                load_id,
                now,
                now,
            )
            for item, dt in new_items
        ]

        con.executemany(
            """
            INSERT INTO data.country_stat (
                cs_country_iso2,
                cs_stats_timestamp,
                cs_stats_resolution,
                cs_v4_prefixes_ris,
                cs_v6_prefixes_ris,
                cs_asns_ris,
                cs_v4_prefixes_stats,
                cs_v6_prefixes_stats,
                cs_asns_stats,
                load_id,
                created,
                updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            rows_to_insert,
        )
        return len(rows_to_insert)
    finally:
        if close_con:
            con.close()


def insert_country_asn_neighbours_to_lake(
    country_iso2,
    neighbours,
    load_id=None,
    con=None,
):
    if not neighbours:
        return 0

    if load_id is None:
        load_id = generate_load_id()

    close_con = False
    if con is None:
        con = get_lake_connection(role="writer", read_only=False)
        close_con = True

    try:
        dates = list(set(item["date"] for item in neighbours))
        placeholders = ", ".join(["?"] * len(dates))

        query_existing = f"""
            SELECT an_asn, an_neighbour, strftime(an_date, '%Y-%m-%d'), an_type
            FROM data.asn_neighbour
            WHERE strftime(an_date, '%Y-%m-%d') IN ({placeholders});
        """
        existing_rows = con.execute(query_existing, dates).fetchall()
        existing_set = set((asn, nbr, dt, tp) for asn, nbr, dt, tp in existing_rows)

        new_items = [
            item for item in neighbours
            if (item["asn_req"], item["asn"], item["date"], item["type"]) not in existing_set
        ]

        if not new_items:
            return 0

        now = datetime.now()
        rows_to_insert = [
            (
                item["asn_req"],
                item["asn"],
                datetime.strptime(item["date"], "%Y-%m-%d"),
                item["type"],
                item["power"],
                item.get("v4_peers"),
                item.get("v6_peers"),
                load_id,
                now,
                now,
            )
            for item in new_items
        ]

        con.executemany(
            """
            INSERT INTO data.asn_neighbour (
                an_asn,
                an_neighbour,
                an_date,
                an_type,
                an_power,
                an_v4_peers,
                an_v6_peers,
                load_id,
                created,
                updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            rows_to_insert,
        )
        return len(rows_to_insert)
    finally:
        if close_con:
            con.close()


def insert_traffic_for_country_to_lake(
    country_iso2,
    traffic,
    load_id=None,
    con=None,
):
    if not traffic or not traffic.get("timestamps"):
        return 0

    if load_id is None:
        load_id = generate_load_id()

    close_con = False
    if con is None:
        con = get_lake_connection(role="writer", read_only=False)
        close_con = True

    try:
        parsed_entries = []
        for ts_str, val in zip(traffic["timestamps"], traffic["values"]):
            try:
                dt = datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                dt = datetime.strptime(ts_str.replace("Z", ""), "%Y-%m-%dT%H:%M:%S")
            parsed_entries.append((dt, val, dt.strftime("%Y-%m-%d %H:%M:%S")))

        timestamps = list(set(entry[2] for entry in parsed_entries))
        placeholders = ", ".join(["?"] * len(timestamps))

        query_existing = f"""
            SELECT strftime(cr_date, '%Y-%m-%d %H:%M:%S')
            FROM data.country_traffic
            WHERE cr_country_iso2 = ?
              AND strftime(cr_date, '%Y-%m-%d %H:%M:%S') IN ({placeholders});
        """
        existing_rows = con.execute(query_existing, [country_iso2] + timestamps).fetchall()
        existing_set = set(row[0] for row in existing_rows)

        new_entries = [entry for entry in parsed_entries if entry[2] not in existing_set]
        if not new_entries:
            return 0

        now = datetime.now()
        rows_to_insert = [
            (country_iso2, dt, val, load_id, now, now)
            for dt, val, _ in new_entries
        ]

        con.executemany(
            """
            INSERT INTO data.country_traffic (
                cr_country_iso2,
                cr_date,
                cr_traffic,
                load_id,
                created,
                updated
            ) VALUES (?, ?, ?, ?, ?, ?);
            """,
            rows_to_insert,
        )
        return len(rows_to_insert)
    finally:
        if close_con:
            con.close()


def insert_internet_quality_for_country_to_lake(
    country_iso2,
    internet_quality,
    load_id=None,
    con=None,
):
    if not internet_quality or not internet_quality.get("timestamps"):
        return 0

    if load_id is None:
        load_id = generate_load_id()

    close_con = False
    if con is None:
        con = get_lake_connection(role="writer", read_only=False)
        close_con = True

    try:
        parsed_entries = []
        for ts, p75, p50, p25 in zip(
            internet_quality["timestamps"],
            internet_quality["p75"],
            internet_quality["p50"],
            internet_quality["p25"],
        ):
            try:
                dt = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                dt = datetime.strptime(ts.replace("Z", ""), "%Y-%m-%dT%H:%M:%S")
            parsed_entries.append((dt, p75, p50, p25, dt.strftime("%Y-%m-%d %H:%M:%S")))

        timestamps = list(set(entry[4] for entry in parsed_entries))
        placeholders = ", ".join(["?"] * len(timestamps))

        query_existing = f"""
            SELECT strftime(ci_date, '%Y-%m-%d %H:%M:%S')
            FROM data.country_internet_quality
            WHERE ci_country_iso2 = ?
              AND strftime(ci_date, '%Y-%m-%d %H:%M:%S') IN ({placeholders});
        """
        existing_rows = con.execute(query_existing, [country_iso2] + timestamps).fetchall()
        existing_set = set(row[0] for row in existing_rows)

        new_entries = [entry for entry in parsed_entries if entry[4] not in existing_set]
        if not new_entries:
            return 0

        now = datetime.now()
        rows_to_insert = [
            (country_iso2, dt, p75, p50, p25, load_id, now, now)
            for dt, p75, p50, p25, _ in new_entries
        ]

        con.executemany(
            """
            INSERT INTO data.country_internet_quality (
                ci_country_iso2,
                ci_date,
                ci_p75,
                ci_p50,
                ci_p25,
                load_id,
                created,
                updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            rows_to_insert,
        )
        return len(rows_to_insert)
    finally:
        if close_con:
            con.close()
