import unittest
from unittest.mock import patch, MagicMock, call, ANY
import datetime
import os
import urllib

# Functions and constants to test
from etl.load_to_database import (
    insert_country_asns_to_db,
    insert_country_stats_to_db,
    get_db_connection,
    BATCH_SIZE,  # Assuming BATCH_SIZE is relevant for call counts or logic
)


class TestLoadToDatabase(unittest.TestCase):

    @patch("etl.load_to_database.get_db_connection")
    def test_insert_country_asns_to_db_success(self, mock_get_db_connection):
        mock_conn = MagicMock()
        # mock_cursor is not used by the source code's SQLAlchemy Core implementation
        mock_get_db_connection.return_value = mock_conn
        # mock_conn.cursor.return_value = mock_cursor # Not used

        # Corrected sample_asns to match expected structure in load_to_database.py
        sample_asns = [
            {"date": "2023-01-01", "asn": "AS123", "is_routed": True},
            {"date": "2023-01-01", "asn": "AS456", "is_routed": False},
        ]
        country_iso = "US"

        insert_country_asns_to_db(
            country_iso, sample_asns, load_to_database=True, save_sql_to_file=False
        )

        mock_get_db_connection.assert_called_once()
        self.assertTrue(mock_conn.execute.called)  # Assert on mock_conn.execute

        # Verify essential parts of the SQL
        if mock_conn.execute.call_args_list:  # Check mock_conn.execute
            # The actual argument to execute is a sqlalchemy.sql.elements.TextClause
            # We need to access its string representation for assertion.
            sql_text_clause = mock_conn.execute.call_args_list[0][0][0]
            executed_sql_string = str(sql_text_clause)

            self.assertIn("INSERT INTO data.asn", executed_sql_string)
            self.assertIn(
                "(a_country_iso2, a_date, a_ripe_id, a_is_routed)", executed_sql_string
            )
            self.assertIn(
                f"('{country_iso}', '2023-01-01', AS123, True)", executed_sql_string
            )
            self.assertIn(
                f"('{country_iso}', '2023-01-01', AS456, False)", executed_sql_string
            )

        mock_conn.commit.assert_called_once()
        # mock_cursor.close.assert_called_once() # Not used
        # mock_conn.close.assert_called_once() # Source code does not explicitly close connection here

    @patch("etl.load_to_database.get_db_connection")
    def test_insert_country_asns_to_db_no_load(self, mock_get_db_connection):
        # Corrected sample_asns
        sample_asns = [{"date": "2023-01-01", "asn": "AS123", "is_routed": True}]

        insert_country_asns_to_db(
            "US", sample_asns, load_to_database=False, save_sql_to_file=False
        )

        mock_get_db_connection.assert_not_called()

    @patch("etl.load_to_database.get_db_connection")
    def test_insert_country_stats_to_db_success(self, mock_get_db_connection):
        mock_conn = MagicMock()
        # mock_cursor is not used
        mock_get_db_connection.return_value = mock_conn
        # mock_conn.cursor.return_value = mock_cursor # Not used

        # Corrected sample_stats to match expected structure (list of dicts)
        sample_stats = [
            {
                "timeline": [{"starttime": "2023-01-01T00:00:00"}],
                "v4_prefixes_ris": 10,
                "v6_prefixes_ris": 5,
                "asns_ris": 1,
                "v4_prefixes_stats": 12,
                "v6_prefixes_stats": 6,
                "asns_stats": 2,
            },
            {
                "timeline": [{"starttime": "2023-01-02T00:00:00"}],
                "v4_prefixes_ris": 20,
                "v6_prefixes_ris": 15,
                "asns_ris": 11,
                "v4_prefixes_stats": 22,
                "v6_prefixes_stats": 16,
                "asns_stats": 12,
            },
        ]
        country_iso = "US"
        resolution = "1d"

        insert_country_stats_to_db(
            country_iso,
            resolution,
            sample_stats,
            load_to_database=True,
            save_sql_to_file=False,
        )

        mock_get_db_connection.assert_called_once()
        self.assertTrue(mock_conn.execute.called)  # Assert on mock_conn.execute

        # Verify essential parts of the SQL
        if mock_conn.execute.call_args_list:  # Check mock_conn.execute
            sql_text_clause = mock_conn.execute.call_args_list[0][0][0]
            executed_sql_string = str(sql_text_clause)

            self.assertIn("INSERT INTO data.country_stat", executed_sql_string)
            self.assertIn(
                "(cs_country_iso2, cs_stats_timestamp, cs_stats_resolution, cs_v4_prefixes_ris, cs_v6_prefixes_ris, cs_asns_ris, cs_v4_prefixes_stats, cs_v6_prefixes_stats, cs_asns_stats )",
                executed_sql_string,
            )
            # First item should have a space and then a trailing comma
            self.assertIn(
                f"('{country_iso}', '2023-01-01T00:00:00', '{resolution}', 10, 5, 1, 12, 6, 2 ),",
                executed_sql_string,
            )
            # Second item is the last, so it has a space then ')' and then the SQL ends with ';'
            self.assertIn(
                f"('{country_iso}', '2023-01-02T00:00:00', '{resolution}', 20, 15, 11, 22, 16, 12 )",
                executed_sql_string,
            )

        mock_conn.commit.assert_called_once()
        # mock_cursor.close.assert_called_once() # Not used
        # mock_conn.close.assert_called_once() # Source code does not explicitly close connection here

    # Patch module-level constants instead of os.environ
    @patch("etl.load_to_database.USER", "test_user")
    @patch("etl.load_to_database.PASSWORD", "test_password_value_from_patch")
    @patch("etl.load_to_database.HOST", "test_host")
    @patch("etl.load_to_database.PORT", "test_port")
    @patch("etl.load_to_database.DBNAME", "test_db")
    @patch("etl.load_to_database.urllib.parse.quote")
    @patch("etl.load_to_database.create_engine")
    def test_get_db_connection_constructs_string_correctly(
        self, mock_create_engine, mock_urllib_quote
    ):
        mock_urllib_quote.return_value = "quoted_test_password"

        mock_engine = MagicMock()
        mock_connection = MagicMock()
        mock_create_engine.return_value = mock_engine
        mock_engine.connect.return_value = mock_connection

        conn = get_db_connection()

        # Assert that urllib.parse.quote was called with the value from the patched module constant
        mock_urllib_quote.assert_called_once_with("test_password_value_from_patch")
        expected_conn_str = (
            "postgresql://test_user:quoted_test_password@test_host:test_port/test_db"
        )
        mock_create_engine.assert_called_once_with(expected_conn_str)
        mock_engine.connect.assert_called_once()
        self.assertEqual(conn, mock_connection)


if __name__ == "__main__":
    unittest.main()
