import argparse
from load_to_database import *
from country_lists import *
from etl_jobs import get_internet_quality_for_country
from datetime import datetime, timedelta

from etl_jobs import (
    get_list_of_asns_for_country,
    get_stats_for_country,
    get_list_of_asn_neighbours_for_country,
    get_traffic_for_country,
)

CLOUDFLARE_API_TOKEN = os.getenv("OZI_CLOUDFLARE_API_TOKEN")

RESOLUTION_DICT = {"D": "daily", "W": "weekly", "M": "Monthly"}


def main():
    parser = argparse.ArgumentParser(
        description="ETL script for OZI Dashboard project."
    )
    parser.add_argument(
        "-t",
        "--task",
        required=True,
        help="ETL task to perform (e.g., 'asns', 'stats_1d').",
    )
    parser.add_argument(
        "-c",
        "--countries",
        required=True,
        nargs="+",
        help="List of country ISO2 codes (e.g., 'US', 'DE').",
    )
    parser.add_argument(
        "-df", "--date-from", required=True, help="Start date in YYYY-MM-DD format."
    )
    parser.add_argument(
        "-dt", "--date-to", required=True, help="End date in YYYY-MM-DD format."
    )
    parser.add_argument(
        "-dr",
        "--date-resolution",
        required=True,
        help="Required resolution: D - Daily, W - Weekly, M - Monthly",
    )
    parser.add_argument(
        "--save-to-file",
        action="store_true",
        help="Save generated SQL to file (default: False)",
    )

    args = parser.parse_args()
    task = args.task
    countries = args.countries
    resolution = args.date_resolution
    try:
        date_from = datetime.strptime(args.date_from, "%Y-%m-%d")
        date_to = datetime.strptime(args.date_to, "%Y-%m-%d")
    except ValueError:
        print("Error: Dates must be in YYYY-MM-DD format.")
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
        print(f"Error: Unknown task '{task}'.")
        return

    if resolution not in RESOLUTION_DICT:
        print(f"Error: Unknown resolution '{resolution}'.")
        return

    dates = generate_dates(date_from, date_to, resolution)

    for iso2 in countries:
        date_from_formatted = date_from.strftime("%Y-%m-%d")
        date_to_formatted = date_to.strftime("%Y-%m-%d")
        print(f"{'Started:':<12} {task}")
        print(f"{'At:':<12} {datetime.now()}")
        print(f"{'Country:':<12} {ALL_COUNTRIES[iso2]}")
        print(f"{'Date From:':<12} {date_from_formatted}")
        print(f"{'Date To:':<12} {date_to_formatted}")
        print(f"{'Resolution:':<12} {RESOLUTION_DICT[resolution]}")

        if task in ["STATS_5M", "TRAFFIC", "INTERNET_QUALITY"]:
            task_map[task](iso2, dates.copy(), save_to_file=args.save_to_file)
        else:
            task_map[task](iso2, dates.copy())

        # task_map[task](iso2, generate_dates(date_from, date_to, resolution))
        # task_map[task](iso2, date_from, date_to, resolution)

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
    for asns_batch in get_list_of_asns_for_country(iso2, dates, BATCH_SIZE):
        insert_country_asns_to_db(iso2, asns_batch)


def etl_load_stats_1d(iso2, dates):
    for date in dates:
        stats = get_stats_for_country(iso2, date, date, "1d")
        if stats:
            insert_country_stats_to_db(iso2, "1d", stats, save_sql_to_file=True)


def etl_load_stats_5m(iso2, dates, save_to_file=False):
    years = sorted(set(date.year for date in dates))
    for year in years:
        date_from = datetime(year, 1, 1)
        date_to = datetime(year + 1, 1, 1)
        stats = get_stats_for_country(iso2, date_from, date_to, "5m")
        if stats:
            insert_country_stats_to_db(iso2, "5m", stats, save_sql_to_file=save_to_file)


def etl_load_asn_neighbours(iso2, dates):
    print(f"{'Getting data from the API and storing to DB...':<50}")
    for neighbours_batch in get_list_of_asn_neighbours_for_country(
        iso2, dates, BATCH_SIZE
    ):
        insert_country_asn_neighbours_to_db(iso2, neighbours_batch)


def etl_load_traffic(iso2, dates, save_to_file=False):
    traffic = get_traffic_for_country(iso2, CLOUDFLARE_API_TOKEN)
    if traffic:
        insert_traffic_for_country_to_db(iso2, traffic, save_sql_to_file=save_to_file)


def etl_load_internet_quality(iso2, dates, save_to_file=False):
    internet_quality = get_internet_quality_for_country(iso2, CLOUDFLARE_API_TOKEN)
    if internet_quality:
        insert_internet_quality_for_country_to_db(
            iso2, internet_quality, save_sql_to_file=save_to_file
        )


if __name__ == "__main__":
    main()
