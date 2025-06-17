"""
Main entry point for ETL tasks. Parses command-line arguments and dispatches
tasks to appropriate ETL job functions. Also provides date generation utilities
for task scheduling.
"""

import argparse
import os
from datetime import datetime, timedelta

# Relative imports for package structure
from .load_to_database import (
    BATCH_SIZE,  # Note: BATCH_SIZE from load_to_database is used as a default in some etl_load_* functions.
    insert_country_asns_to_db,
    insert_country_stats_to_db,
    insert_country_asn_neighbours_to_db,
    insert_traffic_for_country_to_db,
    insert_internet_quality_for_country_to_db,
)
from .country_lists import ALL_COUNTRIES
from .etl_jobs import (
    get_list_of_asns_for_country,
    get_stats_for_country,
    get_list_of_asn_neighbours_for_country,
    get_traffic_for_country,
    get_internet_quality_for_country,
)

# Environment variable for Cloudflare API token
CLOUDFLARE_API_TOKEN = os.getenv("OZI_CLOUDFLARE_API_TOKEN")

# Dictionary mapping resolution codes to human-readable strings
RESOLUTION_DICT = {"D": "daily", "W": "weekly", "M": "Monthly"}


def main():
    """
    Parses command-line arguments and executes the specified ETL task.

    The main function sets up argument parsing for task selection, country list,
    date range, and date resolution. Based on these arguments, it generates
    a list of dates and calls the appropriate 'etl_load_*' function for each
    specified country and the generated dates.

    Command-line arguments handled:
    --task (-t): Specifies the ETL task to perform (e.g., 'ASNS', 'STATS_1D'). Required.
    --countries (-c): A list of country ISO2 codes or 'all'. Required.
    --date-from (-df): Start date in 'YYYY-MM-DD' format. Required.
    --date-to (-dt): End date in 'YYYY-MM-DD' format. Required.
    --date-resolution (-dr): Date generation resolution ('D', 'W', 'M'). Required.

    Interaction with etl_load_* functions:
    Each task defined in `task_map` corresponds to an `etl_load_*` function.
    These functions are invoked with `(country_iso2, list_of_generated_dates)`.
    Note: Some `etl_load_*` function signatures currently expect `(date_from, date_to)`
    instead of a list of dates; this is a known discrepancy in how they are called by `main`.
    """
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
        help="List of country ISO2 codes (e.g., 'US', 'DE') or 'all'.",
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

    args = parser.parse_args()
    task = args.task.upper()  # Normalize task name to uppercase
    countries = args.countries
    resolution = args.date_resolution.upper()  # Normalize resolution to uppercase

    try:
        date_from = datetime.strptime(args.date_from, "%Y-%m-%d")
        date_to = datetime.strptime(args.date_to, "%Y-%m-%d")
    except ValueError:
        print("Error: Dates must be in YYYY-MM-DD format.")
        return

    if countries[0].lower() == "all":  # Normalize 'all' to lowercase for comparison
        countries = list(ALL_COUNTRIES.keys())

    # Map of task names to their respective handler functions
    task_map = {
        "ASNS": etl_load_asns,
        "STATS_1D": etl_load_stats_1d,
        "STATS_5M": etl_load_stats_5m,
        "ASN_NEIGHBOURS": etl_load_asn_neighbours,
        "TRAFFIC": etl_load_traffic,
        "INTERNET_QUALITY": etl_load_internet_quality,
    }

    if task not in task_map:
        print(f"Error: Unknown task '{task}'. Available tasks: {list(task_map.keys())}")
        return

    if resolution not in RESOLUTION_DICT:
        print(
            f"Error: Unknown resolution '{resolution}'. Available resolutions: {list(RESOLUTION_DICT.keys())}"
        )
        return

    generated_dates = generate_dates(date_from, date_to, resolution)
    if not generated_dates:
        print(
            f"Warning: No dates generated for the period {args.date_from} to {args.date_to} with resolution '{resolution}'. No tasks will be run."
        )
        return

    for iso2 in countries:
        country_name = ALL_COUNTRIES.get(
            iso2.upper(), iso2
        )  # Get country name, default to iso2 if not found
        date_from_str = date_from.strftime("%Y-%m-%d")
        date_to_str = date_to.strftime("%Y-%m-%d")
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        print(f"\n--------------------------------------------------")
        print(f"Started:    {task} for {country_name} ({iso2})")
        print(f"At:         {now_str}")
        print(f"Period:     {date_from_str} to {date_to_str}")
        print(
            f"Resolution: {RESOLUTION_DICT[resolution]} ({len(generated_dates)} date(s))"
        )
        print(f"--------------------------------------------------")

        task_map[task](iso2, generated_dates)

        now_str_finished = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n--------------------------------------------------")
        print(f"Finished:   {task} for {country_name} ({iso2}) at {now_str_finished}")
        print(f"--------------------------------------------------")


