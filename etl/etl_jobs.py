from load_to_database import BATCH_SIZE
from extract_from_cloudflare_api import (
    get_cloudflare_traffic_for_country,
    get_cloudflare_internet_quality_for_country,
)
from extract_from_ripe_api import (
    get_country_asns,
    get_country_resource_stats,
    get_asn_neighbours,
)

BAR_LENGTH = 50


def display_progress(
    processed,
    total,
    processed_until_date,
    received_from_api,
    stored_to_database,
    custom_msg="",
):
    date_str = processed_until_date.strftime("%Y-%m-%d")

    progress = float(processed) / total
    filled_length = int(BAR_LENGTH * progress)
    bar = "|" + "█" * filled_length
    if BAR_LENGTH - filled_length - 2 > len(date_str):
        bar += f"-{date_str}{'-' * (BAR_LENGTH - filled_length - len(date_str) - 2)}| "
    else:
        bar += f"{'-' * (BAR_LENGTH - filled_length)}| {date_str}"

    print(
        f"\r{' ' * 12}{bar} Received: {received_from_api}, Stored: {stored_to_database}   {custom_msg}",
        end=" ",
        flush=True,
    )


def get_list_of_asns_for_country(country_iso2, dates, batch_size, verbose=True):
    total_number_of_dates = len(dates)
    asns_batch = []
    received_from_api = 0

    if verbose:
        display_progress(0, total_number_of_dates, dates[0], 0, 0)

    while dates:
        date = dates.pop(0)
        d = get_country_asns(country_iso2, date, save_mode=None)

        if d["data"]:
            routed_asns = d["data"]["countries"][0]["routed"]
            non_routed_asns = d["data"]["countries"][0]["non_routed"]
            routed_list = [
                item.split("(")[1].split(")")[0]
                for item in routed_asns.strip("{}").split(", ")
                if item.startswith("AsnSingle")
            ]
            non_routed_list = [
                item.split("(")[1].split(")")[0]
                for item in non_routed_asns.strip("{}").split(", ")
                if item.startswith("AsnSingle")
            ]

            for asn in routed_list:
                asns_batch.append(
                    {"asn": asn, "date": date.strftime("%Y-%m-%d"), "is_routed": True}
                )
            for asn in non_routed_list:
                asns_batch.append(
                    {"asn": asn, "date": date.strftime("%Y-%m-%d"), "is_routed": False}
                )

            if verbose:
                display_progress(
                    total_number_of_dates - len(dates) - 1,
                    total_number_of_dates,
                    date,
                    received_from_api + len(asns_batch),
                    received_from_api,
                )

            if len(asns_batch) >= batch_size:
                yield asns_batch
                received_from_api += len(asns_batch)
                asns_batch = []

    if asns_batch:
        yield asns_batch


def get_stats_for_country(country_iso2, date_from, date_to, resolution):
    print(
        f"    Getting historical stats {country_iso2}, {resolution}, {date_from}, {date_to}",
        end=" ... ",
    )
    d = get_country_resource_stats(
        country_iso2, resolution, date_from, save_mode="file"
    )
    if d:
        stats = d["data"].get("stats")
        print(f"    {len(stats)} records found")
        return stats


def get_asn_neighbour_counts_for_country(country_iso2, dates, verbose=True):
    """
    For each ASN in the country, fetch neighbours from RIPE API and compute
    total_neighbours, local_neighbours, foreign_neighbours.
    Local = neighbour ASN is in the same country; Foreign = neighbour is in another country.
    Yields batches of count records for loading.
    """
    total_number_of_dates = len(dates)
    count_batch = []
    processed_asns = 0

    if verbose:
        display_progress(0, total_number_of_dates, dates[0], 0, 0)

    while dates:
        date = dates.pop(0)
        # Collect ALL ASNs for this country/date first (needed for correct local/foreign classification)
        all_asns_for_date = []
        for asn_list in get_list_of_asns_for_country(
            country_iso2, [date], BATCH_SIZE, verbose=False
        ):
            all_asns_for_date.extend(asn_list)
        local_asns = {str(item["asn"]) for item in all_asns_for_date}

        for item in all_asns_for_date:
                asn = item["asn"]
                processed_asns += 1
                if verbose:
                    display_progress(
                        total_number_of_dates - len(dates),
                        total_number_of_dates,
                        date,
                        processed_asns,
                        processed_asns - len(count_batch),
                        f"    asn {asn}",
                    )

                d = get_asn_neighbours(asn, date)
                if not d or not d.get("data") or not d["data"].get("neighbours"):
                    continue

                total = 0
                local = 0
                foreign = 0

                for row in d["data"]["neighbours"]:
                    # Only count left/right neighbours (exclude uncertain, per existing views)
                    n_type = row.get("type") or row.get("position", "")
                    if n_type not in ("left", "right"):
                        continue

                    neighbour_asn = str(row.get("asn", "")).strip()
                    if not neighbour_asn:
                        continue

                    total += 1
                    if neighbour_asn in local_asns:
                        local += 1
                    else:
                        foreign += 1

                if total > 0:
                    count_batch.append(
                        {
                            "asn": int(asn) if str(asn).isdigit() else asn,
                            "country_iso2": country_iso2,
                            "date": date.strftime("%Y-%m-%d"),
                            "total_neighbours": total,
                            "local_neighbours": local,
                            "foreign_neighbours": foreign,
                        }
                    )

                if len(count_batch) >= BATCH_SIZE:
                    yield count_batch
                    count_batch = []

    if count_batch:
        yield count_batch


def get_traffic_for_country(country_iso2, token):
    print(f"Getting traffic for {country_iso2}", end=" ... ")
    d = get_cloudflare_traffic_for_country(country_iso2, token, copy_to_file=True)

    if not d or "result" not in d or "main" not in d["result"]:
        print(f"{'No traffic data found or invalid response.':<50}")
        return None
    else:
        traffic = d["result"]["main"]
        timestamps = traffic.get("timestamps", [])
        print(f"{len(timestamps)} records found")
        return traffic


def get_internet_quality_for_country(country_iso2, token):
    print(f"    Getting internet quality for {country_iso2}", end=" ... ")
    d = get_cloudflare_internet_quality_for_country(
        country_iso2, token, copy_to_file=True
    )

    if not d or "result" not in d or "main" not in d["result"]:
        print(f"{'No internet quality data found or invalid response.':<50}")
        return None
    else:
        internet_quality = d["result"]["main"]
        timestamps = internet_quality.get("timestamps", [])
        print(f"{len(timestamps)} records found")
        return internet_quality
