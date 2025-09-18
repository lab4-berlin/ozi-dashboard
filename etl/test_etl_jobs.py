import unittest
from unittest.mock import patch, MagicMock, ANY
from datetime import datetime

from main import (
    etl_load_asns,
    etl_load_stats_1d,
    etl_load_stats_5m,
    etl_load_asn_neighbours,
    etl_load_traffic,
    etl_load_internet_quality,
)

MODULE_DB = "main"
MODULE_JOBS = "main"


class TestETLJobs(unittest.TestCase):
    @patch(f"{MODULE_DB}.insert_country_asns_to_db")
    @patch(f"{MODULE_JOBS}.get_list_of_asns_for_country")
    def test_etl_load_asns(self, mock_get_asns, mock_insert_asns):
        iso2 = "US"
        dates = [datetime(2023, 1, 1), datetime(2023, 1, 2)]

        mock_get_asns.return_value = [["ASN1", "ASN2"], ["ASN3"]]

        etl_load_asns(iso2, dates)

        mock_get_asns.assert_called_once_with(iso2, dates, ANY)
        self.assertEqual(mock_insert_asns.call_count, 2)
        mock_insert_asns.assert_any_call(iso2, ["ASN1", "ASN2"])
        mock_insert_asns.assert_any_call(iso2, ["ASN3"])

    @patch(f"{MODULE_DB}.insert_country_stats_to_db")
    @patch(f"{MODULE_JOBS}.get_stats_for_country")
    def test_etl_load_stats_1d(self, mock_get_stats, mock_insert_stats):
        iso2 = "DE"
        dates = [datetime(2023, 1, 1), datetime(2023, 1, 2)]

        mock_get_stats.side_effect = [[{"stat": 1}], None]

        etl_load_stats_1d(iso2, dates)

        self.assertEqual(mock_get_stats.call_count, 2)
        mock_insert_stats.assert_called_once_with(
            iso2, "1d", [{"stat": 1}], save_sql_to_file=True
        )

    @patch(f"{MODULE_DB}.insert_country_stats_to_db")
    @patch(f"{MODULE_JOBS}.get_stats_for_country")
    def test_etl_load_stats_5m(self, mock_get_stats, mock_insert_stats):
        iso2 = "FR"
        dates = [datetime(2023, 1, 1)]

        mock_get_stats.return_value = [{"stat": "some"}]

        etl_load_stats_5m(iso2, dates, save_to_file=False)

        mock_get_stats.assert_called_once_with(
            iso2, datetime(2023, 1, 1), datetime(2024, 1, 1), "5m"
        )
        mock_insert_stats.assert_called_once_with(
            iso2, "5m", [{"stat": "some"}], save_sql_to_file=False
        )

    @patch(f"{MODULE_DB}.insert_country_asn_neighbours_to_db")
    @patch(f"{MODULE_JOBS}.get_list_of_asn_neighbours_for_country")
    def test_etl_load_asn_neighbours(self, mock_get_neighbours, mock_insert_neighbours):
        iso2 = "JP"
        dates = [datetime(2023, 1, 1), datetime(2023, 1, 2)]

        mock_get_neighbours.return_value = [["N1", "N2"], ["N3"]]

        etl_load_asn_neighbours(iso2, dates)

        mock_get_neighbours.assert_called_once_with(iso2, dates, ANY)
        self.assertEqual(mock_insert_neighbours.call_count, 2)
        mock_insert_neighbours.assert_any_call(iso2, ["N1", "N2"])
        mock_insert_neighbours.assert_any_call(iso2, ["N3"])

    @patch(f"{MODULE_DB}.insert_traffic_for_country_to_db")
    @patch(f"{MODULE_JOBS}.get_traffic_for_country")
    def test_etl_load_traffic(self, mock_get_traffic, mock_insert_traffic):
        iso2 = "BR"
        dates = [datetime(2023, 1, 1)]

        mock_get_traffic.return_value = {"traffic": "some_data"}

        etl_load_traffic(iso2, dates, save_to_file=False)

        mock_get_traffic.assert_called_once_with(iso2, ANY)
        mock_insert_traffic.assert_called_once_with(
            iso2, {"traffic": "some_data"}, save_sql_to_file=False
        )

    @patch(f"{MODULE_DB}.insert_internet_quality_for_country_to_db")
    @patch(f"{MODULE_JOBS}.get_internet_quality_for_country")
    def test_etl_load_internet_quality(self, mock_get_quality, mock_insert_quality):
        iso2 = "IN"
        dates = [datetime(2023, 1, 1)]

        mock_get_quality.return_value = {"latency": 42}

        etl_load_internet_quality(iso2, dates, save_to_file=False)

        mock_get_quality.assert_called_once_with(iso2, ANY)
        mock_insert_quality.assert_called_once_with(
            iso2, {"latency": 42}, save_sql_to_file=False
        )


if __name__ == "__main__":
    unittest.main()
