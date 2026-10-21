import os
import sys
import unittest
import tempfile
import shutil
from datetime import datetime

# Add root directory to python path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)


class TestLoadToLake(unittest.TestCase):
    def setUp(self):
        # Create temporary isolated directory for SQLite catalog and local lake Parquet storage
        self.test_dir = tempfile.mkdtemp(prefix="test_lake_")
        self.catalog_path = os.path.join(self.test_dir, "test_lake.sqlite")
        self.data_path = os.path.join(self.test_dir, "data_files/")
        os.makedirs(self.data_path, exist_ok=True)

        # Set environment variables for isolated test lake
        os.environ["OZI_LAKE_CATALOG"] = self.catalog_path
        os.environ["OZI_LAKE_DATA_PATH"] = self.data_path
        os.environ["OZI_DUCKDB_WRITER_MEM_LIMIT"] = "256MB"
        os.environ["OZI_DUCKDB_READER_MEM_LIMIT"] = "128MB"

        # Initialize lake catalog & schema
        from etl.init_lake import init_sqlite_wal, apply_schema, configure_catalog_options, seed_countries
        from common.lake import get_lake_connection

        init_sqlite_wal(self.catalog_path)
        self.con = get_lake_connection(role="writer", read_only=False)
        configure_catalog_options(self.con)
        apply_schema(self.con, os.path.join(ROOT_DIR, "lake_schema.sql"))
        seed_countries(self.con, os.path.join(ROOT_DIR, "insert_countries.sql"))

    def tearDown(self):
        if hasattr(self, "con"):
            self.con.close()
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_country_seed(self):
        count = self.con.execute("SELECT count(*) FROM data.country;").fetchone()[0]
        self.assertGreater(count, 200, "Country table should contain seeded countries")

    def test_insert_asns_and_deduplication(self):
        from etl.load_to_lake import insert_country_asns_to_lake, generate_load_id

        load_id = generate_load_id()
        country_iso2 = "US"
        items = [
            {"asn": 1234, "date": "2026-01-01", "is_routed": True},
            {"asn": 5678, "date": "2026-01-01", "is_routed": False},
        ]

        # First insert
        inserted = insert_country_asns_to_lake(country_iso2, items, load_id=load_id, con=self.con)
        self.assertEqual(inserted, 2)

        count = self.con.execute("SELECT count(*) FROM data.asn WHERE a_country_iso2 = 'US';").fetchone()[0]
        self.assertEqual(count, 2)

        # Duplicate insert attempt
        inserted_dups = insert_country_asns_to_lake(country_iso2, items, load_id=load_id, con=self.con)
        self.assertEqual(inserted_dups, 0)

        count_after = self.con.execute("SELECT count(*) FROM data.asn WHERE a_country_iso2 = 'US';").fetchone()[0]
        self.assertEqual(count_after, 2)

    def test_insert_country_stats_and_deduplication(self):
        from etl.load_to_lake import insert_country_stats_to_lake, generate_load_id

        load_id = generate_load_id()
        country_iso2 = "DE"
        stats = [
            {
                "timeline": [{"starttime": "2026-01-01T00:00:00Z"}],
                "v4_prefixes_ris": 100,
                "v6_prefixes_ris": 50,
                "asns_ris": 120,
                "v4_prefixes_stats": 110,
                "v6_prefixes_stats": 55,
                "asns_stats": 125,
            }
        ]

        inserted = insert_country_stats_to_lake(country_iso2, "1d", stats, load_id=load_id, con=self.con)
        self.assertEqual(inserted, 1)

        # Duplicate attempt
        inserted_dups = insert_country_stats_to_lake(country_iso2, "1d", stats, load_id=load_id, con=self.con)
        self.assertEqual(inserted_dups, 0)

        rows = self.con.execute("SELECT cs_country_iso2, cs_stats_resolution FROM data.country_stat;").fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0], ("DE", "1d"))

    def test_insert_asn_neighbours(self):
        from etl.load_to_lake import insert_country_asn_neighbours_to_lake, generate_load_id

        load_id = generate_load_id()
        neighbours = [
            {
                "asn_req": 111,
                "asn": 222,
                "date": "2026-01-01",
                "type": "left",
                "power": 10,
                "v4_peers": 5,
                "v6_peers": 2,
            }
        ]

        inserted = insert_country_asn_neighbours_to_lake("US", neighbours, load_id=load_id, con=self.con)
        self.assertEqual(inserted, 1)

        count = self.con.execute("SELECT count(*) FROM data.asn_neighbour;").fetchone()[0]
        self.assertEqual(count, 1)

    def test_finalize_and_materialized_views(self):
        from etl.load_to_lake import insert_country_asns_to_lake, insert_country_asn_neighbours_to_lake, generate_load_id
        from etl.finalize_lake import finalize_materialized_tables

        load_id = generate_load_id()

        # Seed ASNs for two countries
        insert_country_asns_to_lake("US", [{"asn": 100, "date": "2026-01-01", "is_routed": True}], load_id=load_id, con=self.con)
        insert_country_asns_to_lake("DE", [{"asn": 200, "date": "2026-01-01", "is_routed": True}], load_id=load_id, con=self.con)

        # Seed neighbour relationship between them
        insert_country_asn_neighbours_to_lake(
            "US",
            [{"asn_req": 100, "asn": 200, "date": "2026-01-01", "type": "left", "power": 1, "v4_peers": 1, "v6_peers": 0}],
            load_id=load_id,
            con=self.con,
        )

        # Run finalization
        finalize_materialized_tables(con=self.con)

        # Verify vm_current_asn
        asns = self.con.execute("SELECT asn_id, asn_country FROM data.vm_current_asn ORDER BY asn_id;").fetchall()
        self.assertEqual(asns, [(100, "US"), (200, "DE")])

        # Verify vm_asn_neighbour marks foreign correctly
        nbrs = self.con.execute("SELECT an_asn, an_neighbour, is_foreign_neighbour FROM data.vm_asn_neighbour;").fetchall()
        self.assertEqual(len(nbrs), 1)
        self.assertEqual(nbrs[0], (100, 200, True))

        # Verify vm_connectivity_index_distinct
        distinct_rows = self.con.execute("SELECT asn_country, asn_count, foreign_neighbour_count FROM data.vm_connectivity_index_distinct;").fetchall()
        self.assertEqual(len(distinct_rows), 1)
        self.assertEqual(distinct_rows[0], ("US", 1, 1))

    def test_backout_load(self):
        from etl.load_to_lake import insert_country_asns_to_lake, generate_load_id
        from etl.main import run_backout

        load1 = generate_load_id()
        load2 = generate_load_id()

        insert_country_asns_to_lake("US", [{"asn": 1, "date": "2026-01-01", "is_routed": True}], load_id=load1, con=self.con)
        insert_country_asns_to_lake("US", [{"asn": 2, "date": "2026-01-01", "is_routed": True}], load_id=load2, con=self.con)

        self.assertEqual(self.con.execute("SELECT count(*) FROM data.asn;").fetchone()[0], 2)

        # Backout load1
        run_backout(load1)

        remaining = self.con.execute("SELECT a_ripe_id, load_id FROM data.asn;").fetchall()
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0][0], 2)
        self.assertEqual(remaining[0][1], load2)


if __name__ == "__main__":
    unittest.main()
