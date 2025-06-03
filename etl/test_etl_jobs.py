import unittest
from unittest.mock import patch, MagicMock, call
import datetime
import io
import sys

# Functions and constants to test
from etl.etl_jobs import (
    get_list_of_asns_for_country,
    get_stats_for_country,
    get_list_of_asn_neighbours_for_country,
    display_progress,
    BAR_LENGTH,  # Assuming BAR_LENGTH is defined in etl_jobs.py
)

# These are mocked, but importing them helps to ensure the patch targets are correct
# from etl.extract_from_ripe_api import get_country_asns, get_country_resource_stats, get_asn_neighbours


class TestEtlJobs(unittest.TestCase):

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_display_progress_output(self, mock_stdout):
        processed_date = datetime.datetime(2023, 1, 1, 10, 30, 0)
        display_progress(
            processed=10,
            total=100,
            processed_until_date=processed_date,
            received_from_api=50,
            stored_to_database=40,
            custom_msg="Test Message",
        )
        output = mock_stdout.getvalue()

        self.assertIn("Test Message", output)
        # self.assertIn("10/100", output) # display_progress doesn't print this ratio directly
        self.assertIn(
            processed_date.strftime("%Y-%m-%d %H:%M:%S"), output
        )  # Date is part of the bar or custom message
        self.assertIn(" Received: 50", output)  # Corrected: Added leading space
        self.assertIn(" Stored: 40", output)  # Corrected: Added leading space

        # Check progress bar components
        filled_length = int(BAR_LENGTH * 10 / 100)  # 5
        self.assertIn(
            "|" + "█" * filled_length, output
        )  # Check for pipe and filled part

        # Check for date embedding or presence (date itself is checked separately)
        # Check for some hyphens if the bar is not full
        if filled_length < BAR_LENGTH:
            self.assertIn("-", output)
        self.assertIn(
            "| ", output
        )  # Bar ends with "| " or "| date_str" if date appended

        self.assertIn("10.0%", output)

    @patch(
        "etl.etl_jobs.get_country_asns"
    )  # Patching the function as it's used in etl_jobs module
    def test_get_list_of_asns_for_country_success(self, mock_get_country_asns_api):
        # Mock RIPE API response structure - corrected to AsnSingle format
        mock_response_date1 = {
            "data": {
                "countries": [
                    {
                        "routed": "AsnSingle(AS123), AsnSingle(AS456)",
                        "non_routed": "AsnSingle(AS789)",
                    }
                ]
            }
        }
        mock_response_date2 = {
            "data": {
                "countries": [
                    {"routed": "AsnSingle(AS1011)", "non_routed": "AsnSingle(AS1213)"}
                ]
            }
        }
        mock_get_country_asns_api.side_effect = [
            mock_response_date1,
            mock_response_date2,
        ]

        original_dates = [datetime.datetime(2023, 1, 1), datetime.datetime(2023, 1, 2)]
        # Pass a copy of dates if the function modifies it, or use original_dates for assertions
        dates_for_function_call = list(original_dates)

        results_generator = get_list_of_asns_for_country(
            "US", dates_for_function_call, batch_size=2, verbose=False
        )

        all_results = []
        for batch in results_generator:
            all_results.extend(batch)

        # Assertions
        self.assertEqual(mock_get_country_asns_api.call_count, 2)
        # Use original_dates for assertion as dates_for_function_call will be empty
        mock_get_country_asns_api.assert_any_call("US", original_dates[0])
        mock_get_country_asns_api.assert_any_call("US", original_dates[1])

        expected_results = [
            {
                "asn": "AS123",
                "date": "2023-01-01",
                "is_routed": True,
            },  # Corrected ASN format
            {"asn": "AS456", "date": "2023-01-01", "is_routed": True},
            {"asn": "AS789", "date": "2023-01-01", "is_routed": False},
            {"asn": "AS1011", "date": "2023-01-02", "is_routed": True},
            {"asn": "AS1213", "date": "2023-01-02", "is_routed": False},
        ]
        self.assertEqual(len(all_results), 5)
        for expected_item in expected_results:
            self.assertIn(expected_item, all_results)

    @patch("etl.etl_jobs.get_country_asns")
    def test_get_list_of_asns_for_country_batching(self, mock_get_country_asns_api):
        # Corrected mock response to AsnSingle format
        mock_response = {
            "data": {
                "countries": [
                    {
                        "routed": "AsnSingle(AS1),AsnSingle(AS2),AsnSingle(AS3)",
                        "non_routed": "AsnSingle(AS4),AsnSingle(AS5)",
                    }
                ]
            }
        }
        mock_get_country_asns_api.return_value = mock_response
        # Pass a copy of dates if the function modifies it
        dates_for_function_call = [datetime.datetime(2023, 1, 1)]

        results_generator = get_list_of_asns_for_country(
            "US", dates_for_function_call, batch_size=3, verbose=False
        )

        batches = list(results_generator)
        self.assertEqual(len(batches), 2)
        self.assertEqual(len(batches[0]), 3)
        self.assertEqual(len(batches[1]), 2)

        self.assertEqual(
            batches[0][0], {"asn": "AS1", "date": "2023-01-01", "is_routed": True}
        )

    @patch("etl.etl_jobs.get_country_asns")
    def test_get_list_of_asns_for_country_empty_response(
        self, mock_get_country_asns_api
    ):
        mock_get_country_asns_api.return_value = {"data": None}
        dates_for_function_call = [datetime.datetime(2023, 1, 1)]
        results_generator = get_list_of_asns_for_country(
            "US", dates_for_function_call, batch_size=2, verbose=False
        )
        all_results = list(results_generator)
        self.assertEqual(
            len(all_results), 0
        )  # Corrected: expects no batches if no data

    @patch("etl.etl_jobs.get_country_resource_stats")
    def test_get_stats_for_country_success(self, mock_get_country_resource_stats_api):
        mock_response = {"data": {"stats": [{"key": "value1"}, {"key": "value2"}]}}
        mock_get_country_resource_stats_api.return_value = mock_response

        result = get_stats_for_country("US", "2023-01-01", "2023-01-02", "1d")

        # Corrected assertion to include save_mode
        mock_get_country_resource_stats_api.assert_called_once_with(
            "US", "1d", "2023-01-01", "2023-01-02", save_mode="file"
        )
        self.assertEqual(result, [{"key": "value1"}, {"key": "value2"}])

    @patch("etl.etl_jobs.get_country_resource_stats")
    def test_get_stats_for_country_no_data(self, mock_get_country_resource_stats_api):
        mock_get_country_resource_stats_api.return_value = None
        result = get_stats_for_country("US", "2023-01-01", "2023-01-02", "1d")
        self.assertIsNone(
            result
        )  # This case (API call returns None) should still be None

        mock_get_country_resource_stats_api.return_value = {
            "data": {"stats": []}
        }  # API returns empty stats list
        result = get_stats_for_country("US", "2023-01-01", "2023-01-02", "1d")
        # Corrected: function now returns [] if API provides an empty list for stats
        self.assertEqual(result, [])

    @patch(
        "etl.etl_jobs.get_asn_neighbours"
    )  # Mock the get_asn_neighbours from extract_from_ripe_api
    @patch(
        "etl.etl_jobs.get_list_of_asns_for_country"
    )  # Mock the already tested function within etl_jobs
    def test_get_list_of_asn_neighbours_for_country_success(
        self, mock_get_asns_for_country, mock_get_asn_neighbours_api
    ):
        # Configure mock for get_list_of_asns_for_country to yield a controlled list of ASNs
        # It yields batches, so simulate that. Corrected ASN format
        asn_batch_1 = [
            {"asn": "AS123", "date": "2023-01-01", "is_routed": True},
            {"asn": "AS456", "date": "2023-01-01", "is_routed": True},
        ]
        mock_get_asns_for_country.return_value = iter([asn_batch_1])

        mock_neighbour_response_as123 = {
            "data": {
                "neighbours": [
                    {"type": "left", "power": 1, "v4_peers": 1, "v6_peers": 1}
                ]
            }  # asn_req and date are added by function
        }
        mock_neighbour_response_as456 = {
            "data": {
                "neighbours": [
                    {"type": "right", "power": 2, "v4_peers": 2, "v6_peers": 2}
                ]
            }
        }
        mock_get_asn_neighbours_api.side_effect = [
            mock_neighbour_response_as123,
            mock_neighbour_response_as456,
        ]

        original_dates = [datetime.datetime(2023, 1, 1)]
        dates_for_function_call = list(original_dates)

        results_generator = get_list_of_asn_neighbours_for_country(
            "US", dates_for_function_call, batch_size_neighbours=1, verbose=False
        )

        all_results = []
        for batch in results_generator:
            all_results.extend(batch)

        # Assertions
        # The dates list passed to get_list_of_asns_for_country inside the loop is a new list with single date_obj
        mock_get_asns_for_country.assert_called_once_with(
            "US", [original_dates[0]], batch_size=100, verbose=False
        )

        self.assertEqual(mock_get_asn_neighbours_api.call_count, 2)
        mock_get_asn_neighbours_api.assert_any_call(
            "AS123", original_dates[0]
        )  # Corrected ASN format
        mock_get_asn_neighbours_api.assert_any_call("AS456", original_dates[0])

        expected_results = [
            {
                "asn_req": "AS123",
                "date": "2023-01-01",
                "type": "left",
                "power": 1,
                "v4_peers": 1,
                "v6_peers": 1,
            },
            {
                "asn_req": "AS456",
                "date": "2023-01-01",
                "type": "right",
                "power": 2,
                "v4_peers": 2,
                "v6_peers": 2,
            },
        ]
        self.assertEqual(len(all_results), 2)
        # No need to pop 'asn' as it's not part of the mock_neighbour_response, it's part of asn_batch_1 items
        for expected_item in expected_results:
            self.assertIn(expected_item, all_results)


if __name__ == "__main__":
    unittest.main()
