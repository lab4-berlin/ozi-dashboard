# OZI Dashboard: Postgres → DuckLake (SQLite catalog + Hetzner Object Storage) migration plan

Date: 2026-10-21 · Status: updated with maintenance bundling & pre-implementation corrections, awaiting implementation

## 1. Goal & constraints

Replace running Postgres as the analytical store with a DuckLake:
- **Catalog**: SQLite (`ozi_lake.sqlite` on a mounted block-storage volume) — multi-process
  readers (Dash) + serialized writers (ETL), chosen over a DuckDB-file catalog because
  DuckDB database files take an exclusive process lock that blocks even READ_ONLY attaches.
  - **Concurrency & Locking**: SQLite catalog MUST have WAL mode enabled (`PRAGMA journal_mode = WAL;`).
    Because journal mode is a persistent file property, `init_lake.py` sets it once via Python's standard `sqlite3` module.
    Connection-level lock contention during writes is handled by **DuckLake's internal retry-with-backoff mechanism**
    (catalog connections are managed internally by the extension, so Python cannot inject per-connection `busy_timeout` PRAGMAs).
- **Storage**: Parquet files on Hetzner Object Storage (S3-compatible, Ceph-backed), `DATA_PATH 's3://<bucket>/ozi_lake/'`.
  - S3 configuration requires `url_style = 'path'` and `use_ssl = true`.
- **Local emulation**: MinIO container (`use_ssl = false`, `url_style = 'path'`), same env-var contract as Hetzner.
  - Bootstrap checks and creates the target bucket idempotently before DuckLake attaches.
- **Transition**: dual-run — old Postgres stays as migration source + verification target.
  - Switchable via `OZI_STORAGE_BACKEND=postgres|lake|both`.
- **Out of scope**: Redash (left completely untouched), `source.api_response` (jsonb cache stays PG-only / unused).
- DuckLake v1.0 (production-ready, ships as `ducklake` extension in DuckDB ≥ 1.5.2).
  - Data inlining keeps small changes in the catalog (threshold: 10 rows); retention/time-travel via snapshots.

## 2. Architecture

```
external APIs ─▶ ozi-etl (duckdb ctx, RW) ──writes──▶ Hetzner Object Storage (prod) / MinIO (local)
                     │ finalize/compaction                                    ▲
                     ▼                                                        │
        precomputed vm_* tables + v_* views                                   │
                     ▲                                      litestream: replicates catalog (path-style)
                     │                                                        │
        plotly-dash (duckdb ctx, READ_ONLY) ────reads────▶ /data/ozi_lake.sqlite (WAL mode)
```

- **Catalog Concurrency**: One DuckLake SQLite catalog; Dash attaches `READ_ONLY`; ETL writes using DuckLake's
  transaction-retry mechanism. Persistent WAL mode ensures non-blocking concurrent reads while writes commit.
- **Time travel**: attach earlier snapshot READ_ONLY, e.g.
  `ATTACH 'ducklake:sqlite:/data/ozi_lake.sqlite' AS ozi_hist (DATA_PATH 's3://…', SNAPSHOT_VERSION n, READ_ONLY)`;
  old Parquet files remain until snapshot expiration and file cleanup.
- **Maintenance Bundling via `CHECKPOINT`**:
  Maintenance does not require orchestrating individual functions. Calling `CHECKPOINT ozi_lake;` with configured catalog
  options sequentially executes:
  `flush_inlined_data` → `expire_snapshots` → `merge_adjacent_files` → `rewrite_data_files` → `cleanup_old_files` → `delete_orphaned_files`.
- **Catalog Backup & Disaster Recovery**: Catalog file never lives on object storage; `-wal`/`-shm` stay next to it.
  - Litestream sidecar container continuously replicates `ozi_lake.sqlite` into the S3 bucket (`catalog_backup/`).
  - Litestream S3 replica uses **path-style addressing** (`path-style: true`) for MinIO and Hetzner Ceph compatibility.
  - Disaster recovery: `litestream restore -o /data/ozi_lake.sqlite s3://<bucket>/catalog_backup/`.
- **Scratch Space Isolation**: DuckDB disk spilling uses container-local ephemeral directories
  (`/tmp/lake_etl`, `/tmp/lake_dash`), rather than a shared volume, eliminating lock collisions.

