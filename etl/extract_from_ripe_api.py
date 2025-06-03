"""
This module provides functions to interact with the RIPE Stat API
for AS (Autonomous System) and network resource data.

It handles API calls with retries and provides options to save responses.
"""

import json
import re
from datetime import datetime
from json import JSONDecodeError  # More specific import
import requests
import time

API_URL = "https://stat.ripe.net/data/{}/data.json"
RETRIES = 5


def get_country_asns(country_iso2, date, save_mode=None):
    """
    Retrieves a list of Autonomous Systems (ASNs) for a given country and date.

    Args:
        country_iso2 (str): The ISO2 code of the country.
        date (datetime.datetime): The specific date for which to query ASNs.
        save_mode (str, optional): If 'file', saves the API response to a file.
                                   Defaults to None (no save).

    Returns:
        dict or None: A dictionary containing the API response data if successful,
                      otherwise None. The data typically includes ASN details.
                      Returns None if the API call fails after all retries.
    """
    url = API_URL.format("country-asns")
    params = {
        "resource": country_iso2,
        "query_time": date.strftime("%Y-%m-%dT00:00:00Z"),
        "lod": 1,
    }
    data = ripe_api_call(url, params)

    if save_mode == "file" and data is not None:  # Ensure data exists before saving
        save_api_response(
            url=url, params=params, response_data=data, save_mode=save_mode
        )
    return data


def get_country_resource_stats(
    country_iso2, resolution, start_time, end_time, save_mode=None
):
    """
    Retrieves resource statistics for a country within a specified time range and resolution.

    Args:
        country_iso2 (str): The ISO2 code of the country.
        resolution (str): The time resolution for statistics (e.g., "1d" for daily).
        start_time (str): The start date/time for the query (YYYY-MM-DD or ISO8601).
        end_time (str): The end date/time for the query (YYYY-MM-DD or ISO8601).
        save_mode (str, optional): If 'file', saves the API response. Defaults to None.

    Returns:
        dict or None: A dictionary with resource statistics if successful, else None.
                      Returns None if the API call fails after all retries.
    """
    url = API_URL.format("country-resource-stats")
    params = {
        "resource": country_iso2,
        "starttime": start_time,
        "endtime": end_time,
        "resolution": resolution,
    }
    data = ripe_api_call(url, params)

    if save_mode == "file" and data is not None:
        save_api_response(
            url=url, params=params, response_data=data, save_mode=save_mode
        )
    return data


def get_asn_neighbours(asn, date, save_mode=None):
    """
    Retrieves a list of ASN neighbours for a given ASN at a specific date.

    Args:
        asn (str): The Autonomous System Number (e.g., "AS12345").
        date (datetime.datetime): The specific date for the query.
        save_mode (str, optional): If 'file', saves the API response. Defaults to None.

    Returns:
        dict or None: A dictionary with ASN neighbours data if successful, else None.
                      Returns None if the API call fails after all retries.
    """
    url = API_URL.format("asn-neighbours")
    params = {"resource": asn, "query_time": date.strftime("%Y-%m-%dT00:00:00Z")}
    data = ripe_api_call(url, params)

    if save_mode == "file" and data is not None:
        save_api_response(
            url=url, params=params, response_data=data, save_mode=save_mode
        )
    return data


