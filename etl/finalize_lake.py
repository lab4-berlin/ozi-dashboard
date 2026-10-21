#!/usr/bin/env python3
import os
import sys
import time

# Ensure workspace root is in python path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from common.lake import get_lake_connection


def finalize_materialized_tables(con=None):
    """
    Recomputes MV-equivalent plain tables in DuckLake.
    Orders execution:
      1. vm_current_asn (distinct latest ASNs)
      2. vm_asn_neighbour (joined with vm_current_asn)
      3. vm_connectivity_index_by_country
      4. vm_connectivity_index_by_asn_top10
      5. vm_connectivity_index_distinct (pre-aggregated for fast Dash queries)
    """
    close_con = False
    if con is None:
        con = get_lake_connection(role="writer", read_only=False)
        close_con = True

    start_total = time.time()
    try:
        print("Starting DuckLake finalization (rebuilding vm_* tables)...")

        # 1. vm_current_asn
        t0 = time.time()
        print("Rebuilding data.vm_current_asn...")
        con.execute(
            """
            CREATE OR REPLACE TABLE data.vm_current_asn AS
            SELECT DISTINCT ON (a_ripe_id)
                a_ripe_id AS asn_id,
                a_date AS last_updated,
                a_country_iso2 AS asn_country
            FROM data.asn
            ORDER BY a_ripe_id, a_date DESC;
            """
        )
        cnt1 = con.execute("SELECT count(*) FROM data.vm_current_asn;").fetchone()[0]
        print(f"data.vm_current_asn rebuilt in {time.time()-t0:.2f}s ({cnt1} rows).")

        # 2. vm_asn_neighbour
        t0 = time.time()
        print("Rebuilding data.vm_asn_neighbour...")
        con.execute(
            """
            CREATE OR REPLACE TABLE data.vm_asn_neighbour AS
            SELECT n.an_date,
                   n.an_asn,
                   a1.asn_country,
                   n.an_neighbour,
                   COALESCE(a2.asn_country, 'UNKNOWN') AS neighbour_country,
                   CASE WHEN a1.asn_country <> COALESCE(a2.asn_country, 'UNKNOWN') THEN true ELSE false END AS is_foreign_neighbour,
                   n.an_type,
                   n.an_power,
                   n.an_v4_peers,
                   n.an_v6_peers
            FROM data.asn_neighbour n
            LEFT JOIN data.vm_current_asn a1 ON a1.asn_id = n.an_asn
            LEFT JOIN data.vm_current_asn a2 ON a2.asn_id = n.an_neighbour
            WHERE n.an_type IN ('left', 'right');
            """
        )
        cnt2 = con.execute("SELECT count(*) FROM data.vm_asn_neighbour;").fetchone()[0]
        print(f"data.vm_asn_neighbour rebuilt in {time.time()-t0:.2f}s ({cnt2} rows).")

        # 3. vm_connectivity_index_by_country
        t0 = time.time()
        print("Rebuilding data.vm_connectivity_index_by_country...")
        con.execute(
            """
            CREATE OR REPLACE TABLE data.vm_connectivity_index_by_country AS
            SELECT asn_country,
                   an_date AS date,
                   count(DISTINCT an_asn) AS asn_count,
                   sum(CASE WHEN is_foreign_neighbour THEN 1 ELSE 0 END) AS foreign_neighbour_count,
                   sum(CASE WHEN NOT is_foreign_neighbour THEN 1 ELSE 0 END) AS local_neighbour_count,
                   count(*) AS total_neighbour_count,
                   (sum(CASE WHEN is_foreign_neighbour THEN 1 ELSE 0 END)::DOUBLE / count(*)::DOUBLE) AS foreign_neighbours_share
            FROM data.vm_asn_neighbour
            WHERE asn_country IS NOT NULL
            GROUP BY asn_country, an_date;
            """
        )
        cnt3 = con.execute("SELECT count(*) FROM data.vm_connectivity_index_by_country;").fetchone()[0]
        print(f"data.vm_connectivity_index_by_country rebuilt in {time.time()-t0:.2f}s ({cnt3} rows).")

        # 4. vm_connectivity_index_by_asn_top10
        t0 = time.time()
        print("Rebuilding data.vm_connectivity_index_by_asn_top10...")
        con.execute(
            """
            CREATE OR REPLACE TABLE data.vm_connectivity_index_by_asn_top10 AS
            SELECT an_asn,
                   an_date,
                   asn_country,
                   foreign_neighbour_count,
                   local_neighbour_count,
                   total_neighbour_count,
                   foreign_neighbours_share,
                   rn
            FROM (
                SELECT an_asn,
                       an_date,
                       asn_country,
                       sum(CASE WHEN is_foreign_neighbour THEN 1 ELSE 0 END) AS foreign_neighbour_count,
                       sum(CASE WHEN NOT is_foreign_neighbour THEN 1 ELSE 0 END) AS local_neighbour_count,
                       count(*) AS total_neighbour_count,
                       (sum(CASE WHEN is_foreign_neighbour THEN 1 ELSE 0 END)::DOUBLE / count(*)::DOUBLE) AS foreign_neighbours_share,
                       row_number() OVER (PARTITION BY asn_country, an_date ORDER BY count(*) DESC) AS rn
                FROM data.vm_asn_neighbour
                WHERE asn_country IS NOT NULL
                GROUP BY an_asn, an_date, asn_country
            ) sub
            WHERE rn <= 10;
            """
        )
        cnt4 = con.execute("SELECT count(*) FROM data.vm_connectivity_index_by_asn_top10;").fetchone()[0]
        print(f"data.vm_connectivity_index_by_asn_top10 rebuilt in {time.time()-t0:.2f}s ({cnt4} rows).")

        # 5. vm_connectivity_index_distinct (for Dash)
        t0 = time.time()
        print("Rebuilding data.vm_connectivity_index_distinct...")
        con.execute(
            """
            CREATE OR REPLACE TABLE data.vm_connectivity_index_distinct AS
            SELECT asn_country,
                   an_date AS date,
                   count(DISTINCT an_asn) AS asn_count,
                   sum(CASE WHEN is_foreign_neighbour THEN 1 ELSE 0 END) AS foreign_neighbour_count,
                   sum(CASE WHEN NOT is_foreign_neighbour THEN 1 ELSE 0 END) AS local_neighbour_count,
                   count(*) AS total_neighbour_count,
                   round(sum(CASE WHEN is_foreign_neighbour THEN 1 ELSE 0 END)::DOUBLE / NULLIF(count(*), 0)::DOUBLE * 100::DOUBLE) AS foreign_share_pct
            FROM (
                SELECT DISTINCT an_asn,
                               an_neighbour,
                               an_date,
                               asn_country,
                               is_foreign_neighbour
                FROM data.vm_asn_neighbour
            ) deduplicated
            GROUP BY asn_country, an_date;
            """
        )
        cnt5 = con.execute("SELECT count(*) FROM data.vm_connectivity_index_distinct;").fetchone()[0]
        print(f"data.vm_connectivity_index_distinct rebuilt in {time.time()-t0:.2f}s ({cnt5} rows).")

        print(f"DuckLake finalization complete in {time.time()-start_total:.2f}s.")
    finally:
        if close_con:
            con.close()


if __name__ == "__main__":
    finalize_materialized_tables()