## 3. New env contract (`.env.ozi`, overlay for compose)

```bash
# Storage & Catalog
OZI_STORAGE_BACKEND=both              # postgres | lake | both (for dual-run)
OZI_LAKE_CATALOG=/data/ozi_lake.sqlite
OZI_LAKE_DATA_PATH=s3://ozi_lake/ozi_lake/
OZI_S3_ENDPOINT=minio:9000            # MinIO: minio:9000 · Hetzner: fsn1.your-objectstorage.com
OZI_S3_BUCKET=ozi_lake
OZI_S3_ACCESS_KEY_ID=minioadmin
OZI_S3_SECRET_ACCESS_KEY=minioadmin
OZI_S3_REGION=fsn1                    # or us-east-1 for MinIO (validate signing against Hetzner in Phase 3)
OZI_S3_USE_SSL=false                  # MinIO: false · Hetzner: true
OZI_S3_URL_STYLE=path                 # path required for MinIO & Hetzner

# Memory & Execution Profiles
OZI_DUCKDB_WRITER_MEM_LIMIT=1GB
OZI_DUCKDB_READER_MEM_LIMIT=512MB
OZI_DUCKDB_WRITER_THREADS=8
OZI_DUCKDB_READER_THREADS=4
OZI_TEMP_DIR=/tmp/lake                # container-local scratch directory
OZI_MAX_TEMP_SIZE=4GB

# Compose Overlay Auto-Loading
COMPOSE_FILE=docker-compose.yml:docker-compose.lake.yml
```

## 4. New & updated files

| File | Purpose |
|---|---|
| `docker-compose.yml` & `docker-compose.lake.yml` | **Build Context Fix**: change `plotly-dash-app` build context from `./plotly_dash` to `.` (repo root) with `dockerfile: plotly_dash/Dockerfile`. Overlay adds `minio` service (local dev), `litestream` sidecar service (catalog continuous replication to S3), and `lake_catalog` volume. |
| `common/lake.py` | Shared connection module visible to both `etl` and `plotly_dash`: creates S3 secret with `url_style='path'` and SSL flag; attaches DuckLake (`READ_ONLY` variant for readers); applies per-role config profiles (`memory_limit`, `threads`, `temp_directory`, `max_temp_directory_size`, `preserve_insertion_order=false` on writers, `autoinstall_known_extensions=false`); context manager with transaction commit/rollback. |
| `lake_schema.sql` | Canonical DuckLake DDL: schemas (`CREATE SCHEMA IF NOT EXISTS data;`), tables, native partition schemes (`SET PARTITIONED BY (...)`), and views. No sequences/triggers — writers populate `created/updated` and collision-safe `load_id`. |
| `etl/init_lake.py` | Idempotent bootstrap: S3 bucket existence check/creation, sets SQLite `PRAGMA journal_mode = WAL;` via Python `sqlite3`, ATTACH-once, configures default catalog options for compaction/retention, executes `lake_schema.sql`, seeds `data.country` from `insert_countries.sql`. Startup assertions for memory limits, extensions, and tables. |
| `etl/load_to_lake.py` | Port of the 5 writers (ASNS, STATS_1D, STATS_5M, ASN_NEIGHBOURS, TRAFFIC, INTERNET_QUALITY): bound parameters (no f-string SQL); batched transactions (accumulates rows per task/country run to avoid 1-row commits); **collision-safe `load_id` generation** (`BIGINT` formatted as `YYYYMMDDHHMMSS` + 4-digit random/worker discriminator, e.g. `202610210853220101`, paired with `data.etl_load` ledger); in-database anti-join deduplication; `preserve_insertion_order=false`. |
| `etl/finalize_lake.py` | Recompute MV-equivalents into plain lake tables via CTAS-then-swap: `vm_current_asn`, `vm_asn_neighbour`, `vm_connectivity_index_by_country`, `_by_asn_top10`, and **`vm_connectivity_index_distinct`**; `v_*` chain becomes plain pass-through views over them → Dash SQL queries remain unchanged and fast. |
| `maintenance` (`-t MAINTENANCE` / `etl/compact_lake.py`) | Compaction & retention: calls **`CHECKPOINT ozi_lake;`** with configured catalog options (`expire_older_than => '30 days'`, `delete_older_than => '1 day'`, `rewrite_delete_threshold => 0.2`). This single command flushes inlined data, expires old snapshots, merges adjacent files, rewrites delete-heavy Parquet files, cleans up deleted files from S3, and removes orphaned files; followed by a size report via DuckLake metadata. |
| `etl/migrate_pg_to_lake.py` | Uses DuckDB `postgres_scanner` to read PG tables directly into DuckLake: `INSERT INTO data.<t> SELECT … FROM postgres_scan(...)`; runs finalize last; outputs row-count and checksum parity report. |
| `litestream.yml` | Litestream configuration mounting `/data/ozi_lake.sqlite` and replicating to `s3://<bucket>/catalog_backup/` with explicit **`path-style: true`**. |
| `etl/run_daily_stats.py` | Reads latest timestamp from `country_stat` in DuckLake; runs `STATS_1D`; automatically executes `finalize_lake.py` on completion so new daily data propagates to Dash views immediately. |
| `plotly_dash/dash_app.py` & `generate_static_graph.py` | **Resolution Filter Fixes**: updates both `fetch_data()` AND **`get_available_date_range()`** to include `WHERE cs_stats_resolution = '1d'` across `country_stat` queries. Prevents the date picker from expanding into 5m-only ranges; reads via `common/lake.py` (READ_ONLY profile) using `.arrow().to_pandas()`. |
| `etl/requirements.txt` & `plotly_dash/requirements.txt` | Add `duckdb>=1.5.2`, `pyarrow` (for Dash Arrow reader), and `boto3` (for S3 bucket check in ETL). |
| Dockerfiles | Pre-bake extensions (`sqlite`, `ducklake`, `httpfs`, `postgres_scanner`) into `/opt/duckdb/extensions` during build to satisfy `autoinstall_known_extensions=false`. |
| backout | `DELETE FROM data.<t> WHERE load_id = :id` ETL task (replaces `bulk_delete_operations.sql`). Running `main.py -t MAINTENANCE` after a large backout re-compacts tables via `rewrite_delete_threshold` / `rewrite_data_files`, purging delete vectors and restoring read performance. |

