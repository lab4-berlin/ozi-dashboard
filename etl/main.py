import argparse
import asyncio
import os
import sys
from datetime import datetime, timedelta

from country_lists import ALL_COUNTRIES
from load_to_database import (
    insert_country_asns_to_db,
    insert_country_stats_to_db,
    insert_country_asn_neighbours_to_db,
    insert_traffic_for_country_to_db,
    insert_internet_quality_for_country_to_db,
)
from load_to_lake import (
    insert_country_asns_to_lake,
    insert_country_stats_to_lake,
    insert_country_asn_neighbours_to_lake,
    insert_traffic_for_country_to_lake,
    insert_internet_quality_for_country_to_lake,
    generate_load_id,
    record_load_start,
    record_load_end,
    BATCH_SIZE,
)
from etl_jobs import (
    get_list_of_asns_for_country,
    get_stats_for_country,
    get_list_of_asn_neighbours_for_country,
    get_traffic_for_country,
    get_internet_quality_for_country,
)

CLOUDFLARE_API_TOKEN = os.getenv("OZI_CLOUDFLARE_API_TOKEN")
OZI_STORAGE_BACKEND = os.getenv("OZI_STORAGE_BACKEND", "both").lower()

RESOLUTION_DICT = {"D": "daily", "W": "weekly", "M": "Monthly"}


def run_finalize():
    from finalize_lake import finalize_materialized_tables
    finalize_materialized_tables()


def run_maintenance():
    from compact_lake import compact_and_clean_lake
    compact_and_clean_lake()


def run_backout(load_id: int):
    print(f"Backing out load_id: {load_id} across DuckLake and PostgreSQL...")
    from common.lake import get_lake_connection
    con = get_lake_connection(role="writer", read_only=False)
    try:
        tables = [
            "asn",
            "asn_neighbour",
            "country_stat",
            "country_traffic",
            "country_internet_quality",
        ]
        con.execute("BEGIN TRANSACTION;")
        for tbl in tables:
            res = con.execute(f"DELETE FROM data.{tbl} WHERE load_id = ?;", [load_id])
        con.execute("UPDATE data.etl_load SET status = 'rolled_back' WHERE load_id = ?;", [load_id])
        con.execute("COMMIT;")
        print(f"DuckLake load {load_id} backed out successfully.")
    except Exception:
        con.execute("ROLLBACK;")
        raise
    finally:
        con.close()


