import requests


def get_cloudflare_traffic_for_country(country_iso2, api_token, copy_to_file=False):
    api_url = "https://api.cloudflare.com/client/v4/radar/netflows/timeseries"
    params = {"name": "main", "location": country_iso2, "dateRange": "52w"}
    headers = {
        "Authorization": f"Bearer {api_token}",
    }

    try:
        response = requests.get(api_url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()

    except requests.exceptions.RequestException as e:
        print("An error occurred during cloudflare API call:", e)

    return data


def get_cloudflare_internet_quality_for_country(
    country_iso2, api_token, copy_to_file=False
):
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
        response.raise_for_status()
        data = response.json()

    except requests.exceptions.RequestException as e:
        print("An error occurred during cloudflare API call:", e)

    return data
