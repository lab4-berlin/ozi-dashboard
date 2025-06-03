import unittest
from unittest.mock import patch, MagicMock, call
import datetime
import argparse
import io
import sys
import os  # For CLOUDFLARE_API_TOKEN if needed by specific task tests later, and for ALL_COUNTRIES path

# Functions and constants to test from etl.main
from etl.main import (
    main,
    generate_dates,
    # Actual etl_load_* functions are patched via string path 'etl.main.etl_load_*'
)

# Import ALL_COUNTRIES for mocking, it's in etl.country_lists, imported by etl.main
# To mock it where etl.main looks for it:
# @patch('etl.main.ALL_COUNTRIES', MOCK_ALL_COUNTRIES_DICT)

# Mocked ALL_COUNTRIES for testing --countries all
MOCK_ALL_COUNTRIES_DICT = {
    "US": "United States",
    "CA": "Canada",
    "GB": "United Kingdom",
}


class TestGenerateDates(unittest.TestCase):
    def test_generate_dates_daily(self):
        date_from = datetime.datetime(2023, 1, 1)
        date_to = datetime.datetime(2023, 1, 3)
        expected = [
            datetime.datetime(2023, 1, 1),
            datetime.datetime(2023, 1, 2),
            datetime.datetime(2023, 1, 3),
        ]
        self.assertEqual(generate_dates(date_from, date_to, "D"), expected)

    def test_generate_dates_weekly_starts_on_monday(self):
        date_from = datetime.datetime(2023, 1, 2)  # A Monday
        date_to = datetime.datetime(2023, 1, 15)  # Two full weeks
        # Expects: Mon Jan 2, Mon Jan 9
        # generate_dates advances to the *next* Monday if not already a Monday.
        # (7 - date_from.weekday()) % 7. For Mon (0), (7-0)%7 = 0. So date_from is unchanged.
        expected = [
            datetime.datetime(2023, 1, 2),
            datetime.datetime(2023, 1, 9),
        ]
        self.assertEqual(generate_dates(date_from, date_to, "W"), expected)

    def test_generate_dates_weekly_starts_midweek(self):
        date_from = datetime.datetime(2023, 1, 4)  # A Wednesday
        date_to = datetime.datetime(
            2023, 1, 18
        )  # Through two full Mondays after advance
        # date_from (Wed) advances by (7-2)%7 = 5 days -> Mon Jan 9
        # Expects: Mon Jan 9, Mon Jan 16
        expected = [
            datetime.datetime(2023, 1, 9),
            datetime.datetime(2023, 1, 16),
        ]
        self.assertEqual(generate_dates(date_from, date_to, "W"), expected)

    def test_generate_dates_monthly_starts_on_1st(self):
        date_from = datetime.datetime(2023, 1, 1)
        date_to = datetime.datetime(2023, 3, 1)
        expected = [
            datetime.datetime(2023, 1, 1),
            datetime.datetime(2023, 2, 1),
            datetime.datetime(2023, 3, 1),
        ]
        self.assertEqual(generate_dates(date_from, date_to, "M"), expected)

    def test_generate_dates_monthly_starts_midmonth(self):
        date_from = datetime.datetime(2023, 1, 15)
        date_to = datetime.datetime(2023, 3, 15)
        # date_from (Jan 15) advances to Feb 1
        # Expects: Feb 1, Mar 1
        expected = [
            datetime.datetime(2023, 2, 1),
            datetime.datetime(2023, 3, 1),
        ]
        self.assertEqual(generate_dates(date_from, date_to, "M"), expected)

    def test_generate_dates_invalid_resolution(self):
        with self.assertRaises(ValueError):
            generate_dates(datetime.datetime.now(), datetime.datetime.now(), "X")

    def test_generate_dates_end_date_before_start_date(self):
        date_from = datetime.datetime(2023, 1, 5)
        date_to = datetime.datetime(2023, 1, 1)
        self.assertEqual(generate_dates(date_from, date_to, "D"), [])

    def test_generate_dates_exact_match_start_end_daily(self):
        date_from = datetime.datetime(2023, 1, 1)
        self.assertEqual(generate_dates(date_from, date_from, "D"), [date_from])

    def test_generate_dates_exact_match_start_end_weekly_is_start_of_week(self):
        date_from = datetime.datetime(2023, 1, 2)  # Monday
        # generate_dates advances date_from by 0 days. date (2nd) <= date_to (2nd) is true.
        # Appends Jan 2. Then date becomes Jan 9. date <= date_to is false.
        self.assertEqual(generate_dates(date_from, date_from, "W"), [date_from])

    def test_generate_dates_exact_match_start_end_weekly_not_start_of_week(self):
        date_from = datetime.datetime(2023, 1, 3)  # Tuesday
        date_to = datetime.datetime(2023, 1, 3)  # Tuesday
        # generate_dates advances date_from to next Monday (Jan 9).
        # date (Jan 9) <= date_to (Jan 3) is false. Returns [].
        self.assertEqual(generate_dates(date_from, date_to, "W"), [])

    def test_generate_dates_exact_match_start_end_monthly_is_1st(self):
        date_from = datetime.datetime(2023, 1, 1)
        self.assertEqual(generate_dates(date_from, date_from, "M"), [date_from])

    def test_generate_dates_exact_match_start_end_monthly_not_1st(self):
        date_from = datetime.datetime(2023, 1, 5)
        date_to = datetime.datetime(2023, 1, 5)
        # generate_dates advances date_from to Feb 1st.
        # date (Feb 1) <= date_to (Jan 5) is false. Returns [].
        self.assertEqual(generate_dates(date_from, date_to, "M"), [])


