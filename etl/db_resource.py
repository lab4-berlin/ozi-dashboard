from dagster import resource
import psycopg2
import os

from dotenv import load_dotenv
load_dotenv()

@resource
def db_connection():
    """Dagster resource to manage database connection."""
    conn = psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT", "5432")
    )
    try:
        yield conn
    finally:
        conn.close()