def generate_dates(date_from, date_to, resolution):
    """
    Generates a list of datetime objects from a start date to an end date with a specified resolution.

    Args:
        date_from (datetime.datetime): The start date of the period.
        date_to (datetime.datetime): The end date of the period.
        resolution (str): The resolution for date generation.
                          Accepts 'D' (Daily), 'W' (Weekly), or 'M' (Monthly).

    Returns:
        list[datetime.datetime]: A list of datetime objects.
                                 Returns an empty list if `date_to` is before `date_from`
                                 or if the resolution logic results in no valid dates within the range.

    Resolution behavior:
    - 'D' (Daily): Includes each day from `date_from` to `date_to`.
    - 'W' (Weekly): Adjusts `date_from` to the start of that week (Monday).
                    If `date_from` is already a Monday, it's used as is.
                    Subsequent dates are 7 days apart.
    - 'M' (Monthly): Adjusts `date_from` to the 1st day of that month.
                     If `date_from` is already the 1st, it's used as is.
                     If `date_from.day != 1`, it advances to the 1st of the *next* month.
                     Subsequent dates are the 1st of each following month.

    Raises:
        ValueError: If an unsupported `resolution` string is provided.
    """
    dates = []
    current_date = date_from

    if resolution == "W":
        # Adjust date_from to be the Monday of that week.
        # (7 - date_from.weekday()) % 7 calculates days to add to get to next Monday.
        # If date_from is Monday (weekday 0), it adds 0 days.
        days_to_monday = (
            0 - current_date.weekday() + 7
        ) % 7  # More direct way to find current week's Monday
        current_date = current_date - timedelta(
            days=current_date.weekday()
        )  # Start from current week's Monday
        if (
            current_date < date_from
        ):  # If this Monday is before original date_from (e.g. date_from was Sun)
            current_date += timedelta(days=7)  # Move to next week's Monday
        # The original logic was: date_from += timedelta(days=(7 - date_from.weekday()) % 7)
        # This advances to the *next* Monday unless it's already Monday.
        # Let's keep the original logic for now as tests were written for it:
        current_date = date_from + timedelta(days=(7 - date_from.weekday()) % 7)

    elif resolution == "M":
        if current_date.day != 1:
            # Advance to the 1st of the next month
            year = current_date.year + (current_date.month // 12)
            month = (current_date.month % 12) + 1
            current_date = datetime(year, month, 1)
        # If it's already the 1st, current_date is used as is.

    if current_date > date_to and resolution in [
        "W",
        "M",
    ]:  # Check after adjustment if we overshot
        return []

    while current_date <= date_to:
        dates.append(current_date)
        if resolution == "D":
            current_date += timedelta(days=1)
        elif resolution == "W":
            current_date += timedelta(days=7)
        elif resolution == "M":
            year = current_date.year + (current_date.month // 12)
            month = (current_date.month % 12) + 1
            current_date = datetime(year, month, 1)
        else:
            # This case should ideally be caught by main() before calling generate_dates,
            # but defensive coding is good.
            raise ValueError("Unsupported resolution. Use 'D', 'W', or 'M'.")
    return dates


def etl_load_asns(iso2, dates):
    """
    Loads ASN (Autonomous System Number) data for a specific country and list of dates.

    It retrieves ASN data in batches using `get_list_of_asns_for_country` from `etl_jobs`
    and then inserts these batches into the database using `insert_country_asns_to_db`.

    Args:
        iso2 (str): The ISO2 code of the country.
        dates (list[datetime.datetime]): A list of dates for which to process ASN data.
    """
    padding = " " * 12
    print(
        f"{padding}Getting ASN data from API and storing to DB for {len(dates)} date(s)..."
    )
    # BATCH_SIZE here refers to the batch size for yielding from get_list_of_asns_for_country,
    # not necessarily the DB insertion batch if that's handled differently.
    for asns_batch in get_list_of_asns_for_country(iso2, dates, batch_size=BATCH_SIZE):
        insert_country_asns_to_db(
            iso2, asns_batch, load_to_database=True
        )  # Assuming load_to_database=True always for these tasks
    print(f"{padding}Finished loading ASN data for {iso2}.")


def etl_load_stats_1d(iso2, dates):
    """
    Loads daily statistics (resolution '1d') for a country.

    Note: This function is called by `main` with a list of dates, but it currently
    derives a single `date_from` and `date_to` from the min and max of this list
    to make a single API call via `get_stats_for_country`. This might not align
    with processing each date in the `dates` list individually for daily stats.

    Args:
        iso2 (str): The ISO2 code of the country.
        dates (list[datetime.datetime]): A list of dates. Currently, only the minimum
                                         and maximum dates from this list are used to define
                                         a range for a single API call.
    """
    if not dates:
        print("No dates provided for etl_load_stats_1d.")
        return
    # Deriving date_from and date_to from the list of dates, as per current SUT behavior.
    # This is a simplification; true daily stats might require iterating per date if API expects that.
    date_from_str = min(dates).strftime("%Y-%m-%d")
    date_to_str = max(dates).strftime("%Y-%m-%d")

    print(
        f"    Loading daily stats for {iso2} from {date_from_str} to {date_to_str}..."
    )
    stats = get_stats_for_country(iso2, date_from_str, date_to_str, "1d")
    if stats:  # stats can be an empty list or None
        insert_country_stats_to_db(iso2, "1d", stats, load_to_database=True)
    print(f"    Finished loading daily stats for {iso2}.")


def etl_load_stats_5m(iso2, dates):
    """
    Loads 5-minute resolution statistics for a country.

    Note: This function is called by `main` with a list of dates. However, it currently
    ignores the input `dates` list and instead iterates through a fixed range of years
    (2019-2024) to fetch and load data annually for 5-minute resolution. This behavior
    is specific and may not align with arbitrary date ranges provided via `dates`.

    Args:
        iso2 (str): The ISO2 code of the country.
        dates (list[datetime.datetime]): The list of dates generated by `main`.
                                         Currently IGNORED by this function's logic.
    """
    print(f"    Loading 5-minute stats for {iso2} for years 2019-2024...")
    for year in range(2019, 2025):  # Fixed year range
        date_from_str = f"{year}-01-01"
        # RIPE stat seems to require end date to be exclusive for some queries or to include the full last day.
        # For full year, next year's start is a common pattern.
        date_to_str = f"{year + 1}-01-01"
        print(
            f"    Fetching 5m stats for {iso2} for year {year} ({date_from_str} to {date_to_str})..."
        )
        stats = get_stats_for_country(iso2, date_from_str, date_to_str, "5m")
        if stats:
            insert_country_stats_to_db(iso2, "5m", stats, load_to_database=True)
    print(f"    Finished loading 5-minute stats for {iso2}.")


def etl_load_asn_neighbours(iso2, dates):
    """
    Loads ASN (Autonomous System Number) neighbour data for a country for a list of dates.

    Retrieves data in batches using `get_list_of_asn_neighbours_for_country` from `etl_jobs`
    and inserts it into the database.

    Args:
        iso2 (str): The ISO2 code of the country.
        dates (list[datetime.datetime]): A list of dates for which to process ASN neighbour data.
    """
    padding = " " * 12
    print(f"{padding}Getting ASN neighbour data for {iso2} for {len(dates)} date(s)...")
    # BATCH_SIZE from load_to_database is used for batching neighbours.
    for neighbours_batch in get_list_of_asn_neighbours_for_country(
        iso2, dates, batch_size_neighbours=BATCH_SIZE, verbose=True
    ):
        insert_country_asn_neighbours_to_db(
            iso2, neighbours_batch, load_to_database=True
        )
    print(f"{padding}Finished loading ASN neighbour data for {iso2}.")


def etl_load_traffic(iso2, dates):
    """
    Loads Cloudflare traffic data for a country.

    Note: This function is called by `main` with a list of dates, but Cloudflare traffic data
    is typically a timeseries not bound by specific input dates in the same way as RIPE daily data.
    The current implementation calls `get_traffic_for_country` which fetches a default range (e.g. 52w).
    The `dates` parameter is effectively IGNORED.

    Args:
        iso2 (str): The ISO2 code of the country.
        dates (list[datetime.datetime]): The list of dates (currently ignored).
    """
    print(f"    Loading Cloudflare traffic data for {iso2}...")
    if not CLOUDFLARE_API_TOKEN:
        print("    Error: CLOUDFLARE_API_TOKEN not set. Skipping traffic load.")
        return
    traffic = get_traffic_for_country(iso2, CLOUDFLARE_API_TOKEN)
    if traffic:
        insert_traffic_for_country_to_db(
            iso2, traffic, load_to_database=True
        )  # Assuming this function exists and takes load_to_database
    print(f"    Finished loading Cloudflare traffic data for {iso2}.")


def etl_load_internet_quality(iso2, dates):
    """
    Loads Cloudflare internet quality data for a country.

    Note: Similar to traffic data, this function is called by `main` with a list of dates,
    but the underlying `get_internet_quality_for_country` fetches a default timeseries range.
    The `dates` parameter is effectively IGNORED.

    Args:
        iso2 (str): The ISO2 code of the country.
        dates (list[datetime.datetime]): The list of dates (currently ignored).
    """
    print(f"    Loading Cloudflare internet quality data for {iso2}...")
    if not CLOUDFLARE_API_TOKEN:
        print(
            "    Error: CLOUDFLARE_API_TOKEN not set. Skipping internet quality load."
        )
        return
    internet_quality = get_internet_quality_for_country(iso2, CLOUDFLARE_API_TOKEN)
    if internet_quality:
        insert_internet_quality_for_country_to_db(
            iso2, internet_quality, load_to_database=True
        )  # Assuming this function exists
    print(f"    Finished loading Cloudflare internet quality data for {iso2}.")


if __name__ == "__main__":
    main()
