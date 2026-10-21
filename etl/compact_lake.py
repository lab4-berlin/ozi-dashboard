#!/usr/bin/env python3
import os
import sys
import time

# Ensure workspace root is in python path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from common.lake import get_lake_connection


def compact_and_clean_lake(con=None):
    """
    Runs DuckLake maintenance via the bundled CHECKPOINT statement:
      1. Flushes inlined data
      2. Expires snapshots older than retention threshold (default 30 days)
      3. Merges adjacent small Parquet files
      4. Rewrites files exceeding deleted-row threshold (reclaiming delete tombstones)
      5. Cleans up expired data files from storage
      6. Deletes untracked orphaned files
    Followed by an inventory/size report via DuckLake metadata.
    """
    close_con = False
    if con is None:
        con = get_lake_connection(role="writer", read_only=False)
        close_con = True

    t0 = time.time()
    try:
        print("Starting DuckLake maintenance checkpoint...")
        # Ensure retention and compaction thresholds are set
        con.execute("CALL ozi.set_option('expire_older_than', '30 days');")
        con.execute("CALL ozi.set_option('delete_older_than', '1 day');")
        con.execute("CALL ozi.set_option('rewrite_delete_threshold', 0.2);")

        # Execute bundled maintenance checkpoint
        con.execute("CHECKPOINT ozi;")
        print(f"Maintenance checkpoint completed in {time.time()-t0:.2f}s.")

        # Print storage summary / table size report
        print("\n--- DuckLake Table Status Report ---")
        tables = con.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'data'
            ORDER BY table_name;
            """
        ).fetchall()

        for (tbl,) in tables:
            try:
                row_cnt = con.execute(f"SELECT count(*) FROM data.{tbl};").fetchone()[0]
                print(f"  data.{tbl:<35} : {row_cnt:>10} rows")
            except Exception as e:
                print(f"  data.{tbl:<35} : error ({e})")

        print("------------------------------------\n")
    finally:
        if close_con:
            con.close()


if __name__ == "__main__":
    compact_and_clean_lake()
