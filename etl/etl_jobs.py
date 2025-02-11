from etl.load_to_database import BATCH_SIZE
from etl.extract_from_cloudflare_api import get_cloudflare_traffic_for_country, get_cloudflare_internet_quality_for_country
from etl.extract_from_ripe_api import get_country_asns, get_country_resource_stats, get_asn_neighbours

BAR_LENGTH = 50

def display_progress(processed, total, processed_until_date, received_from_api, stored_to_database, custom_msg=''):
    date_str = processed_until_date.strftime("%Y-%m-%d")

    progress = float(processed) / total
    filled_length = int(BAR_LENGTH * progress)
    bar = '|' + '█' * filled_length
    if BAR_LENGTH - filled_length -2 > len(date_str):
        bar += '-' + date_str + '-' * (BAR_LENGTH - filled_length - len(date_str) - 2) + '| '
    else:
        bar += '-' * (50 - filled_length) + '| ' + date_str

    print(f'\r{' ' * 12}{bar} Received: {received_from_api}, Stored: {stored_to_database}   {custom_msg}', end=' ', flush=True)


def get_list_of_asns_for_country(country_iso2, dates, batch_size, verbose=True):
    total_number_of_dates = len(dates)
    asns_batch = []
    received_from_api = 0

    if verbose:
        display_progress(0, total_number_of_dates, dates[0],0,0)

    while dates:
        date = dates.pop(0)
        d = get_country_asns(country_iso2, date, save_mode=None)

        if d['data']:
            routed_asns = d['data']['countries'][0]['routed']
            non_routed_asns = d['data']['countries'][0]['non_routed']
            routed_list = [ item.split('(')[1].split(')')[0] for item in routed_asns.strip('{}').split(', ') if item.startswith("AsnSingle")]
            non_routed_list = [ item.split('(')[1].split(')')[0] for item in non_routed_asns.strip('{}').split(', ') if item.startswith("AsnSingle")]

            for asn in routed_list:
                asns_batch.append({'asn':asn, 'date':date.strftime("%Y-%m-%d"), 'is_routed' : True})
            for asn in non_routed_list:
                asns_batch.append({'asn':asn, 'date':date.strftime("%Y-%m-%d"), 'is_routed' : False})

            if verbose:
                display_progress(total_number_of_dates - len(dates) - 1, total_number_of_dates, date, received_from_api + len(asns_batch), received_from_api)

            if len(asns_batch) >= batch_size:
                yield asns_batch
                received_from_api += len(asns_batch)
                asns_batch = []

    if asns_batch:
        yield asns_batch

def get_stats_for_country(country_iso2, date_from, date_to, resolution):
    print(f"    Getting historical stats {country_iso2}, {resolution}, {date_from}, {date_to}", end=' ... ')
    d = get_country_resource_stats(country_iso2, resolution, date_from, date_to, save_mode='file')
    if d:
        stats = d['data']['stats']
        print(f"    {len(stats)} records found")
        return stats


def get_list_of_asn_neighbours_for_country(country_iso2, dates, batch_size, verbose=True):
    total_number_of_dates = len(dates)
    neighbours_batch = []
    received_from_api = 0
    stored_to_database = 0

    if verbose:
        display_progress(0, total_number_of_dates, dates[0], 0, 0)

    while dates:
        date = dates.pop(0)
        for asn_list in get_list_of_asns_for_country(country_iso2, [date], BATCH_SIZE, verbose=False):
            counter=0
            for item in asn_list:
                asn=item['asn']
                counter+=1
                if verbose:
                    display_progress(total_number_of_dates - len(dates) - 1, total_number_of_dates,
                                                date, received_from_api + len(neighbours_batch), stored_to_database,
                                                f'    asn {counter}/{len(asn_list)}')

                d = get_asn_neighbours(asn, date)
                if d['data']:
                    for row in d['data']['neighbours']:
                        row['asn_req'] = asn
                        row['date'] = date.strftime("%Y-%m-%d")
                        neighbours_batch.append(row)


                if len(neighbours_batch) >= batch_size:
                    yield neighbours_batch
                    stored_to_database += len(neighbours_batch)
                    received_from_api += len(neighbours_batch)
                    neighbours_batch = []

    if neighbours_batch:
        yield neighbours_batch



def get_traffic_for_country(country_iso2, token):
    print(f"Getting traffic for {country_iso2}", end=" ... ")
    d = get_cloudflare_traffic_for_country(country_iso2, token, copy_to_file=True)
    if d:
        traffic = d['result']['main']
        print(f"{len(traffic['timestamps'])} records found")
        return traffic

def get_internet_quality_for_country(country_iso2, token):
    print(f"    Getting internet quality for {country_iso2}", end=" ... ")
    d = get_cloudflare_internet_quality_for_country(country_iso2, token, copy_to_file=True)
    if d:
        internet_quality = d['result']['main']
        print(f"{len(internet_quality['timestamps'])} records found")
        return internet_quality