def main():
    parser = argparse.ArgumentParser(
        description="ETL script for OZI Dashboard project."
    )
    parser.add_argument(
        "-t",
        "--task",
        required=True,
        help="ETL task to perform (e.g., 'ASNS', 'STATS_1D', 'FINALIZE', 'MAINTENANCE', 'BACKOUT').",
    )
    parser.add_argument(
        "-c",
        "--countries",
        nargs="+",
        help="List of country ISO2 codes (e.g., 'US', 'DE').",
    )
    parser.add_argument(
        "-df", "--date-from", help="Start date in YYYY-MM-DD format."
    )
    parser.add_argument(
        "-dt", "--date-to", help="End date in YYYY-MM-DD format."
    )
    parser.add_argument(
        "-dr",
        "--date-resolution",
        help="Required resolution: D - Daily, W - Weekly, M - Monthly",
    )
    parser.add_argument(
        "--load-id",
        type=int,
        help="Load ID for BACKOUT task.",
    )
    parser.add_argument(
        "--save-to-file",
        action="store_true",
        help="Save generated SQL to file (default: False)",
    )
    parser.add_argument(
        "--async-ripe",
        action="store_true",
        help="Use the async RIPE client (httpx + connection pool) for ASN_NEIGHBOURS.",
    )

    args = parser.parse_args()
    task = args.task.upper()

    # Management tasks
    if task == "FINALIZE":
        run_finalize()
        return

    if task == "MAINTENANCE":
        run_maintenance()
        return

    if task == "BACKOUT":
        if not args.load_id:
            print("Error: --load-id is required for BACKOUT task.", file=sys.stderr)
            sys.exit(1)
        run_backout(args.load_id)
        return

    # Ingestion tasks require countries, dates, resolution
    if not (args.countries and args.date_from and args.date_to and args.date_resolution):
        print("Error: -c/--countries, -df/--date-from, -dt/--date-to, and -dr/--date-resolution are required.", file=sys.stderr)
        sys.exit(1)

    countries = args.countries
    resolution = args.date_resolution
    try:
        date_from = datetime.strptime(args.date_from, "%Y-%m-%d")
        date_to = datetime.strptime(args.date_to, "%Y-%m-%d")
    except ValueError:
        print("Error: Dates must be in YYYY-MM-DD format.", file=sys.stderr)
        return

    if countries[0] == "all":
        countries = list(ALL_COUNTRIES.keys())

    task_map = {
        "ASNS": etl_load_asns,
        "STATS_1D": etl_load_stats_1d,
        "STATS_5M": etl_load_stats_5m,
        "ASN_NEIGHBOURS": etl_load_asn_neighbours,
        "TRAFFIC": etl_load_traffic,
        "INTERNET_QUALITY": etl_load_internet_quality,
    }

    if task not in task_map:
        print(f"Error: Unknown task '{task}'.", file=sys.stderr)
        return

    if resolution not in RESOLUTION_DICT:
        print(f"Error: Unknown resolution '{resolution}'.", file=sys.stderr)
        return

    dates = generate_dates(date_from, date_to, resolution)

    for iso2 in countries:
        date_from_formatted = date_from.strftime("%Y-%m-%d")
        date_to_formatted = date_to.strftime("%Y-%m-%d")
        print(f"{'Started:':<12} {task}")
        print(f"{'At:':<12} {datetime.now()}")
        print(f"{'Country:':<12} {ALL_COUNTRIES.get(iso2, iso2)}")
        print(f"{'Date From:':<12} {date_from_formatted}")
        print(f"{'Date To:':<12} {date_to_formatted}")
        print(f"{'Resolution:':<12} {RESOLUTION_DICT[resolution]}")
        print(f"{'Backend:':<12} {OZI_STORAGE_BACKEND}")

        if task in ["STATS_5M", "TRAFFIC", "INTERNET_QUALITY"]:
            task_map[task](iso2, dates.copy(), save_to_file=args.save_to_file)
        elif task == "ASN_NEIGHBOURS" and args.async_ripe:
            etl_load_asn_neighbours_async(iso2, dates.copy())
        else:
            task_map[task](iso2, dates.copy())

        print(f"\n{'At:':<12} {datetime.now()}")
        print(f"{'Finished:':<12} {task}")


