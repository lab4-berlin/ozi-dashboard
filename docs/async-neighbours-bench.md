---
layout: default
---
# Async ASN-neighbours pipeline — testing & benchmarking

The `ASN_NEIGHBOURS` ETL job has an async implementation built on `httpx` +
`tenacity`, gated behind the `--async-ripe` flag on `main.py`. This document
explains how to verify it produces the same data as the sync version and how to
measure the speedup.

## What it does

- Single shared `httpx.AsyncClient` per process with a bounded connection pool
  (`Limits(max_connections=N)`) plus an `asyncio.Semaphore(N)` as defence in
  depth.
- Default concurrency `N = 6`, configurable via `OZI_RIPE_CONCURRENCY`.
  RIPEstat's hard cap is 8 concurrent requests per IP.
- Per-call retry with exponential backoff + jitter (max 6 attempts), honoring
  the `Retry-After` header on `429` responses; retries also fire on `5xx`,
  transport errors, timeouts, and JSON decode errors.
- Per-date fan-out: the ASN list is fetched once per date, then one
  neighbour request is launched per ASN and consumed via
  `asyncio.as_completed`, so completed batches start flowing to the DB while
  later requests are still in flight.
- DB writes stay synchronous (`psycopg2` via `insert_country_asn_neighbours_to_db`).

## Tunable env vars

| Variable | Default | Meaning |
|---|---|---|
| `OZI_RIPE_CONCURRENCY` | `6` | Concurrent in-flight requests. Hard cap is 8/IP. |
| `OZI_RIPE_TIMEOUT` | `30` | Total request timeout (s). |
| `OZI_RIPE_CONNECT_TIMEOUT` | `5` | Connect timeout (s). |
| `OZI_RIPE_MAX_ATTEMPTS` | `6` | Total tenacity attempts per request. |
| `OZI_RIPE_BACKOFF_INITIAL` | `1` | Backoff initial delay (s). |
| `OZI_RIPE_BACKOFF_MAX` | `60` | Backoff cap (s). |
| `OZI_RIPE_USER_AGENT` | `ozi-dashboard-etl/1.0 (+...)` | Sent on every request. |

## Step-by-step

### 1. Install the new deps

In your venv:

```bash
cd etl
pip install -r requirements.txt -r requirements-dev.txt
```

Or with Docker: `docker compose build ozi-etl`.

### 2. Run the unit tests (fast, no network, no DB)

```bash
cd etl
python -m pytest test_ripe_api_async.py -v
```

Expect 9 passed in well under a second. These cover retry, 429
`Retry-After` handling, transport/JSON errors, final-failure behaviour, and
that the concurrency cap is enforced.

### 3. Run the side-by-side bench (live RIPE, no DB writes)

The bench script runs both implementations against the same workload,
collects every batch into memory (DB bypassed), and asserts set-equality on
`(asn_req, asn, date, type, power, v4_peers, v6_peers)`.

Smoke run — small country, a few weeks (well under a minute):

```bash
cd etl
python bench_neighbours.py --country AM --date-from 2024-01-01 --date-to 2024-01-31 --resolution W
```

Representative run — a full year of a mid-sized country:

```bash
python bench_neighbours.py --country LV --date-from 2024-01-01 --date-to 2024-12-31 --resolution W
```

Stress run — a full year of a large country:

```bash
python bench_neighbours.py --country UA --date-from 2024-01-01 --date-to 2024-12-31 --resolution W
```

Sample output:

```
=== RIPE neighbours bench ===
  country     : LV
  date range  : 2024-01-01 .. 2024-12-31  (W)
  dates       : 52
  concurrency : 6 (OZI_RIPE_CONCURRENCY)
  order       : sync-first

--- sync ---
  wall_time       : <T_sync> s
  rows_returned   : ...
  unique_rows     : ...
  requests        : ...

--- async ---
  wall_time       : <T_async> s
  rows_returned   : ...
  unique_rows     : ...
  requests        : ...
  retries         : ...
  status_429      : ...
  status_5xx      : ...
  transport_errors: ...
  json_errors     : ...
  final_failures  : ...

speedup (sync / async): <T_sync / T_async>x

--- Equivalence ---
  sync unique rows  : N
  async unique rows : N
  intersection      : N
  only in sync      : 0
  only in async     : 0
  result            : OK (sets are identical)
```

The script exits `0` on identical sets and `1` on any mismatch (with up to 5
sample diffs printed for each side).

### 4. (Optional) Rule out RIPE-side drift

Run the bench a second time with reversed order to confirm the "only-in-X"
counts stay zero independent of who ran first:

```bash
python bench_neighbours.py --country LV --date-from 2024-01-01 --date-to 2024-12-31 --resolution W --order async-first
```

If both orders give zero diff, any later mismatch is a real bug.

### 5. (Optional) Tune concurrency

```bash
OZI_RIPE_CONCURRENCY=4 python bench_neighbours.py ...
OZI_RIPE_CONCURRENCY=7 python bench_neighbours.py ...
```

If `status_429` starts climbing, dial it back.

### 6. Try the new path end-to-end (writes to DB)

Same args as the usual `main.py` invocation, with the new flag added:

```bash
python main.py --task ASN_NEIGHBOURS --countries LV \
    --date-from 2024-12-01 --date-to 2024-12-31 \
    --date-resolution W --async-ripe
```

`insert_country_asn_neighbours_to_db` already de-dupes against the DB, so it's
safe to re-run on a date range that's already been loaded.

### 7. Cleanup once verified

After the bench is green and one production cycle has run with `--async-ripe`,
the sync neighbour code path can be deleted: `get_list_of_asn_neighbours_for_country`
in `etl_jobs.py`, the `--async-ripe` flag itself, and `etl_load_asn_neighbours`
collapses to the async-only version.