## 5. Physical schema / query optimization

### A. Native Partition Transforms (Iceberg-compatible)
DuckLake supports native partition transforms directly on date/timestamp columns. This avoids custom helper columns and enables automatic partition pruning on queries filtering on raw timestamp/date columns:

```sql
ALTER TABLE data.country_stat SET PARTITIONED BY (cs_stats_resolution, year(cs_stats_timestamp), month(cs_stats_timestamp));
ALTER TABLE data.asn_neighbour SET PARTITIONED BY (year(an_date), month(an_date));
ALTER TABLE data.asn SET PARTITIONED BY (year(a_date), month(a_date));
```

| Table | Partition Transform | Sort (file/row-group order) | Notes |
|---|---|---|---|
| `country_stat` | `(cs_stats_resolution, year(cs_stats_timestamp), month(cs_stats_timestamp))` | `(cs_country_iso2, cs_stats_timestamp)` | Separates Dash `1d` from large `5m` data; allows zone map min/max pruning. |
| `asn_neighbour` (biggest) | `(year(an_date), month(an_date))` | `(an_date, an_asn)` | Matches finalize's group-by; second-side pair sorted within row-group. |
| `asn` | `(year(a_date), month(a_date))` | `(a_country_iso2, a_date)` | Matches dedupe filter `(a_country_iso2, a_date)`. |
| `country_traffic`, `…_internet_quality` | `(year(date), month(date))` | `(country, date)` | Pruned on date-range queries. |
| `country`, `country_tag` | — | — | Tiny static lookup tables. |
| `vm_*` precomputed tables | — | `(date, asn_country)` | Monolithic, pre-sorted tables for instantaneous Dash scans. |

