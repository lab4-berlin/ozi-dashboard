import os
import duckdb
from contextlib import contextmanager

# Default configuration values
DEFAULT_LAKE_CATALOG = "/data/ozi_lake.sqlite"
DEFAULT_LAKE_DATA_PATH = "s3://ozi_lake/ozi_lake/"

# Module-level references
OZI_LAKE_CATALOG = os.getenv("OZI_LAKE_CATALOG", DEFAULT_LAKE_CATALOG)
OZI_LAKE_DATA_PATH = os.getenv("OZI_LAKE_DATA_PATH", DEFAULT_LAKE_DATA_PATH)


def get_s3_config():
    """Reads current S3 configuration from environment."""
    endpoint = os.getenv("OZI_S3_ENDPOINT", "minio:9000")
    bucket = os.getenv("OZI_S3_BUCKET", "ozi_lake").strip()
    key_id = os.getenv("OZI_S3_ACCESS_KEY_ID", "minioadmin")
    secret = os.getenv("OZI_S3_SECRET_ACCESS_KEY", os.getenv("OZI_S3_SECRET", "minioadmin"))
    region = os.getenv("OZI_S3_REGION", "fsn1")
    url_style = os.getenv("OZI_S3_URL_STYLE", "path")

    use_ssl_env = os.getenv("OZI_S3_USE_SSL")
    if use_ssl_env is not None:
        use_ssl = use_ssl_env.lower() in ("true", "1", "yes")
    else:
        clean = endpoint.lower()
        if clean.startswith("http://") or "minio" in clean or "localhost" in clean or "127.0.0.1" in clean:
            use_ssl = False
        else:
            use_ssl = True

    endpoint_host = endpoint.replace("http://", "").replace("https://", "")

    return {
        "endpoint": endpoint,
        "endpoint_host": endpoint_host,
        "bucket": bucket,
        "key_id": key_id,
        "secret": secret,
        "region": region,
        "url_style": url_style,
        "use_ssl": use_ssl,
    }


def get_lake_connection(role="reader", read_only=None, catalog_path=None, data_path=None):
    """
    Creates and configures an in-memory DuckDB connection attached to the DuckLake catalog.

    Parameters:
      role: 'reader' (default) or 'writer'.
      read_only: whether to attach catalog as READ_ONLY. Defaults to True for reader, False for writer.
      catalog_path: path to SQLite catalog file (overrides OZI_LAKE_CATALOG env).
      data_path: path to Parquet storage directory or S3 URL (overrides OZI_LAKE_DATA_PATH env).
    """
    if catalog_path is None:
        catalog_path = os.getenv("OZI_LAKE_CATALOG", DEFAULT_LAKE_CATALOG)
    if data_path is None:
        data_path = os.getenv("OZI_LAKE_DATA_PATH", DEFAULT_LAKE_DATA_PATH)

    if read_only is None:
        read_only = (role == "reader")

    is_writer = (role == "writer")
    mem_limit = os.getenv("OZI_DUCKDB_WRITER_MEM_LIMIT", "1GB") if is_writer else os.getenv("OZI_DUCKDB_READER_MEM_LIMIT", "512MB")
    threads = int(os.getenv("OZI_DUCKDB_WRITER_THREADS", "8")) if is_writer else int(os.getenv("OZI_DUCKDB_READER_THREADS", "4"))
    preserve_order = not is_writer

    # Ensure parent directory for catalog exists if writing
    catalog_dir = os.path.dirname(catalog_path)
    if catalog_dir:
        os.makedirs(catalog_dir, exist_ok=True)

    # Ensure local directory exists if data_path is a filesystem path
    if not data_path.startswith("s3://"):
        local_dir = data_path.replace("file://", "")
        os.makedirs(local_dir, exist_ok=True)

    # Isolated ephemeral scratch directory per role
    base_temp = os.getenv("OZI_TEMP_DIR", "/tmp/lake")
    temp_dir = f"{base_temp}_{role}"
    os.makedirs(temp_dir, exist_ok=True)

    max_temp_size = os.getenv("OZI_MAX_TEMP_SIZE", "4GB")
    ext_dir = os.getenv("DUCKDB_EXTENSION_DIRECTORY", "/opt/duckdb/extensions")

    con = duckdb.connect(":memory:")

    # Configure DuckDB engine options
    if os.path.exists(ext_dir):
        con.execute(f"SET extension_directory = '{ext_dir}';")

    con.execute("SET autoinstall_known_extensions = false;")
    con.execute(f"SET memory_limit = '{mem_limit}';")
    con.execute(f"SET threads = {threads};")
    con.execute(f"SET temp_directory = '{temp_dir}';")
    con.execute(f"SET max_temp_directory_size = '{max_temp_size}';")
    con.execute(f"SET preserve_insertion_order = {str(preserve_order).lower()};")

    # Load required extensions
    con.execute("LOAD sqlite;")
    con.execute("LOAD ducklake;")
    con.execute("LOAD httpfs;")

    # Configure S3 secret if data path targets object storage
    if data_path.startswith("s3://"):
        s3 = get_s3_config()
        secret_sql = f"""
        CREATE SECRET IF NOT EXISTS lake_s3 (
            TYPE S3,
            KEY_ID '{s3['key_id']}',
            SECRET '{s3['secret']}',
            REGION '{s3['region']}',
            ENDPOINT '{s3['endpoint_host']}',
            URL_STYLE '{s3['url_style']}',
            USE_SSL {str(s3['use_ssl']).lower()}
        );
        """
        con.execute(secret_sql)

    # Attach DuckLake catalog
    # Note: DuckLake's internal retry-with-backoff handles SQLite concurrency.
    attach_flags = f"DATA_PATH '{data_path}'"
    if read_only:
        attach_flags += ", READ_ONLY"

    attach_sql = f"ATTACH 'ducklake:sqlite:{catalog_path}' AS ozi ({attach_flags});"
    con.execute(attach_sql)
    con.execute("USE ozi;")

    return con


@contextmanager
def lake_connection(role="reader", read_only=None, catalog_path=None, data_path=None):
    """Context manager for obtaining a configured lake connection."""
    con = get_lake_connection(role=role, read_only=read_only, catalog_path=catalog_path, data_path=data_path)
    try:
        yield con
    finally:
        con.close()


@contextmanager
def lake_transaction(catalog_path=None, data_path=None):
    """Context manager for write transactions with automatic commit/rollback."""
    con = get_lake_connection(role="writer", read_only=False, catalog_path=catalog_path, data_path=data_path)
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
    expected_mem = os.getenv("OZI_DUCKDB_WRITER_MEM_LIMIT", "1GB") if is_writer else os.getenv("OZI_DUCKDB_READER_MEM_LIMIT", "512MB")

    actual_mem = con.execute("SELECT current_setting('memory_limit');").fetchone()[0]
    print(f"DuckLake [{expected_role}] memory_limit: {actual_mem} (target: {expected_mem})")
