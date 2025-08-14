import unittest
from datetime import datetime
from sqlalchemy import create_engine, text
import time
import os
from load_to_database import (
    insert_country_asns_to_db,
    insert_country_stats_to_db,
    insert_country_asn_neighbours_to_db,
    insert_traffic_for_country_to_db,
    insert_internet_quality_for_country_to_db,
)

# Database connection details (from docker-compose.yml)
DB_HOST = os.environ.get("OZI_DATABASE_HOST", "ozi-postgres")
DB_PORT = 5432
DB_NAME = os.environ.get("OZI_DATABASE_NAME", "ozi_db2")
DB_USER = os.environ.get("OZI_DATABASE_USER", "ozi")
DB_PASS = os.environ.get("OZI_DATABASE_PASSWORD", "ozi_password")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

class TestLoadToDatabase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create a database engine for the test class
        cls.engine = create_engine(DATABASE_URL)
        # Wait for the database to be ready and schema to exist
        max_retries = 10
        retry_delay_seconds = 5
        for i in range(max_retries):
            try:
                with cls.engine.connect() as connection:
                    connection.execute(text("SELECT 1 FROM data.asn LIMIT 1;"))
                    print(f"Schema 'data' and table 'data.asn' accessible after {i+1} attempts.")
                    break
            except Exception as e:
                print(f"Database connection failed: {e}, retrying in {retry_delay_seconds} seconds... (Attempt {i+1}/{max_retries})")
            time.sleep(retry_delay_seconds)
        else:
            raise Exception("Could not connect to database or find 'data' schema after multiple retries.")

    def setUp(self):
        # Clear tables before each test to ensure a clean state
        with self.engine.connect() as connection:
            connection.execute(text("TRUNCATE TABLE data.asn CASCADE;"))
            connection.execute(text("TRUNCATE TABLE data.country_stat CASCADE;"))
            connection.execute(text("TRUNCATE TABLE data.asn_neighbour CASCADE;"))
            connection.execute(text("TRUNCATE TABLE data.country_traffic CASCADE;"))
            connection.execute(text("TRUNCATE TABLE data.country_internet_quality CASCADE;"))
            connection.commit()

    def test_insert_country_asns_to_db_no_duplicates(self):
        country_iso2 = "US"
        list_of_asns = [
            {"asn": 123, "date": "2023-01-01", "is_routed": True},
            {"asn": 456, "date": "2023-01-01", "is_routed": False},
        ]

        insert_country_asns_to_db(country_iso2, list_of_asns)
        insert_country_asns_to_db(country_iso2, list_of_asns)  # Attempt to insert duplicates

        with self.engine.connect() as connection:
            result = connection.execute(text("SELECT COUNT(*) FROM data.asn;")).scalar()
            self.assertEqual(result, len(list_of_asns))

            # Verify the content
            asns_in_db = connection.execute(text("SELECT a_ripe_id, a_date, a_is_routed FROM data.asn ORDER BY a_ripe_id;")).fetchall()
            expected_asns = sorted([(item["asn"], datetime.strptime(item["date"], "%Y-%m-%d").date(), item["is_routed"]) for item in list_of_asns])
            # Convert datetime.datetime to datetime.date for comparison
            asns_in_db_dates_converted = [(asn, date.date() if isinstance(date, datetime) else date, is_routed) for asn, date, is_routed in asns_in_db]
            self.assertEqual(asns_in_db_dates_converted, expected_asns)

    def test_insert_country_stats_to_db_no_duplicates(self):
        country_iso2 = "DE"
        resolution = "1d"
        stats = [
            {"timeline": [{"starttime": "2023-01-01T00:00:00Z"}], "v4_prefixes_ris": 10, "v6_prefixes_ris": 5, "asns_ris": 2, "v4_prefixes_stats": 100, "v6_prefixes_stats": 50, "asns_stats": 20},
            {"timeline": [{"starttime": "2023-01-02T00:00:00Z"}], "v4_prefixes_ris": 11, "v6_prefixes_ris": 6, "asns_ris": 3, "v4_prefixes_stats": 101, "v6_prefixes_stats": 51, "asns_stats": 21},
        ]

        insert_country_stats_to_db(country_iso2, resolution, stats)
        insert_country_stats_to_db(country_iso2, resolution, stats) # Attempt to insert duplicates

        with self.engine.connect() as connection:
            result = connection.execute(text("SELECT COUNT(*) FROM data.country_stat;")).scalar()
            self.assertEqual(result, len(stats))

            # Verify content (simplified check)
            stats_in_db = connection.execute(text("SELECT cs_stats_timestamp FROM data.country_stat ORDER BY cs_stats_timestamp;")).fetchall()
            expected_timestamps = sorted([datetime.strptime(item["timeline"][0]["starttime"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=None) for item in stats])
            self.assertEqual([ts[0] for ts in stats_in_db], expected_timestamps)

    def test_insert_country_asn_neighbours_to_db_no_duplicates(self):
        country_iso2 = "JP"
        neighbours = [
            {"asn_req": 1, "asn": 123, "date": "2023-01-01", "type": "peer", "power": 10, "v4_peers": 5, "v6_peers": 5},
            {"asn_req": 2, "asn": 456, "date": "2023-01-01", "type": "cust", "power": 20, "v4_peers": 10, "v6_peers": 10},
        ]

        insert_country_asn_neighbours_to_db(country_iso2, neighbours)
        insert_country_asn_neighbours_to_db(country_iso2, neighbours) # Attempt to insert duplicates

        with self.engine.connect() as connection:
            result = connection.execute(text("SELECT COUNT(*) FROM data.asn_neighbour;")).scalar()
            self.assertEqual(result, len(neighbours))

            # Verify content (simplified check)
            neighbours_in_db = connection.execute(text("SELECT an_asn, an_neighbour, an_date, an_type FROM data.asn_neighbour ORDER BY an_asn, an_neighbour;")).fetchall()
            expected_neighbours = sorted([(item["asn_req"], item["asn"], datetime.strptime(item["date"], "%Y-%m-%d").date(), item["type"]) for item in neighbours])
            # Convert datetime.datetime to datetime.date for comparison
            neighbours_in_db_dates_converted = [(asn_req, asn, date.date() if isinstance(date, datetime) else date, type) for asn_req, asn, date, type in neighbours_in_db]
            self.assertEqual(neighbours_in_db_dates_converted, expected_neighbours)

    def test_insert_traffic_for_country_to_db_no_duplicates(self):
        country_iso2 = "BR"
        traffic = {
            "timestamps": ["2023-01-01T00:00:00Z", "2023-01-02T00:00:00Z"],
            "values": [100, 200]
        }

        insert_traffic_for_country_to_db(country_iso2, traffic)
        insert_traffic_for_country_to_db(country_iso2, traffic) # Attempt to insert duplicates

        with self.engine.connect() as connection:
            result = connection.execute(text("SELECT COUNT(*) FROM data.country_traffic;")).scalar()
            self.assertEqual(result, len(traffic["timestamps"]))

            # Verify content (simplified check)
            traffic_in_db = connection.execute(text("SELECT cr_date, cr_traffic FROM data.country_traffic ORDER BY cr_date;")).fetchall()
            expected_traffic = sorted([(datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=None), val) for ts, val in zip(traffic["timestamps"], traffic["values"])])
            # Convert datetime.datetime to remove timezone for comparison
            traffic_in_db_converted = [(ts.replace(tzinfo=None) if isinstance(ts, datetime) else ts, val) for ts, val in traffic_in_db]
            self.assertEqual(traffic_in_db_converted, expected_traffic)

    def test_insert_internet_quality_for_country_to_db_no_duplicates(self):
        country_iso2 = "IN"
        internet_quality = {
            "timestamps": ["2023-01-01T00:00:00Z", "2023-01-02T00:00:00Z"],
            "p75": [10, 11],
            "p50": [5, 6],
            "p25": [2, 3],
        }

        insert_internet_quality_for_country_to_db(country_iso2, internet_quality)
        insert_internet_quality_for_country_to_db(country_iso2, internet_quality) # Attempt to insert duplicates

        with self.engine.connect() as connection:
            result = connection.execute(text("SELECT COUNT(*) FROM data.country_internet_quality;")).scalar()
            self.assertEqual(result, len(internet_quality["timestamps"]))

            # Verify content (simplified check)
            quality_in_db = connection.execute(text("SELECT ci_date, ci_p75, ci_p50, ci_p25 FROM data.country_internet_quality ORDER BY ci_date;")).fetchall()
            expected_quality = sorted([
                (datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=None), p75, p50, p25)
                for ts, p75, p50, p25 in zip(internet_quality["timestamps"], internet_quality["p75"], internet_quality["p50"], internet_quality["p25"])
            ])
            # Convert datetime.datetime to remove timezone for comparison
            quality_in_db_converted = [(ts.replace(tzinfo=None) if isinstance(ts, datetime) else ts, p75, p50, p25) for ts, p75, p50, p25 in quality_in_db]
            self.assertEqual(quality_in_db_converted, expected_quality)

if __name__ == "__main__":
    unittest.main()