def ripe_api_call(url, params):
    """
    Performs a generic API call to the RIPE Stat API with retry logic.

    Args:
        url (str): The full API endpoint URL.
        params (dict): A dictionary of query parameters for the API call.

    Returns:
        dict or None: The JSON response from the API parsed into a dictionary
                      if the call is successful. Returns None if the call fails
                      after all configured retries (due to network issues,
                      HTTP errors, or invalid JSON response).

    Handles Exceptions:
        - requests.exceptions.HTTPError: For HTTP error status codes (4xx, 5xx).
        - requests.exceptions.RequestException: For other request issues (network, timeout).
        - json.JSONDecodeError: If the response text is not valid JSON.
        - Exception: Catches any other unexpected errors during the call.
    Retries are performed for these exceptions up to `RETRIES` times with a 1-second delay.
    """
    attempts_left = RETRIES
    while attempts_left > 0:
        try:
            response = requests.get(url, params=params)  # Corrected: params=params
            response.raise_for_status()  # Raises HTTPError for bad responses (4XX or 5XX)
            return json.loads(response.text)  # Return parsed JSON directly
        except requests.exceptions.HTTPError as http_err:
            attempts_left -= 1
            print(
                f"\nHTTP error during API request: {http_err}. URL: {url}, Params: {params}. Retries left: {attempts_left}"
                + ("... RETRYING" if attempts_left > 0 else "... STOP")
            )
            if attempts_left > 0:
                time.sleep(1)
        except (
            requests.exceptions.RequestException
        ) as req_err:  # Includes connection, timeout
            attempts_left -= 1
            print(
                f"\nRequest exception during API request: {req_err}. URL: {url}, Params: {params}. Retries left: {attempts_left}"
                + ("... RETRYING" if attempts_left > 0 else "... STOP")
            )
            if attempts_left > 0:
                time.sleep(1)
        except JSONDecodeError as json_err:  # If response.text is not valid JSON
            attempts_left -= 1
            # Usually, JSON decode errors are not worth retrying as the response is likely malformed.
            # However, sticking to current RETRIES for all handled exceptions for now.
            print(
                f"\nJSON decode error during API request: {json_err}. URL: {url}, Params: {params}. Response text: '{response.text[:100]}...'. Retries left: {attempts_left}"
                + ("... RETRYING" if attempts_left > 0 else "... STOP")
            )
            if attempts_left > 0:
                time.sleep(1)
        except Exception as e:  # Catch any other unexpected errors
            attempts_left -= 1
            print(
                f"\nAn unexpected error occurred during API request: {e}. URL: {url}, Params: {params}. Retries left: {attempts_left}"
                + ("... RETRYING" if attempts_left > 0 else "... STOP")
            )
            if attempts_left > 0:
                time.sleep(1)
    return None


def save_api_response(url, params, response_data, save_mode=None):
    """
    Saves the API response data to a JSON file.

    The filename is constructed using the URL, query parameters, and a timestamp
    to ensure uniqueness and provide context. Sensitive parts of params or URL
    are not explicitly handled here for sanitization beyond basic character replacement.

    Args:
        url (str): The API URL used for the request.
        params (dict): The parameters used in the API request.
        response_data (dict): The JSON data (as a dictionary) received from the API.
        save_mode (str, optional): Currently, only 'file' is implemented.
                                   If 'file', data is saved. Otherwise, no action.

    File Naming Convention:
        'data/ripe_response_<timestamp>_<sanitized_url_and_params>.json'
        Timestamp format: YYYY-MM-DD_HH-MM-SS
        Sanitization: Replaces characters like {},.<>:"/\\|?* with '_'
    """
    if save_mode == "file":
        # Create a deepcopy of params for modification, to avoid altering original dict
        params_copy = json.loads(
            json.dumps(params)
        )  # Simple deepcopy for typical dicts
        for key, value in params_copy.items():
            if isinstance(
                value, datetime
            ):  # This check might be redundant if params are already strings
                params_copy[key] = value.isoformat()

        # Create a string from URL and params for the filename
        # Ensure a consistent order for params if Python version < 3.7 for reproducibility
        # For Python 3.7+ dicts are ordered, for <3.7 sort by keys for consistency
        # params_string = json.dumps(params_copy, sort_keys=True, separators=(",", ":"))
        # However, current code does not sort_keys. Sticking to that.
        params_string = json.dumps(params_copy, separators=(",", ":"))

        identifier_string = f"{url}{params_string}"
        # Sanitize the string to be filesystem-friendly
        sanitized_identifier_string = re.sub(
            r'[{},.<>:"/\\|?*]', "_", identifier_string
        )
        # Limit length of sanitized string to prevent overly long filenames
        max_len_identifier = 100  # Arbitrary limit
        sanitized_identifier_string = sanitized_identifier_string[:max_len_identifier]

        timestamp_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        # Ensure 'data/' directory exists (optional, good practice)
        # import os; os.makedirs('data', exist_ok=True)

        filename = (
            f"data/ripe_response_{timestamp_str}_{sanitized_identifier_string}.json"
        )

        try:
            with open(filename, "w") as f:
                json.dump(response_data, f, indent=4)  # Save as pretty JSON
            print(f"API response saved to {filename}")
        except IOError as e:
            print(f"Error saving API response to {filename}: {e}")
