from dagster import resource
import os
import urllib
from sqlalchemy import create_engine
from dotenv import load_dotenv
load_dotenv()

@resource
def db_connection():
    """
    Dagster resource to manage database connection using SQLAlchemy.
    """
    USER = os.getenv("DB_USER")
    PASSWORD = os.getenv("DB_PASSWORD", None)
    DBNAME = os.getenv("DB_NAME")
    PORT = os.getenv("DB_PORT", "5432")
    HOST = os.getenv("DB_HOST")

    if PASSWORD is None:
        raise ValueError("Database password is not set in environment variables.")

    encoded_password = urllib.parse.quote(PASSWORD)
    connection_string = f"postgresql://{USER}:{encoded_password}@{HOST}:{PORT}/{DBNAME}"
    
    engine = create_engine(connection_string)
    return engine  
