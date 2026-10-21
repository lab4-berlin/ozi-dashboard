#!/usr/bin/env python3
import os
import sys
import time

# Ensure workspace root is in python path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from common.lake import get_lake_connection
from etl.finalize_lake import finalize_materialized_tables

# Postgres credentials
PG_HOST = os.getenv("POSTGRES_HOST", "ozi-postgres")
PG_PORT = os.getenv("POSTGRES_PORT", "5432")
PG_USER = os.getenv("POSTGRES_OZI_USER", os.getenv("POSTGRES_USER", "ozi"))
PG_PASSWORD = os.getenv("POSTGRES_OZI_PASSWORD", os.getenv("POSTGRES_PASSWORD", "ozi_password"))
PG_DB = os.getenv("POSTGRES_DB", "ozi_db2")

TABLES_TO_MIGRATE = [
    "country",
    "country_tag",
    "etl_load",
    "asn",
    "asn_neighbour",
    "country_stat",
    "country_traffic",
    "country_internet_quality",
]


def migrate_pg_to_lake():
    """
    Migrates all data tables from PostgreSQL to DuckLake using DuckDB's postgres_scanner.
    Generates a row-count parity validation report.
    """
    print("=" * 60)
    print("Postgres → DuckLake Migration via postgres_scanner")
    print(f"Source: postgres://{PG_USER}@{PG_HOST}:{PG_PORT}/{PG_DB}")
    print("=" * 60)

    con = get_lake_connection(role="writer", read_only=False)
    try:
        # Load postgres scanner
        con.execute("LOAD postgres_scanner;")

        # Attach Postgres source
        pg_conn_str = f"dbname={PG_DB} user={PG_USER} password={PG_PASSWORD} host={PG_HOST} port={PG_PORT}"
        print("Attaching Postgres database...")
        con.execute(f"ATTACH '{pg_conn_str}' AS pg (TYPE postgres);")

        parity_report = []

        for tbl in TABLES_TO_MIGRATE:
            print(f"\nMigrating table: data.{tbl}...")
            t0 = time.time()

            # Check source count
            pg_count = con.execute(f"SELECT count(*) FROM pg.data.{tbl};").fetchone()[0]

            # Clear destination table first if re-running
            con.execute(f"TRUNCATE TABLE ozi.data.{tbl};")

            # Copy data using postgres_scanner
            con.execute(f"INSERT INTO ozi.data.{tbl} SELECT * FROM pg.data.{tbl};")
            elapsed = time.time() - t0

            # Verify lake count
            lake_count = con.execute(f"SELECT count(*) FROM ozi.data.{tbl};").fetchone()[0]
            status = "MATCH" if pg_count == lake_count else "MISMATCH"

            parity_report.append((tbl, pg_count, lake_count, status, elapsed))
            print(f"  Copied {lake_count} rows in {elapsed:.2f}s [{status}].")

        # Detach Postgres
        con.execute("DETACH pg;")

        # Run finalization to compute vm_* tables
        print("\nRebuilding materialized views/tables in DuckLake...")
        finalize_materialized_tables(con)

        # Print final validation summary
        print("\n" + "=" * 65)
        print(f"{'Table':<30} | {'Postgres':>10} | {'DuckLake':>10} | {'Status':>8}")
        print("-" * 65)
        all_matched = True
        for tbl, pg_cnt, lake_cnt, status, _ in parity_report:
            print(f"{tbl:<30} | {pg_cnt:>10} | {lake_cnt:>10} | {status:>8}")
            if status != "MATCH":
                all_matched = False
        print("=" * 65)

        if all_matched:
            print("Migration completed successfully with 100% row-count parity!")
        else:
            print("WARNING: Some tables had row-count mismatches. Review logs above.", file=sys.stderr)
            sys.exit(1)
    finally:
        con.close()


if __name__ == "__main__":
    migrate_pg_to_lake()
