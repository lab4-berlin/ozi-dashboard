from etl.load_to_database import *
from etl.country_lists import *
from etl.etl_jobs import *
from datetime import datetime, timedelta
import argparse


CLOUDFLARE_API_TOKEN=os.getenv('OZI_CLOUDFLARE_API_TOKEN')

RESOLUTION_DICT = { 'D': 'daily', 'W': 'weekly', 'M': 'Monthly' }

def main():
    parser = argparse.ArgumentParser(description="ETL script for OZI Dashboard project.")
    parser.add_argument('-t', '--task', required=True, help="ETL task to perform (e.g., 'asns', 'stats_1d').")
    parser.add_argument('-c', '--countries', required=True, nargs='+', help="List of country ISO2 codes (e.g., 'US', 'DE').")
    parser.add_argument('-df', '--date-from', required=True, help="Start date in YYYY-MM-DD format.")
    parser.add_argument('-dt', '--date-to', required=True, help="End date in YYYY-MM-DD format.")
    parser.add_argument('-dr', '--date-resolution', required=True, help="Required resolution: D - Daily, W - Weekly, M - Monthly")

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

    if countries[0] == 'all':
        countries = list(ALL_COUNTRIES.keys())

    task_map = {
        "ASNS": etl_load_asns,
        "STATS_1D": etl_load_stats_1d,
        "STATS_5M": etl_load_stats_5m,
        "ASN_NEIGHBOURS": etl_load_asn_neighbours,
        "TRAFFIC": etl_load_traffic,
        "INTERNET_QUALITY": etl_load_internet_quality
    }

    if task not in task_map:
        print(f"Error: Unknown task '{task}'.")
        return

    if resolution not in RESOLUTION_DICT:
        print(f"Error: Unknown resolution '{resolution}'.")
        return

    for iso2 in countries:
        print(f"Started:    {task}")
        print(f"At:         {datetime.now()}")
        print(f"Country:    {ALL_COUNTRIES[iso2]}")
        print(f"Date From:  {date_from.strftime("%Y-%m-%d")}")
        print(f"Date To:    {date_to.strftime("%Y-%m-%d")}")
        print(f"Resolution: {RESOLUTION_DICT[resolution]}")

        # task_map[task](iso2, generate_dates(date_from, date_to, resolution))
        task_map[task](iso2, date_from, date_to)

        print(f"\nAt:         {datetime.now()}")
        print(f"Finished:   {task}")

def generate_dates(date_from, date_to, resolution):
    dates = []
    if resolution == 'W':
        date_from += timedelta(days=(7 - date_from.weekday()) % 7)
    elif resolution == 'M':
        if date_from.day != 1:
            year = date_from.year + (date_from.month // 12)
            month = (date_from.month % 12) + 1
            date_from = datetime(year, month, 1)

    date = date_from

    while date <= date_to:
        dates.append(date)
        if resolution == 'D':
            date += timedelta(days=1)
        elif resolution == 'W':
            date += timedelta(days=7)
        elif resolution == 'M':
            year = date.year + (date.month // 12)
            month = (date.month % 12) + 1
            date = datetime(year, month, 1)
        else:
            raise ValueError("Unsupported resolution. Use 'D', 'W', or 'M'.")

    return dates


def etl_load_asns(iso2, dates):
    print(f"{' '*12}Getting data from the API and storing to DB... ")
    for asns_batch in get_list_of_asns_for_country(iso2, dates, BATCH_SIZE):
        insert_country_asns_to_db(iso2, asns_batch, save_sql_to_file=False, load_to_database=True)


def etl_load_stats_1d(iso2, date_from, date_to):
    stats = get_stats_for_country(iso2, date_from, date_to, '1d')
    if stats:
        insert_country_stats_to_db(iso2, '1d', stats, True)

def etl_load_stats_5m(iso2, date_from, date_to):
    for year in range(2019, 2025):
        stats = get_stats_for_country(iso2, f"{year}-01-01", f'{year + 1}-01-01', '5m')
        if stats:
            insert_country_stats_to_db(iso2, '5m', stats, True)

def etl_load_asn_neighbours(iso2, dates):
    print(f"{' '*12}Getting data from the API and storing to DB... ")
    for neighbours_batch in get_list_of_asn_neighbours_for_country(iso2, dates, BATCH_SIZE):
        insert_country_asn_neighbours_to_db(iso2, neighbours_batch, True)


def etl_load_traffic(iso2, date_from, date_to):
    traffic=get_traffic_for_country(iso2, CLOUDFLARE_API_TOKEN)
    if traffic:
        insert_traffic_for_country_to_db(iso2, traffic, True)

def etl_load_internet_quality(iso2, date_from, date_to):
    internet_quality = get_internet_quality_for_country(iso2, CLOUDFLARE_API_TOKEN)
    if internet_quality:
         insert_internet_quality_for_country_to_db(iso2, internet_quality, True)

if __name__ == "__main__":
    main()
