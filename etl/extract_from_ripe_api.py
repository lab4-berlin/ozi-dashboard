import json
import re
from datetime import datetime
from json import loads
import requests

API_URL = 'https://stat.ripe.net/data/{}/data.json'
RETRIES = 5

def get_country_asns(country_iso2, date, save_mode=None):
    url = API_URL.format("country-asns")
    params = {"resource": country_iso2, "query_time": date.strftime("%Y-%m-%dT00:00:00Z"), "lod": 1}
    data = ripe_api_call(url, params)

    if save_mode:
        save_api_response(url, params, data, save_mode)
    return data


def get_country_resource_stats(country_iso2, resolution, start_time, end_time, save_mode=None):
    url = API_URL.format("country-resource-stats")
    params = {"resource": country_iso2, "starttime": start_time, "endtime": end_time, "resolution": resolution}
    data = ripe_api_call(url, params)

    if save_mode:
        save_api_response(url, params, data, save_mode)
    return data

def get_asn_neighbours(asn, date, save_mode=None):
    url = API_URL.format("asn-neighbours")
    params = {"resource": asn, "query_time": date.strftime("%Y-%m-%dT00:00:00Z")}
    data = ripe_api_call(url, params)

    if save_mode:
        save_api_response(url, params, data, save_mode)
    return data


def ripe_api_call(url, params):
    attempts_left = RETRIES
    while attempts_left > 0:
        try:
            response = requests.get(url, params)
            data = loads(response.text)
            if data:
                return data
        except Exception as e:
            print("\nException during API request" + "... RETRYING" if attempts_left else "... STOP")
    return None

def save_api_response(url, params, response, save_mode = None):
    if save_mode == 'file':
        for key, value in params.items():
            if isinstance(value, datetime):
                params[key] = value.isoformat()
        params_string = json.dumps(params, separators=(",", ":"))
        str = f'{url}{params_string}'
        str = re.sub(r'[{},.<>:"/\\|?*]', '_', str)
        filename = f"data/ripe_response_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}_{str}.json"

        with open(filename, 'w') as f:
            print(response, file=f)
