#!/usr/bin/env python3
import os
import sys
import sqlite3

# Ensure workspace root is in python path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from common.lake import (
    OZI_LAKE_CATALOG,
    OZI_LAKE_DATA_PATH,
    OZI_S3_ENDPOINT,
    OZI_S3_BUCKET,
    OZI_S3_ACCESS_KEY_ID,
    OZI_S3_SECRET_ACCESS_KEY,
    OZI_S3_REGION,
    OZI_S3_USE_SSL,
    get_lake_connection,
    assert_lake_settings,
)


def init_sqlite_wal(catalog_path):
    """Initializes the SQLite catalog file and permanently enables WAL mode."""
    catalog_dir = os.path.dirname(catalog_path)
    if catalog_dir:
        os.makedirs(catalog_dir, exist_ok=True)

    print(f"Initializing SQLite catalog at: {catalog_path}")
    conn = sqlite3.connect(catalog_path)
    try:
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode = WAL;")
        mode = cursor.fetchone()[0]
        print(f"SQLite journal_mode set to: {mode}")
    finally:
        conn.close()


def ensure_s3_bucket():
    """Idempotently checks and creates target S3 bucket if targeting object storage."""
    if not OZI_LAKE_DATA_PATH.startswith("s3://"):
        # Local filesystem path
        local_dir = OZI_LAKE_DATA_PATH.replace("file://", "")
        os.makedirs(local_dir, exist_ok=True)
        print(f"Target is local filesystem: {local_dir}")
        return

    try:
        import boto3
        from botocore.exceptions import ClientError

        protocol = "https" if OZI_S3_USE_SSL else "http"
        endpoint_host = OZI_S3_ENDPOINT.replace("http://", "").replace("https://", "")
        endpoint_url = f"{protocol}://{endpoint_host}"

        print(f"Verifying S3 bucket '{OZI_S3_BUCKET}' at {endpoint_url}...")
        s3 = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=OZI_S3_ACCESS_KEY_ID,
            aws_secret_access_key=OZI_S3_SECRET_ACCESS_KEY,
            region_name=OZI_S3_REGION,
            use_ssl=OZI_S3_USE_SSL,
        )

        try:
            s3.head_bucket(Bucket=OZI_S3_BUCKET)
            print(f"S3 bucket '{OZI_S3_BUCKET}' exists.")
        except ClientError as e:
            error_code = str(e.response.get("Error", {}).get("Code", ""))
            if error_code in ("404", "NoSuchBucket"):
                print(f"Bucket '{OZI_S3_BUCKET}' not found. Creating...")
                # Hetzner and MinIO handle default or location constraints
                try:
                    s3.create_bucket(Bucket=OZI_S3_BUCKET)
                except Exception:
                    s3.create_bucket(
                        Bucket=OZI_S3_BUCKET,
                        CreateBucketConfiguration={"LocationConstraint": OZI_S3_REGION},
                    )
                print(f"S3 bucket '{OZI_S3_BUCKET}' created successfully.")
            else:
                print(f"Notice: S3 head_bucket response: {e}. Proceeding.")
    except ImportError:
        print("boto3 not installed; skipping external S3 bucket verification.")
    except Exception as e:
        print(f"Warning: S3 bucket verification encountered: {e}. Proceeding.")


def apply_schema(con, schema_path):
    """Executes the DDL statements from the schema file."""
    print(f"Applying schema DDL from {schema_path}...")
    with open(schema_path, "r", encoding="utf-8") as f:
        sql_content = f.read()

    # Split and execute individual statements
    statements = [stmt.strip() for stmt in sql_content.split(";") if stmt.strip()]
    for stmt in statements:
        # Skip comment-only blocks
        lines = [line for line in stmt.splitlines() if not line.strip().startswith("--")]
        if not "".join(lines).strip():
            continue
        try:
            con.execute(stmt + ";")
        except Exception as e:
            # If an ALTER TABLE SET PARTITIONED BY has already been applied, continue gracefully
            if "already partitioned" in str(e).lower():
                continue
            print(f"Error applying statement:\n{stmt}\nError: {e}", file=sys.stderr)
            raise

    print("Schema applied successfully.")


def configure_catalog_options(con):
    """Configures default DuckLake retention and compaction options."""
    try:
        con.execute("CALL ozi.set_option('expire_older_than', '30 days');")
        con.execute("CALL ozi.set_option('delete_older_than', '1 day');")
        con.execute("CALL ozi.set_option('rewrite_delete_threshold', 0.2);")
        print("DuckLake catalog compaction & retention options configured.")
    except Exception as e:
        print(f"Notice: catalog option configuration: {e}")


def seed_countries(con, seed_path):
    """Seeds the country table from insert_countries.sql if currently empty."""
    count = con.execute("SELECT count(*) FROM data.country;").fetchone()[0]
    if count > 0:
        print(f"data.country already contains {count} records. Skipping seed.")
        return

    if not os.path.exists(seed_path):
        print(f"Warning: Seed file {seed_path} not found. Skipping.")
        return

    print(f"Seeding data.country from {seed_path}...")
    with open(seed_path, "r", encoding="utf-8") as f:
        statements = []
        for line in f:
            line_str = line.strip()
            if not line_str or line_str.startswith("\\") or line_str.startswith("--"):
                continue
            if line_str.endswith(";"):
                statements.append(line_str)

    con.execute("BEGIN TRANSACTION;")
    try:
        for stmt in statements:
            con.execute(stmt)
        con.execute("COMMIT;")
        seeded_count = con.execute("SELECT count(*) FROM data.country;").fetchone()[0]
        print(f"Seeded {seeded_count} countries.")
    except Exception:
        con.execute("ROLLBACK;")
        raise


def main():
    schema_path = os.path.join(ROOT_DIR, "lake_schema.sql")
    seed_path = os.path.join(ROOT_DIR, "insert_countries.sql")

    # Step 1: Initialize SQLite WAL mode
    init_sqlite_wal(OZI_LAKE_CATALOG)

    # Step 2: Ensure S3 bucket exists
    ensure_s3_bucket()

    # Step 3: Connect to DuckLake as writer
    con = get_lake_connection(role="writer", read_only=False)
    try:
        # Step 4: Configure catalog options
        configure_catalog_options(con)

        # Step 5: Apply DDL
        apply_schema(con, schema_path)

        # Step 6: Seed reference data
        seed_countries(con, seed_path)

        # Step 7: Startup assertions
        assert_lake_settings(con, expected_role="writer")
        tables = con.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'data';"
        ).fetchall()
        table_names = [t[0] for t in tables]
        print(f"Verified {len(table_names)} tables/views in 'data' schema: {', '.join(table_names)}")
        print("DuckLake initialization completed successfully!")
    finally:
        con.close()


if __name__ == "__main__":
    main()