def generate_dates(date_from, date_to, resolution):
    dates = []
    if resolution == "W":
        date_from += timedelta(days=(7 - date_from.weekday()) % 7)
    elif resolution == "M":
        if date_from.day != 1:
            year = date_from.year + (date_from.month // 12)
            month = (date_from.month % 12) + 1
            date_from = datetime(year, month, 1)

    date = date_from

    while date <= date_to:
        dates.append(date)
        if resolution == "D":
            date += timedelta(days=1)
        elif resolution == "W":
            date += timedelta(days=7)
        elif resolution == "M":
            year = date.year + (date.month // 12)
            month = (date.month % 12) + 1
            date = datetime(year, month, 1)
        else:
            raise ValueError("Unsupported resolution. Use 'D', 'W', or 'M'.")

    return dates


def etl_load_asns(iso2, dates):
    print(f"{'Getting data from the API and storing to DB...':<50}")
    load_id = generate_load_id()
    for asns_batch in get_list_of_asns_for_country(iso2, dates, BATCH_SIZE):
        if OZI_STORAGE_BACKEND in ("postgres", "both"):
            insert_country_asns_to_db(iso2, asns_batch)
        if OZI_STORAGE_BACKEND in ("lake", "both"):
            insert_country_asns_to_lake(iso2, asns_batch, load_id=load_id)


def etl_load_stats_1d(iso2, dates):
    all_stats = []
    load_id = generate_load_id()
    for date in dates:
        stats = get_stats_for_country(iso2, date, date, "1d")
        if stats:
            all_stats.extend(stats)
            if OZI_STORAGE_BACKEND in ("postgres", "both"):
                insert_country_stats_to_db(iso2, "1d", stats, save_sql_to_file=True)

    # Batch insert to lake across all dates in 1 clean transaction
    if all_stats and OZI_STORAGE_BACKEND in ("lake", "both"):
        insert_country_stats_to_lake(iso2, "1d", all_stats, load_id=load_id)


def etl_load_stats_5m(iso2, dates, save_to_file=False):
    years = sorted(set(date.year for date in dates))
    load_id = generate_load_id()
    for year in years:
        date_from = datetime(year, 1, 1)
        date_to = datetime(year + 1, 1, 1)
        stats = get_stats_for_country(iso2, date_from, date_to, "5m")
        if stats:
            if OZI_STORAGE_BACKEND in ("postgres", "both"):
                insert_country_stats_to_db(iso2, "5m", stats, save_sql_to_file=save_to_file)
            if OZI_STORAGE_BACKEND in ("lake", "both"):
                insert_country_stats_to_lake(iso2, "5m", stats, load_id=load_id)


def etl_load_asn_neighbours(iso2, dates):
    print(f"{'Getting data from the API and storing to DB...':<50}")
    load_id = generate_load_id()
    for neighbours_batch in get_list_of_asn_neighbours_for_country(
        iso2, dates, BATCH_SIZE
    ):
        if OZI_STORAGE_BACKEND in ("postgres", "both"):
            insert_country_asn_neighbours_to_db(iso2, neighbours_batch)
        if OZI_STORAGE_BACKEND in ("lake", "both"):
            insert_country_asn_neighbours_to_lake(iso2, neighbours_batch, load_id=load_id)


def etl_load_asn_neighbours_async(iso2, dates):
    print(f"{'Getting data from the API (async) and storing to DB...':<50}")
    from etl_jobs_async import get_list_of_asn_neighbours_for_country_async
    from extract_from_ripe_api_async import aclose_client

    load_id = generate_load_id()

    async def _run():
        try:
            async for neighbours_batch in get_list_of_asn_neighbours_for_country_async(
                iso2, dates, BATCH_SIZE
            ):
                if OZI_STORAGE_BACKEND in ("postgres", "both"):
                    insert_country_asn_neighbours_to_db(iso2, neighbours_batch)
                if OZI_STORAGE_BACKEND in ("lake", "both"):
                    insert_country_asn_neighbours_to_lake(iso2, neighbours_batch, load_id=load_id)
        finally:
            await aclose_client()

    asyncio.run(_run())


def etl_load_traffic(iso2, dates, save_to_file=False):
    traffic = get_traffic_for_country(iso2, CLOUDFLARE_API_TOKEN)
    if traffic:
        load_id = generate_load_id()
        if OZI_STORAGE_BACKEND in ("postgres", "both"):
            insert_traffic_for_country_to_db(iso2, traffic, save_sql_to_file=save_to_file)
        if OZI_STORAGE_BACKEND in ("lake", "both"):
            insert_traffic_for_country_to_lake(iso2, traffic, load_id=load_id)


def etl_load_internet_quality(iso2, dates, save_to_file=False):
    internet_quality = get_internet_quality_for_country(iso2, CLOUDFLARE_API_TOKEN)
    if internet_quality:
        load_id = generate_load_id()
        if OZI_STORAGE_BACKEND in ("postgres", "both"):
            insert_internet_quality_for_country_to_db(
                iso2, internet_quality, save_sql_to_file=save_to_file
            )
        if OZI_STORAGE_BACKEND in ("lake", "both"):
            insert_internet_quality_for_country_to_lake(
                iso2, internet_quality, load_id=load_id
            )


if __name__ == "__main__":
    main()
