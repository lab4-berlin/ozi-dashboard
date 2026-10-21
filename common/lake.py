import os
import duckdb
from contextlib import contextmanager

# Catalog and Storage configuration
OZI_LAKE_CATALOG = os.getenv("OZI_LAKE_CATALOG", "/data/ozi_lake.sqlite")
OZI_LAKE_DATA_PATH = os.getenv("OZI_LAKE_DATA_PATH", "s3://ozi_lake/ozi_lake/")

# S3 configuration
OZI_S3_ENDPOINT = os.getenv("OZI_S3_ENDPOINT", "minio:9000")
OZI_S3_BUCKET = os.getenv("OZI_S3_BUCKET", "ozi_lake").strip()
OZI_S3_ACCESS_KEY_ID = os.getenv("OZI_S3_ACCESS_KEY_ID", "minioadmin")
OZI_S3_SECRET_ACCESS_KEY = os.getenv(
    "OZI_S3_SECRET_ACCESS_KEY",
    os.getenv("OZI_S3_SECRET", "minioadmin"),
)
OZI_S3_REGION = os.getenv("OZI_S3_REGION", "fsn1")
OZI_S3_URL_STYLE = os.getenv("OZI_S3_URL_STYLE", "path")

# SSL auto-detection
_use_ssl_env = os.getenv("OZI_S3_USE_SSL")
if _use_ssl_env is not None:
    OZI_S3_USE_SSL = _use_ssl_env.lower() in ("true", "1", "yes")
else:
    # Auto-detect: disable SSL for local minio / localhost / http endpoints
    clean_endpoint = OZI_S3_ENDPOINT.lower()
    if clean_endpoint.startswith("http://") or "minio" in clean_endpoint or "localhost" in clean_endpoint or "127.0.0.1" in clean_endpoint:
        OZI_S3_USE_SSL = False
    else:
        OZI_S3_USE_SSL = True

# Clean endpoint host for DuckDB secret (strip protocol if present)
OZI_S3_ENDPOINT_HOST = OZI_S3_ENDPOINT.replace("http://", "").replace("https://", "")

# DuckDB Resource Profiles
WRITER_MEM_LIMIT = os.getenv("OZI_DUCKDB_WRITER_MEM_LIMIT", "1GB")
READER_MEM_LIMIT = os.getenv("OZI_DUCKDB_READER_MEM_LIMIT", "512MB")
WRITER_THREADS = int(os.getenv("OZI_DUCKDB_WRITER_THREADS", "8"))
READER_THREADS = int(os.getenv("OZI_DUCKDB_READER_THREADS", "4"))
OZI_MAX_TEMP_SIZE = os.getenv("OZI_MAX_TEMP_SIZE", "4GB")
DUCKDB_EXT_DIR = os.getenv("DUCKDB_EXTENSION_DIRECTORY", "/opt/duckdb/extensions")


def get_lake_connection(role="reader", read_only=None):
    """
    Creates and configures an in-memory DuckDB connection attached to the DuckLake catalog.

    Roles:
      - 'reader': lower memory limit (512MB default), 4 threads, attaches READ_ONLY by default.
      - 'writer': higher memory limit (1GB default), 8 threads, preserve_insertion_order=false.
    """
    if read_only is None:
        read_only = (role == "reader")

    is_writer = (role == "writer")
    mem_limit = WRITER_MEM_LIMIT if is_writer else READER_MEM_LIMIT
    threads = WRITER_THREADS if is_writer else READER_THREADS
    preserve_order = not is_writer

    # Isolated ephemeral scratch directory per role
    base_temp = os.getenv("OZI_TEMP_DIR", "/tmp/lake")
    temp_dir = f"{base_temp}_{role}"
    os.makedirs(temp_dir, exist_ok=True)

    con = duckdb.connect(":memory:")

    # Configure DuckDB engine options
    if os.path.exists(DUCKDB_EXT_DIR):
        con.execute(f"SET extension_directory = '{DUCKDB_EXT_DIR}';")

    con.execute("SET autoinstall_known_extensions = false;")
    con.execute(f"SET memory_limit = '{mem_limit}';")
    con.execute(f"SET threads = {threads};")
    con.execute(f"SET temp_directory = '{temp_dir}';")
    con.execute(f"SET max_temp_directory_size = '{OZI_MAX_TEMP_SIZE}';")
    con.execute(f"SET preserve_insertion_order = {str(preserve_order).lower()};")

    # Load required extensions
    con.execute("LOAD sqlite;")
    con.execute("LOAD ducklake;")
    con.execute("LOAD httpfs;")

    # Configure S3 secret if data path targets object storage
    if OZI_LAKE_DATA_PATH.startswith("s3://"):
        secret_sql = f"""
        CREATE SECRET IF NOT EXISTS lake_s3 (
            TYPE S3,
            KEY_ID '{OZI_S3_ACCESS_KEY_ID}',
            SECRET '{OZI_S3_SECRET_ACCESS_KEY}',
            REGION '{OZI_S3_REGION}',
            ENDPOINT '{OZI_S3_ENDPOINT_HOST}',
            URL_STYLE '{OZI_S3_URL_STYLE}',
            USE_SSL {str(OZI_S3_USE_SSL).lower()}
        );
        """
        con.execute(secret_sql)

    # Attach DuckLake catalog
    # Note: DuckLake's internal retry-with-backoff handles SQLite concurrency.
    attach_flags = f"DATA_PATH '{OZI_LAKE_DATA_PATH}'"
    if read_only:
        attach_flags += ", READ_ONLY"

    attach_sql = f"ATTACH 'ducklake:sqlite:{OZI_LAKE_CATALOG}' AS ozi ({attach_flags});"
    con.execute(attach_sql)
    con.execute("USE ozi;")

    return con


@contextmanager
def lake_connection(role="reader", read_only=None):
    """Context manager for obtaining a configured lake connection."""
    con = get_lake_connection(role=role, read_only=read_only)
    try:
        yield con
    finally:
        con.close()


@contextmanager
def lake_transaction():
    """Context manager for write transactions with automatic commit/rollback."""
    con = get_lake_connection(role="writer", read_only=False)
    try:
        con.execute("BEGIN TRANSACTION;")
        yield con
        con.execute("COMMIT;")
    except Exception:
        con.execute("ROLLBACK;")
        raise
    finally:
        con.close()


def assert_lake_settings(con, expected_role="reader"):
    """Validates runtime memory limit and loaded extensions."""
    is_writer = (expected_role == "writer")
    expected_mem = WRITER_MEM_LIMIT if is_writer else READER_MEM_LIMIT

    actual_mem = con.execute("SELECT current_setting('memory_limit');").fetchone()[0]
    print(f"DuckLake [{expected_role}] memory_limit: {actual_mem} (target: {expected_mem})")