@patch("etl.main.etl_load_internet_quality")
@patch("etl.main.etl_load_traffic")
@patch("etl.main.etl_load_asn_neighbours")
@patch("etl.main.etl_load_stats_5m")
@patch("etl.main.etl_load_stats_1d")
@patch("etl.main.etl_load_asns")
@patch(
    "etl.main.ALL_COUNTRIES", MOCK_ALL_COUNTRIES_DICT
)  # Mock ALL_COUNTRIES used by main
class TestMainFunction(unittest.TestCase):

    def run_main_with_args(self, args_list):
        with patch("sys.argv", args_list):
            main()

    def test_main_dispatches_asns_task(self, mock_load_asns, _m1, _m2, _m3, _m4, _m5):
        args = [
            "main.py",
            "--task",
            "ASNS",
            "--countries",
            "US",
            "CA",
            "--date-from",
            "2023-01-01",
            "--date-to",
            "2023-01-02",
            "--date-resolution",
            "D",
        ]

        expected_dates = [datetime.datetime(2023, 1, 1), datetime.datetime(2023, 1, 2)]

        self.run_main_with_args(args)

        mock_load_asns.assert_any_call("US", expected_dates)
        mock_load_asns.assert_any_call("CA", expected_dates)
        self.assertEqual(mock_load_asns.call_count, 2)

    def test_main_dispatches_stats1d_task(
        self, _m0, mock_load_stats_1d, _m2, _m3, _m4, _m5
    ):
        args = [
            "main.py",
            "--task",
            "STATS_1D",
            "--countries",
            "GB",
            "--date-from",
            "2023-03-01",
            "--date-to",
            "2023-03-01",
            "--date-resolution",
            "M",
        ]

        # date_from (Mar 1) is already 1st of month. generate_dates will produce [Mar 1]
        expected_dates = [datetime.datetime(2023, 3, 1)]

        self.run_main_with_args(args)
        # main.py calls etl_load_stats_1d(iso2, dates_list) due to the bug
        mock_load_stats_1d.assert_called_once_with("GB", expected_dates)

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_main_dispatches_all_countries_asns(
        self, mock_stdout, mock_load_asns, _m1, _m2, _m3, _m4, _m5
    ):
        args = [
            "main.py",
            "--task",
            "ASNS",
            "--countries",
            "all",
            "--date-from",
            "2023-01-01",
            "--date-to",
            "2023-01-01",
            "--date-resolution",
            "D",
        ]

        expected_dates = [datetime.datetime(2023, 1, 1)]

        self.run_main_with_args(args)

        self.assertEqual(mock_load_asns.call_count, len(MOCK_ALL_COUNTRIES_DICT))
        for country_code in MOCK_ALL_COUNTRIES_DICT.keys():
            mock_load_asns.assert_any_call(country_code, expected_dates)

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_main_invalid_task(self, mock_stdout, _m0, _m1, _m2, _m3, _m4, _m5):
        args = [
            "main.py",
            "--task",
            "INVALID_TASK",
            "--countries",
            "US",
            "--date-from",
            "2023-01-01",
            "--date-to",
            "2023-01-01",
            "--date-resolution",
            "D",
        ]
        self.run_main_with_args(args)
        self.assertIn("Error: Unknown task 'INVALID_TASK'", mock_stdout.getvalue())

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_main_invalid_date_format(self, mock_stdout, _m0, _m1, _m2, _m3, _m4, _m5):
        args = [
            "main.py",
            "--task",
            "ASNS",
            "--countries",
            "US",
            "--date-from",
            "2023/01/01",
            "--date-to",
            "2023-01-01",
            "--date-resolution",
            "D",
        ]
        self.run_main_with_args(args)
        self.assertIn(
            "Error: Dates must be in YYYY-MM-DD format.", mock_stdout.getvalue()
        )

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_main_invalid_resolution(self, mock_stdout, _m0, _m1, _m2, _m3, _m4, _m5):
        args = [
            "main.py",
            "--task",
            "ASNS",
            "--countries",
            "US",
            "--date-from",
            "2023-01-01",
            "--date-to",
            "2023-01-01",
            "--date-resolution",
            "X",
        ]
        self.run_main_with_args(args)
        self.assertIn("Error: Unknown resolution 'X'", mock_stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
