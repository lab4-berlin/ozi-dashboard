"""
This module orchestrates ETL jobs by fetching data using API extraction functions
and preparing it in a format suitable for database loading or further processing.
It includes utilities for displaying progress during long operations and for
batching data retrieved from APIs.
"""

from .load_to_database import (
    BATCH_SIZE,
)  # BATCH_SIZE here is likely for default batching in db loading, not directly used in this module's functions' parameters.
from .extract_from_cloudflare_api import (
    get_cloudflare_traffic_for_country,
    get_cloudflare_internet_quality_for_country,
)
from .extract_from_ripe_api import (
    get_country_asns,
    get_country_resource_stats,
    get_asn_neighbours,
)
import datetime

BAR_LENGTH = 50  # Defines the visual length of the progress bar in characters.


def display_progress(
    processed,
    total,
    processed_until_date,
    received_from_api,
    stored_to_database,
    custom_msg="",
):
    """
    Displays a progress bar and status information to the console.

    Args:
        processed (int): Number of items/tasks already processed.
        total (int): Total number of items/tasks to process.
        processed_until_date (datetime.datetime): The date until which processing has been completed (often the current date being processed).
        received_from_api (int): Count of records received from an API.
        stored_to_database (int): Count of records successfully stored in the database.
        custom_msg (str, optional): A custom message string to display alongside progress. Defaults to ''.

    Prints:
        A line to sys.stdout representing the progress, including a visual bar,
        percentage, date, API received count, DB stored count, and custom message.
        Uses carriage return `\\r` to update the line in place.
    """
    date_str = processed_until_date.strftime("%Y-%m-%d %H:%M:%S")
    progress = 0.0 if total == 0 else float(processed) / total
    filled_length = int(BAR_LENGTH * progress)

    _bar = "|" + "█" * filled_length
    # Logic to embed date within the bar if space allows
    if (BAR_LENGTH - filled_length - 2) >= len(date_str):
        _bar += (
            "-"
            + date_str
            + "-" * (BAR_LENGTH - filled_length - len(date_str) - 2)
            + "| "
        )
    else:
        _bar += "-" * (BAR_LENGTH - filled_length - 1) + "| "
        _bar += date_str  # Append date if it doesn't fit inside

    padding = " " * 12
    print(
        f"\r{padding}{_bar} Received: {received_from_api}, Stored: {stored_to_database}   {custom_msg} {progress:.1%}",
        end=" ",
        flush=True,
    )


def get_list_of_asns_for_country(country_iso2, dates, batch_size, verbose=True):
    """
    Fetches and generates batches of ASN (Autonomous System Number) data for a country over a list of dates.

    It calls the RIPE API for each date to get ASNs, parses the response,
    and yields the data in batches.

    Args:
        country_iso2 (str): The ISO2 code of the country.
        dates (list[datetime.datetime]): A list of dates for which to fetch ASN data.
                                         This list will be processed, and it's recommended
                                         to pass a copy if the original list needs to be preserved,
                                         as the function iterates based on this list's current state.
        batch_size (int): The maximum number of ASN records to include in each yielded batch.
        verbose (bool, optional): If True, prints progress updates to the console. Defaults to True.

    Yields:
        list[dict]: A batch of ASN data. Each dictionary in the list represents one ASN and has the format:
                    {'asn': str,        # ASN identifier, e.g., "AS123"
                     'date': str,       # Date of the record in "YYYY-MM-DD" format
                     'is_routed': bool} # True if the ASN is routed, False otherwise
    """
    total_number_of_dates = len(dates)
    asns_batch = []
    received_from_api = 0  # Tracks items collected from API before forming a full yieldable batch for this specific generator

    if verbose and dates:
        display_progress(
            0,
            total_number_of_dates,
            dates[0],
            0,
            0,
            custom_msg=f"Starting ASNs for {country_iso2}",
        )

    processed_dates_count = 0
    dates_to_process = list(dates)  # Iterate over a copy

    for date in dates_to_process:
        processed_dates_count += 1
        d = get_country_asns(country_iso2, date)  # API call

        if (
            d
            and d.get("data")
            and d["data"].get("countries")
            and d["data"]["countries"][0]
        ):
            country_data = d["data"]["countries"][0]
            routed_asns_str = country_data.get("routed", "")
            non_routed_asns_str = country_data.get("non_routed", "")

            routed_list = []
            if routed_asns_str:
                processed_routed_asns_str = routed_asns_str.strip("{}")
                if processed_routed_asns_str:
                    routed_list = [
                        item.split("(")[1].split(")")[0]
                        for item in processed_routed_asns_str.split(", ")
                        if item.startswith("AsnSingle")
                    ]

            non_routed_list = []
            if non_routed_asns_str:
                processed_non_routed_asns_str = non_routed_asns_str.strip("{}")
                if processed_non_routed_asns_str:
                    non_routed_list = [
                        item.split("(")[1].split(")")[0]
                        for item in processed_non_routed_asns_str.split(", ")
                        if item.startswith("AsnSingle")
                    ]

            all_parsed_for_date = []
            for asn_val in routed_list:
                all_parsed_for_date.append(
                    {
                        "asn": asn_val,
                        "date": date.strftime("%Y-%m-%d"),
                        "is_routed": True,
                    }
                )
            for asn_val in non_routed_list:
                all_parsed_for_date.append(
                    {
                        "asn": asn_val,
                        "date": date.strftime("%Y-%m-%d"),
                        "is_routed": False,
                    }
                )

            for item in all_parsed_for_date:
                asns_batch.append(item)
                if len(asns_batch) == batch_size:
                    yield list(asns_batch)  # Yield a copy
                    received_from_api += len(asns_batch)
                    asns_batch = []

            if verbose:  # Progress for current date processing
                # 'received_from_api' here reflects fully yielded batches.
                # 'len(asns_batch)' is the current partial batch from this date.
                display_progress(
                    processed_dates_count,
                    total_number_of_dates,
                    date,
                    received_from_api + len(asns_batch),
                    received_from_api,
                    custom_msg=f"ASNs for {country_iso2}",
                )
        else:
            if verbose:  # API call failed or no data for this date
                display_progress(
                    processed_dates_count,
                    total_number_of_dates,
                    date,
                    received_from_api,
                    received_from_api,
                    custom_msg=f"No ASN data for {country_iso2} on {date.strftime('%Y-%m-%d')}",
                )

    if asns_batch:  # Yield any remaining items from the last date
        yield list(asns_batch)
        received_from_api += len(asns_batch)

    if verbose:  # Final summary display
        final_progress_date = (
            dates_to_process[-1]
            if dates_to_process and processed_dates_count > 0
            else datetime.datetime.now()
        )
        # 'stored_to_database' for display_progress is ambiguous here, using 'received_from_api' as a proxy for items this function produced.
        display_progress(
            total_number_of_dates,
            total_number_of_dates,
            final_progress_date,
            received_from_api,
            received_from_api,
            custom_msg=f"Finished ASNs for {country_iso2}",
        )