### B. Query Partition Pruning & Memory Protection
- **`country_stat` query fix in Dash (`fetch_data` and `get_available_date_range`)**:
  ```sql
  -- Main fetch:
  SELECT cs_country_iso2, cs_stats_timestamp, cs_asns_ris, cs_asns_stats
  FROM data.country_stat
  WHERE cs_stats_resolution = '1d'
  ORDER BY cs_stats_timestamp;

  -- Date picker bounds in get_available_date_range():
  SELECT MIN(cs_stats_timestamp::date) as min_date, MAX(cs_stats_timestamp::date) as max_date
  FROM data.country_stat
  WHERE cs_stats_resolution = '1d';
  ```
  Explicit `cs_stats_resolution = '1d'` filter ensures DuckDB skips all `5m` Parquet files completely and prevents the date picker from stretching into 5m-only time horizons.
- **`v_connectivity_index_distinct` precomputation**:
  Dash queries `v_connectivity_index_distinct` directly. Precomputing `vm_connectivity_index_distinct` in `finalize_lake.py` converts a heavy ad-hoc `DISTINCT` aggregation over millions of rows into a direct scan of a small, pre-aggregated table (<10MB memory working set).

### C. Write Batching, `load_id` Safety, and Delete Rewrites
- **Write Batching**: Default data inlining row limit is 10 rows. Single-row inserts get inlined into SQLite and create 1 snapshot per insert. Writers in `etl/load_to_lake.py` buffer data across the task or country run and execute inserts in batches (1,000–5,000 rows per transaction).
- **Collision-Safe `load_id`**: Generated as `BIGINT` combining 14-digit UTC timestamp + 4-digit random/worker discriminator:
  ```python
  import random, time
  load_id = int(time.strftime("%Y%m%d%H%M%S") + f"{random.randint(0, 9999):04d}")
  ```
  Guarantees uniqueness even when multiple ETL tasks trigger in the same second, preventing catastrophic cross-task deletion during a backout.
- **Delete-File Compaction**: A backout executes `DELETE FROM data.<t> WHERE load_id = :id`. In lakehouse formats, deletes leave delete-files (tombstones) that slow subsequent reads. Running `main.py -t MAINTENANCE` invokes `CHECKPOINT`, which triggers `rewrite_data_files` when deleted row ratios exceed `rewrite_delete_threshold` (0.2), reclaiming scan performance.

## 6. DuckDB RAM discipline (OOM prevention)

- **Strict Explicit Memory Limits**:
  - DuckDB defaults `memory_limit` to 80% of host RAM, ignoring Docker container cgroup limits.
  - Writer Profile (`ozi-etl`): `memory_limit = '1GB'` (container `mem_limit: 2g`).
  - Reader Profile (`plotly-dash-app`): `memory_limit = '512MB'` per Gunicorn worker (container `mem_limit: 2g`).
- **Disk Spilling**:
  - DuckDB only spills memory to disk if `temp_directory` is configured.
  - Set separate ephemeral temp directories per container: `temp_directory = '/tmp/lake_etl'` and `/tmp/lake_dash`.
  - Set `max_temp_directory_size = '4GB'` to prevent filling host disks.
- **Client Fetch via PyArrow**:
  - Replace SQLAlchemy `pd.read_sql` in Dash with DuckDB native Arrow streaming:
    `df = con.execute(query).arrow().to_pandas()`.
  - Reuses Arrow zero-copy memory buffers and avoids full Python tuple copies.
- **Startup Verification**:
  - `init_lake.py` and Dash startup run an assertion checking `current_setting('memory_limit')` against the configured environment variable.

## 7. Migration phases

1. **Foundation + Local Environment**:
   - Update `docker-compose.yml` to set `build.context: .` and `dockerfile: plotly_dash/Dockerfile` for `plotly-dash-app`.
   - Add `duckdb`, `pyarrow`, `boto3` to requirements.
   - Update Dockerfiles to pre-bake DuckDB extensions (`sqlite`, `ducklake`, `httpfs`, `postgres_scanner`) to `/opt/duckdb/extensions`.
   - Create `docker-compose.lake.yml` overlay (MinIO service, Litestream sidecar with `path-style: true`, shared catalog volume).
   - Implement `common/lake.py` connection profile manager (S3 secret with path-style, SSL auto-detection, memory/thread limits).
   - Implement `lake_schema.sql` (native partition transforms, tables, views).
   - Implement `etl/init_lake.py` (idempotent MinIO bucket check, SQLite WAL mode via stdlib `sqlite3`, catalog options for compaction, schema application, seed `country`).
