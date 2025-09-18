import json
import re
import os
import time
from datetime import datetime
from json import loads
import requests

API_URL = "https://stat.ripe.net/data/{}/data.json"
RETRIES = 5


def get_country_asns(country_iso2, date, save_mode=None):
    url = API_URL.format("country-asns")
    params = {"resource": country_iso2, "query_time": date.isoformat(), "lod": 1}
    data = ripe_api_call(url, params)

    if save_mode:
        save_api_response(url, params, data, save_mode)
    return data


def get_country_resource_stats(country_iso2, resolution, date, save_mode=None):
    date_str = date.isoformat()
    url = API_URL.format("country-resource-stats")
    params = {
        "resource": country_iso2,
        "starttime": date_str,
        "endtime": date_str,
        "resolution": resolution,
    }
    data = ripe_api_call(url, params)

    if save_mode:
        save_api_response(url, params, data, save_mode)
    return data


def get_asn_neighbours(asn, date, save_mode=None):
    url = API_URL.format("asn-neighbours")
    params = {"resource": asn, "query_time": date.isoformat()}
    data = ripe_api_call(url, params)

    if save_mode:
        save_api_response(url, params, data, save_mode)
    return data


def ripe_api_call(url, params):
    attempts_left = RETRIES
    while attempts_left > 0:
        try:
            response = requests.get(url, params)
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            data = loads(response.text)
            if data:
                return data
        except requests.exceptions.HTTPError as e:
            print(f"\nHTTP Error during API request: {e}")
            attempts_left -= 1
            if attempts_left > 0:
                if e.response.status_code == 429:  # Too Many Requests
                    print("Rate limit hit. Waiting longer before retrying.")
                    time.sleep(10)  # Wait longer for rate limiting
                else:
                    print(f"... RETRYING ({attempts_left} attempts left)")
                    time.sleep(5)  # Standard wait for other HTTP errors
            else:
                print("... STOP")
        except json.JSONDecodeError:
            print(
                f"\nJSON Decode Error: Could not parse response as JSON for URL: {url} with params: {params}"
            )
            attempts_left -= 1
            if attempts_left > 0:
                print(f"... RETRYING ({attempts_left} attempts left)")
                time.sleep(5)  # Wait before retrying for JSON decode errors
            else:
                print("... STOP")
        except Exception as e:
            print(f"\nException during API request: {e}")
            attempts_left -= 1
            if attempts_left > 0:
                print(f"... RETRYING ({attempts_left} attempts left)")
                time.sleep(5)  # Wait for 5 seconds before retrying on other exceptions
            else:
                print("... STOP")
    return None


def sanitize_filename(s: str) -> str:
    return re.sub(r'[{},.<>:"/\\|?*]', "_", s)


def save_api_response(url, params, response, save_mode=None):
    if save_mode == "file":
        params_clean = {
            k: v.isoformat() if isinstance(v, datetime) else v
            for k, v in params.items()
        }

        params_string = json.dumps(params_clean, separators=(",", ":"))
        safe_string = sanitize_filename(f"{url}{params_string}")

        folder = "data"
        os.makedirs(folder, exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"{folder}/ripe_response_{timestamp}_{safe_string}.json"

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(response, f, ensure_ascii=False, indent=2)
