"""This module provides functions to extract data from the Cloudflare API
regarding network traffic and internet quality."""

import requests


def get_cloudflare_traffic_for_country(country_iso2, api_token, copy_to_file=False):
    """
    Retrieves network traffic data for a specific country from the Cloudflare API.

    Args:
        country_iso2 (str): The ISO2 code of the country.
        api_token (str): The Cloudflare API token.
        copy_to_file (bool): If True, saves the data to a file.
                             (Currently not implemented in the function logic).

    Returns:
        dict: The API response JSON as a dictionary if successful, None otherwise.

    Raises:
        requests.exceptions.RequestException: This exception is caught internally,
                                              an error message is printed, and None is returned.
    """
    data = None
    api_url = "https://api.cloudflare.com/client/v4/radar/netflows/timeseries"
    params = {"name": "main", "location": country_iso2, "dateRange": "52w"}
    headers = {
        "Authorization": f"Bearer {api_token}",
    }

    try:
        response = requests.get(api_url, params=params, headers=headers)
        response.raise_for_status()  # Raises an HTTPError for bad responses (4XX or 5XX)
        data = response.json()

    except requests.exceptions.RequestException as e:
        print(f"An error occurred during Cloudflare API call for traffic data: {e}")

    return data


def get_cloudflare_internet_quality_for_country(
    country_iso2, api_token, copy_to_file=False
):
    """
    Retrieves internet quality data (bandwidth) for a specific country from the Cloudflare API.

    Args:
        country_iso2 (str): The ISO2 code of the country.
        api_token (str): The Cloudflare API token.
        copy_to_file (bool): If True, saves the data to a file.
                             (Currently not implemented in the function logic).

    Returns:
        dict: The API response JSON as a dictionary if successful, None otherwise.

    Raises:
        requests.exceptions.RequestException: This exception is caught internally,
                                              an error message is printed, and None is returned.
    """
    data = None
    api_url = "https://api.cloudflare.com/client/v4/radar/quality/iqi/timeseries_groups"
    params = {
        "name": "main",
        "location": country_iso2,
        "dateRange": "52w",
        "metric": "bandwidth",
        "interpolation": "true",
    }
    headers = {
        "Authorization": f"Bearer {api_token}",
    }

    try:
        response = requests.get(api_url, params=params, headers=headers)
        response.raise_for_status()  # Raises an HTTPError for bad responses (4XX or 5XX)
        data = response.json()

    except requests.exceptions.RequestException as e:
        print(
            f"An error occurred during Cloudflare API call for internet quality data: {e}"
        )

    return data