2. **Writers + Finalize + Maintenance**:
   - Implement `etl/load_to_lake.py` (batching writer port, collision-safe `BIGINT` `load_id`, parameterized bound queries).
   - Implement `etl/finalize_lake.py` (precomputes `vm_current_asn`, `vm_asn_neighbour`, `vm_connectivity_index_by_country`, `vm_connectivity_index_by_asn_top10`, and `vm_connectivity_index_distinct`).
   - Implement `etl/compact_lake.py` (`CHECKPOINT ozi_lake;` bundling flush, expire, merge, rewrite, cleanup, and orphan deletion + metadata report).
3. **Migration + Dual-Run**:
   - Implement `etl/migrate_pg_to_lake.py` (`postgres_scanner` bulk load + parity validation report).
   - Validate Hetzner S3 region / Ceph signing semantics against a real Hetzner bucket (`OZI_S3_REGION=fsn1`).
   - Backup production Postgres data volume.
   - Set `OZI_STORAGE_BACKEND=both` in `.env.ozi` to write to both Postgres and DuckLake in parallel.
4. **Dash + Pipelines**:
   - Update `dash_app.py` and `generate_static_graph.py` with `WHERE cs_stats_resolution = '1d'` across both `fetch_data()` and `get_available_date_range()`.
   - Connect Dash to DuckLake via `common/lake.py` using Arrow fetch.
   - Update `etl/run_daily_stats.py` to invoke `finalize_lake.py` upon ETL completion.
   - Set `COMPOSE_FILE=docker-compose.yml:docker-compose.lake.yml` in `.env.ozi` so GH workflows (`etl_daily_stats.yml`, `publish_graphs.yml`, `cd.yml`) load the lake overlay automatically.
   - Deploy Hetzner S3 secrets to production GitHub repository settings.
5. **Tests + CI + Hardening**:
   - Update `docker-compose.test.yml` to include MinIO and lake catalog.
   - Build pytest fixtures: `tmp_lake` (isolated temporary directory with fresh SQLite catalog per test) and MinIO integration fixture.
   - Run disaster recovery drill: verify catalog restoration via `litestream restore` with `path-style: true`.
   - Update `README.md` with operational guide (compaction cron via CHECKPOINT, snapshot rollbacks via `load_id`, backout cleanup, backup/restore).

## 8. Known caveats & verification checklist

- **SQLite WAL Mode & Concurrency**:
  - `init_lake.py` executes `PRAGMA journal_mode = WAL;` once via standard Python `sqlite3` (persisted in file header).
  - DuckLake's internal retry-with-backoff mechanism handles SQLite write locks; catalog connections do not use Python PRAGMAs.
  - Directory permissions on `lake_catalog` volume shared between `ozi-etl` and `plotly-dash-app` containers.
- **S3 & Litestream Compatibility (MinIO & Hetzner)**:
  - `url_style = 'path'` is mandatory for DuckDB `httpfs` against Ceph-backed Hetzner and MinIO.
  - `path-style: true` is mandatory in `litestream.yml`.
  - S3 secret auto-toggles `use_ssl = false` for `http://` endpoints and `true` for `https://`.
  - Validate Hetzner `fsn1` signing region in Phase 3 before production switch.
- **Maintenance via `CHECKPOINT`**:
  - Calling `CHECKPOINT ozi_lake;` automatically cleans up physical Parquet files from S3 and rewrites tables with high delete ratios.
  - After a backout (`DELETE ... WHERE load_id = :id`), running maintenance restores scan performance.
- **Pre-baked Extensions & Build Context**:
  - `DUCKDB_EXTENSION_DIRECTORY=/opt/duckdb/extensions` set in Dockerfiles so containers require no outbound internet access at runtime.
  - Dash build context set to repository root so `common/lake.py` is packaged cleanly into both images.
- **Snapshot Growth Control**:
  - Batching writes in `load_to_lake.py` prevents single-row snapshot proliferation.
  - 30-day retention baseline maintained via daily/weekly `CHECKPOINT` maintenance job.