def get_stats_for_country(country_iso2, date_from, date_to, resolution):
    """
    Retrieves historical resource statistics for a country for a given period and resolution.

    Calls the RIPE API to get these statistics.

    Args:
        country_iso2 (str): The ISO2 code of the country.
        date_from (str): The start date for the statistics query (e.g., "YYYY-MM-DD").
        date_to (str): The end date for the statistics query (e.g., "YYYY-MM-DD").
        resolution (str): The time resolution for the statistics (e.g., "1d" for daily).

    Returns:
        list[dict] or None: A list of dictionaries, where each dictionary is a statistics record
                            from the RIPE API. Returns an empty list if the API provides an empty
                            list of stats. Returns None if the API call fails or returns no data structure.
                            The structure of the dictionaries within the list depends on the RIPE API response
                            for 'country-resource-stats'.
    """
    print(
        f"    Getting historical stats {country_iso2}, {resolution}, {date_from}, {date_to}",
        end=" ... ",
    )
    # save_mode='file' is hardcoded here, consider making it a parameter if flexibility is needed.
    d = get_country_resource_stats(
        country_iso2, resolution, date_from, date_to, save_mode="file"
    )
    if d and d.get("data") and d["data"].get("stats") is not None:
        stats = d["data"]["stats"]
        if stats:
            print(f"    {len(stats)} records found")
        else:
            print("    0 records found (empty list).")
        return stats
    else:
        print("    No stats data found or API error.")
        return None


