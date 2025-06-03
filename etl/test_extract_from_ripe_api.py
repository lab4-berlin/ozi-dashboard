import unittest
from unittest.mock import patch, MagicMock, call
import datetime
import requests  # Required for requests.exceptions.RequestException
import json  # Required for json.loads

# Functions and constants to test
from etl.extract_from_ripe_api import (
    get_country_asns,
    get_country_resource_stats,
    get_asn_neighbours,
    ripe_api_call,
    RETRIES,  # Import RETRIES for assertion
)


class TestRipeAPIExtraction(unittest.TestCase):

    @patch("etl.extract_from_ripe_api.ripe_api_call")
    def test_get_country_asns_success(self, mock_ripe_api_call):
        mock_ripe_api_call.return_value = {"data": "asns_data"}

        test_date = datetime.datetime(2023, 1, 1)
        result = get_country_asns("US", test_date)

        expected_url = "https://stat.ripe.net/data/country-asns/data.json"
        expected_params = {
            "resource": "US",
            "query_time": "2023-01-01T00:00:00Z",
            "lod": 1,
        }
        # ripe_api_call in the source does not take filename_prefix
        mock_ripe_api_call.assert_called_once_with(expected_url, expected_params)
        self.assertEqual(result, {"data": "asns_data"})

    @patch("etl.extract_from_ripe_api.ripe_api_call")
    def test_get_country_resource_stats_success(self, mock_ripe_api_call):
        mock_ripe_api_call.return_value = {"data": "stats_data"}

        result = get_country_resource_stats("US", "1d", "2023-01-01", "2023-01-02")

        expected_url = "https://stat.ripe.net/data/country-resource-stats/data.json"
        expected_params = {
            "resource": "US",
            "resolution": "1d",
            "starttime": "2023-01-01",
            "endtime": "2023-01-02",
        }
        # ripe_api_call in the source does not take filename_prefix
        mock_ripe_api_call.assert_called_once_with(expected_url, expected_params)
        self.assertEqual(result, {"data": "stats_data"})

    @patch("etl.extract_from_ripe_api.ripe_api_call")
    def test_get_asn_neighbours_success(self, mock_ripe_api_call):
        mock_ripe_api_call.return_value = {"data": "neighbours_data"}

        test_date = datetime.datetime(2023, 1, 1)
        result = get_asn_neighbours("AS123", test_date)

        expected_url = "https://stat.ripe.net/data/asn-neighbours/data.json"
        expected_params = {"resource": "AS123", "query_time": "2023-01-01T00:00:00Z"}
        # ripe_api_call in the source does not take filename_prefix
        mock_ripe_api_call.assert_called_once_with(expected_url, expected_params)
        self.assertEqual(result, {"data": "neighbours_data"})

    @patch(
        "etl.extract_from_ripe_api.time.sleep"
    )  # Mock time.sleep to speed up retry tests
    @patch("etl.extract_from_ripe_api.requests.get")
    def test_ripe_api_call_success_on_retry(self, mock_requests_get, mock_time_sleep):
        mock_response_success = MagicMock()
        mock_response_success.status_code = 200
        # ripe_api_call uses response.text and then json.loads()
        mock_response_success.text = '{"data": "retry_success"}'

        mock_requests_get.side_effect = [
            requests.exceptions.RequestException("Attempt 1 failed"),
            requests.exceptions.RequestException("Attempt 2 failed"),
            mock_response_success,
        ]
        # Call ripe_api_call without filename_prefix as it's not an accepted argument
        result = ripe_api_call("http://fakeurl", {})

        self.assertEqual(mock_requests_get.call_count, 3)
        self.assertEqual(result, {"data": "retry_success"})
        # Check that sleep was called twice (for the two retries)
        self.assertEqual(mock_time_sleep.call_count, 2)

    @patch("etl.extract_from_ripe_api.time.sleep")  # Mock time.sleep
    @patch("etl.extract_from_ripe_api.requests.get")
    def test_ripe_api_call_failure_after_retries(
        self, mock_requests_get, mock_time_sleep
    ):
        mock_requests_get.side_effect = requests.exceptions.RequestException(
            "Consistent API Error"
        )

        # Call ripe_api_call without filename_prefix as it's not an accepted argument
        result = ripe_api_call("http://fakeurl", {})

        self.assertEqual(mock_requests_get.call_count, RETRIES)
        self.assertIsNone(result)
        # Check that sleep was called RETRIES - 1 times
        self.assertEqual(mock_time_sleep.call_count, RETRIES - 1)


if __name__ == "__main__":
    unittest.main()
