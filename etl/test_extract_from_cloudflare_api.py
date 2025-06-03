import unittest
from unittest.mock import patch, MagicMock
import requests  # Import requests for requests.exceptions.RequestException
from etl.extract_from_cloudflare_api import (
    get_cloudflare_traffic_for_country,
    get_cloudflare_internet_quality_for_country,
)


class TestCloudflareAPIExtraction(unittest.TestCase):

    @patch("etl.extract_from_cloudflare_api.requests.get")
    def test_get_cloudflare_traffic_success(self, mock_get):
        # Configure the mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result": {"main": "traffic_data"},
            "success": True,
        }
        mock_get.return_value = mock_response

        # Call the function
        result = get_cloudflare_traffic_for_country("US", "fake_token")

        # Assertions
        expected_url = "https://api.cloudflare.com/client/v4/radar/netflows/timeseries"
        expected_params = {"name": "main", "location": "US", "dateRange": "52w"}
        expected_headers = {"Authorization": "Bearer fake_token"}
        mock_get.assert_called_once_with(
            expected_url, params=expected_params, headers=expected_headers
        )
        mock_response.raise_for_status.assert_called_once()
        self.assertEqual(result, {"result": {"main": "traffic_data"}, "success": True})

    @patch("etl.extract_from_cloudflare_api.requests.get")
    def test_get_cloudflare_traffic_api_error(self, mock_get):
        # Configure the mock to raise a requests.exceptions.RequestException
        mock_get.side_effect = requests.exceptions.RequestException("API Error")

        # Call the function
        result = get_cloudflare_traffic_for_country("US", "fake_token")

        # Assertions
        expected_url = "https://api.cloudflare.com/client/v4/radar/netflows/timeseries"
        expected_params = {"name": "main", "location": "US", "dateRange": "52w"}
        expected_headers = {"Authorization": "Bearer fake_token"}
        mock_get.assert_called_once_with(
            expected_url, params=expected_params, headers=expected_headers
        )
        self.assertIsNone(result)

    @patch("etl.extract_from_cloudflare_api.requests.get")
    def test_get_internet_quality_success(self, mock_get):
        # Configure the mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result": {"main": "quality_data"},
            "success": True,
        }
        mock_get.return_value = mock_response

        # Call the function
        result = get_cloudflare_internet_quality_for_country("US", "fake_token")

        # Assertions
        expected_url = (
            "https://api.cloudflare.com/client/v4/radar/quality/iqi/timeseries_groups"
        )
        expected_params = {
            "name": "main",
            "location": "US",
            "dateRange": "52w",
            "metric": "bandwidth",
            "interpolation": "true",
        }
        expected_headers = {"Authorization": "Bearer fake_token"}
        mock_get.assert_called_once_with(
            expected_url, params=expected_params, headers=expected_headers
        )
        mock_response.raise_for_status.assert_called_once()
        self.assertEqual(result, {"result": {"main": "quality_data"}, "success": True})

    @patch("etl.extract_from_cloudflare_api.requests.get")
    def test_get_internet_quality_api_error(self, mock_get):
        # Configure the mock to raise a requests.exceptions.RequestException
        mock_get.side_effect = requests.exceptions.RequestException("API Error")

        # Call the function
        result = get_cloudflare_internet_quality_for_country("US", "fake_token")

        # Assertions
        expected_url = (
            "https://api.cloudflare.com/client/v4/radar/quality/iqi/timeseries_groups"
        )
        expected_params = {
            "name": "main",
            "location": "US",
            "dateRange": "52w",
            "metric": "bandwidth",
            "interpolation": "true",
        }
        expected_headers = {"Authorization": "Bearer fake_token"}
        mock_get.assert_called_once_with(
            expected_url, params=expected_params, headers=expected_headers
        )
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
