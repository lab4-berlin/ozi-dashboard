"""Side-by-side benchmark: sync vs async ASN-neighbours pipeline.

Runs ``get_list_of_asn_neighbours_for_country`` (sync, ``requests``) and
``get_list_of_asn_neighbours_for_country_async`` (async, ``httpx`` + bounded
concurrency) against the live RIPEstat API for the same country/date range,
collecting every batch into memory (DB writes are bypassed). Prints a summary
of timings, request counts, retries, and a set-equality check across the two
result sets.

Example:
    python3 bench_neighbours.py --country AM --date-from 2024-01-01 \\
        --date-to 2024-01-31 --resolution W
"""

import argparse
import asyncio
import time
from datetime import datetime
from typing import List, Tuple

import extract_from_ripe_api as ripe_sync
import extract_from_ripe_api_async as ripe_async
import etl_jobs as jobs_sync
import etl_jobs_async as jobs_async
from main import generate_dates


_NeighbourKey = Tuple


def _row_key(row: dict) -> _NeighbourKey:
    """Build a stable, hashable identity for a neighbour row."""
    return (
        str(row.get("asn_req")),
        str(row.get("asn")),
        row.get("date"),
        row.get("type"),
        row.get("power"),
        row.get("v4_peers"),
        row.get("v6_peers"),
    )


class _SyncCounters:
    """Drop-in counters for the sync code path; mirrors the async STATS dict."""

    def __init__(self):
        self.requests = 0

    def install(self):
        self._orig_call = ripe_sync.ripe_api_call

        def counted(url, params):
            self.requests += 1
            return self._orig_call(url, params)

        ripe_sync.ripe_api_call = counted

    def restore(self):
        ripe_sync.ripe_api_call = self._orig_call


def run_sync(country: str, dates: List[datetime], batch_size: int):
    counters = _SyncCounters()
    counters.install()
    rows: List[dict] = []
    t0 = time.perf_counter()
    try:
        for batch in jobs_sync.get_list_of_asn_neighbours_for_country(
            country, list(dates), batch_size, verbose=False
        ):
            rows.extend(batch)
    finally:
        counters.restore()
    elapsed = time.perf_counter() - t0
    return rows, elapsed, {"requests": counters.requests}


def run_async(country: str, dates: List[datetime], batch_size: int):
    ripe_async.reset_stats()
    rows: List[dict] = []

    async def _drive():
        try:
            async for batch in jobs_async.get_list_of_asn_neighbours_for_country_async(
                country, list(dates), batch_size, verbose=False
            ):
                rows.extend(batch)
        finally:
            await ripe_async.aclose_client()

    t0 = time.perf_counter()
    asyncio.run(_drive())
    elapsed = time.perf_counter() - t0
    return rows, elapsed, ripe_async.snapshot_stats()


def _print_run_summary(label: str, rows: List[dict], elapsed: float, stats: dict):
    print(f"\n--- {label} ---")
    print(f"  wall_time       : {elapsed:.2f} s")
    print(f"  rows_returned   : {len(rows)}")
    print(f"  unique_rows     : {len({_row_key(r) for r in rows})}")
    for k, v in stats.items():
        print(f"  {k:<15} : {v}")


def _print_diff(sync_rows: List[dict], async_rows: List[dict]) -> bool:
    sync_keys = {_row_key(r) for r in sync_rows}
    async_keys = {_row_key(r) for r in async_rows}

    only_sync = sync_keys - async_keys
    only_async = async_keys - sync_keys

    print("\n--- Equivalence ---")
    print(f"  sync unique rows  : {len(sync_keys)}")
    print(f"  async unique rows : {len(async_keys)}")
    print(f"  intersection      : {len(sync_keys & async_keys)}")
    print(f"  only in sync      : {len(only_sync)}")
    print(f"  only in async     : {len(only_async)}")

    ok = not only_sync and not only_async
    if ok:
        print("  result            : OK (sets are identical)")
        return True

    print("  result            : MISMATCH")
    if only_sync:
        print("  sample only-in-sync (up to 5):")
        for k in list(only_sync)[:5]:
            print(f"    {k}")
    if only_async:
        print("  sample only-in-async (up to 5):")
        for k in list(only_async)[:5]:
            print(f"    {k}")
    return False


def main():
    parser = argparse.ArgumentParser(
        description="Compare sync vs async RIPE neighbour pipeline."
    )
    parser.add_argument("--country", required=True)
    parser.add_argument("--date-from", required=True)
    parser.add_argument("--date-to", required=True)
    parser.add_argument(
        "--resolution",
        default="W",
        choices=["D", "W", "M"],
        help="Date resolution: Daily / Weekly / Monthly (default: W).",
    )
    parser.add_argument("--batch-size", type=int, default=1000)
    parser.add_argument(
        "--order",
        choices=["sync-first", "async-first"],
        default="sync-first",
        help="Run order. Run twice (e.g. with --order async-first) to rule out drift.",
    )
    args = parser.parse_args()

    date_from = datetime.strptime(args.date_from, "%Y-%m-%d")
    date_to = datetime.strptime(args.date_to, "%Y-%m-%d")
    dates = generate_dates(date_from, date_to, args.resolution)

    print("=== RIPE neighbours bench ===")
    print(f"  country     : {args.country}")
    print(f"  date range  : {args.date_from} .. {args.date_to}  ({args.resolution})")
    print(f"  dates       : {len(dates)}")
    print(f"  concurrency : {ripe_async.CONCURRENCY} (OZI_RIPE_CONCURRENCY)")
    print(f"  order       : {args.order}")

    if args.order == "sync-first":
        sync_rows, sync_t, sync_stats = run_sync(args.country, dates, args.batch_size)
        async_rows, async_t, async_stats = run_async(
            args.country, dates, args.batch_size
        )
    else:
        async_rows, async_t, async_stats = run_async(
            args.country, dates, args.batch_size
        )
        sync_rows, sync_t, sync_stats = run_sync(args.country, dates, args.batch_size)

    _print_run_summary("sync", sync_rows, sync_t, sync_stats)
    _print_run_summary("async", async_rows, async_t, async_stats)

    if async_t > 0:
        speedup = sync_t / async_t
        print(f"\nspeedup (sync / async): {speedup:.2f}x")

    ok = _print_diff(sync_rows, async_rows)
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