def get_list_of_asn_neighbours_for_country(
    country_iso2, dates, batch_size_neighbours, verbose=True
):
    """
    Fetches and generates batches of ASN neighbour data for all ASNs in a country over a list of dates.

    This function first retrieves all ASNs for the given country and dates (using
    `get_list_of_asns_for_country`), then for each ASN, it fetches its neighbours
    from the RIPE API and yields this data in batches.

    Args:
        country_iso2 (str): The ISO2 code of the country.
        dates (list[datetime.datetime]): A list of dates for which to fetch data.
        batch_size_neighbours (int): The max number of neighbour records in each yielded batch.
        verbose (bool, optional): If True, prints progress. Defaults to True.

    Yields:
        list[dict]: A batch of ASN neighbour data. Each dictionary structure is based on the
                    RIPE 'asn-neighbours' API response, with additional keys:
                    - 'asn_req' (str): The ASN for which neighbours were requested.
                    - 'date' (str): Date of the record in "YYYY-MM-DD" format.
                    Other keys typically include 'type', 'power', 'v4_peers', 'v6_peers', etc.
    """
    total_number_of_dates = len(dates)
    neighbours_batch = []
    total_neighbours_from_api = (
        0  # Tracks items collected from API before forming a full yieldable batch
    )

    if verbose and dates:
        display_progress(
            0,
            total_number_of_dates,
            dates[0],
            0,
            0,
            custom_msg=f"Starting ASN Neighbours for {country_iso2}",
        )

    processed_dates_count = 0
    dates_to_process = list(dates)

    for date_obj in dates_to_process:
        processed_dates_count += 1
        # Defines batch size for fetching ASNs internally, distinct from batch_size_neighbours for yielding.
        asn_fetch_batch_size = 100  # Could be BATCH_SIZE from .load_to_database if that's the intended shared constant.

        for asn_list_batch in get_list_of_asns_for_country(
            country_iso2, [date_obj], batch_size=asn_fetch_batch_size, verbose=False
        ):
            asns_processed_for_date = 0
            total_asns_for_date = len(asn_list_batch)
            for item in asn_list_batch:
                asn = item["asn"]
                asns_processed_for_date += 1
                if verbose:
                    progress_msg = f"ASN Neighbours for {country_iso2} {date_obj.strftime('%Y-%m-%d')}: ASN {asns_processed_for_date}/{total_asns_for_date} (AS{asn})"
                    display_progress(
                        processed_dates_count - 1,
                        total_number_of_dates,
                        date_obj,
                        total_neighbours_from_api + len(neighbours_batch),
                        total_neighbours_from_api,
                        custom_msg=progress_msg,
                    )

                d = get_asn_neighbours(asn, date_obj)
                if d and d.get("data") and d["data"].get("neighbours"):
                    for row in d["data"]["neighbours"]:
                        row["asn_req"] = asn
                        row["date"] = date_obj.strftime("%Y-%m-%d")
                        neighbours_batch.append(row)

                if len(neighbours_batch) >= batch_size_neighbours:
                    yield list(neighbours_batch)  # Yield a copy
                    total_neighbours_from_api += len(neighbours_batch)
                    neighbours_batch = []

        if verbose:  # Progress after all ASNs for a specific date_obj are processed
            display_progress(
                processed_dates_count,
                total_number_of_dates,
                date_obj,
                total_neighbours_from_api + len(neighbours_batch),
                total_neighbours_from_api,
                custom_msg=f"ASN Neighbours for {country_iso2} {date_obj.strftime('%Y-%m-%d')} done.",
            )

    if neighbours_batch:  # Yield any remaining neighbour items
        yield list(neighbours_batch)
        total_neighbours_from_api += len(neighbours_batch)

    if verbose:  # Final summary display
        final_progress_date = (
            dates_to_process[-1]
            if dates_to_process and processed_dates_count > 0
            else datetime.datetime.now()
        )
        display_progress(
            total_number_of_dates,
            total_number_of_dates,
            final_progress_date,
            total_neighbours_from_api,
            total_neighbours_from_api,
            custom_msg=f"Finished ASN Neighbours for {country_iso2}",
        )


def get_traffic_for_country(country_iso2, token):
    """
    Retrieves network traffic data for a country using the Cloudflare API.

    Args:
        country_iso2 (str): The ISO2 code of the country.
        token (str): The Cloudflare API token.

    Returns:
        dict or None: A dictionary containing the traffic data if successful (structure depends on
                      Cloudflare API, typically includes 'timestamps' and 'values' lists).
                      Returns None if the API call fails, data is missing, or an error occurs.
    """
    print(f"Getting traffic for {country_iso2}", end=" ... ")
    # copy_to_file=True is hardcoded here. Consider making it a parameter.
    d = get_cloudflare_traffic_for_country(country_iso2, token, copy_to_file=True)
    if d and d.get("result") and d["result"].get("main"):
        traffic = d["result"]["main"]
        if "timestamps" in traffic:  # Basic check for expected data structure
            print(f"{len(traffic['timestamps'])} records found")
        else:
            print("Timestamps missing in traffic data.")
        return traffic
    else:
        print("No traffic data found or API error.")
        return None


def get_internet_quality_for_country(country_iso2, token):
    """
    Retrieves internet quality data (e.g., bandwidth percentiles) for a country using the Cloudflare API.

    Args:
        country_iso2 (str): The ISO2 code of the country.
        token (str): The Cloudflare API token.

    Returns:
        dict or None: A dictionary containing internet quality data if successful (structure
                      depends on Cloudflare API, typically includes 'timestamps' and percentile lists
                      like 'p75', 'p50', 'p25').
                      Returns None if the API call fails, data is missing, or an error occurs.
    """
    print(f"    Getting internet quality for {country_iso2}", end=" ... ")
    # copy_to_file=True is hardcoded here. Consider making it a parameter.
    d = get_cloudflare_internet_quality_for_country(
        country_iso2, token, copy_to_file=True
    )
    if d and d.get("result") and d["result"].get("main"):
        internet_quality = d["result"]["main"]
        if "timestamps" in internet_quality:  # Basic check for expected data structure
            print(f"{len(internet_quality['timestamps'])} records found")
        else:
            print("Timestamps missing in internet quality data.")
        return internet_quality
    else:
        print("No internet quality data found or API error.")
        return None
