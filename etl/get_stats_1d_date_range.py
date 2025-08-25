#!/usr/bin/env python3

import os
import sys
from datetime import datetime, timedelta
import argparse
from sqlalchemy import create_engine, text

# Add the current directory to the Python path
sys.path.append('/app/etl')

from country_lists import ALL_COUNTRIES


def get_last_date_from_db():
    """
    Get the last date in the country_stat table for STATS_1D data.
    Returns a date object or None if no data exists.
    """
    # Get database connection parameters from environment variables
    db_host = os.getenv('OZI_DATABASE_HOST', 'ozi-postgres')
    db_port = os.getenv('OZI_DATABASE_PORT', '5432')
    db_name = os.getenv('OZI_DATABASE_NAME', 'ozi_db2')
    db_user = os.getenv('OZI_DATABASE_USER', 'ozi')
    db_password = os.getenv('OZI_DATABASE_PASSWORD', 'ozi_password')
    
    try:
        # Create database connection string
        if db_password:
            connection_string = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        else:
            connection_string = f"postgresql://{db_user}@{db_host}:{db_port}/{db_name}"
        
        # Connect to the database
        engine = create_engine(connection_string)
        
        with engine.connect() as conn:
            # Query the latest date from the country_stat table where cs_stats_resolution = '1d'
            result = conn.execute(text("""
                SELECT MAX(cs_stats_timestamp) as max_date
                FROM data.country_stat
                WHERE cs_stats_resolution = '1d'
            """)).fetchone()
            
            if result and result[0]:
                # Return the date part only (without time)
                return result[0].date()
        
        return None
    except Exception as e:
        print(f"ERROR: Database connection or query failed in get_last_date_from_db: {e}", file=sys.stderr)
        return None


def main():
    parser = argparse.ArgumentParser(description="Determine date range for STATS_1D ETL job")
    parser.add_argument(
        "--start-date",
        help="Start date in YYYY-MM-DD format (default: last date in DB or 30 days ago)",
        default=None
    )
    
    args = parser.parse_args()
    
    # Determine the date range
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).date()
    
    if args.start_date:
        try:
            start_date = datetime.strptime(args.start_date, "%Y-%m-%d").date()
        except ValueError:
            print("Error: Start date must be in YYYY-MM-DD format.")
            return 1
    else:
        # Try to get the last date from the database
        last_date = get_last_date_from_db()
        if last_date:
            # Start from the day after the last date
            start_date = last_date + timedelta(days=1)
        else:
            # Default to configurable days ago
            default_days_ago = int(os.getenv('DEFAULT_DAYS_AGO', '30'))
            start_date = today - timedelta(days=default_days_ago)
    
    # Ensure start_date is not in the future
    if start_date > today:
        print("# Start date is in the future. Nothing to do.")
        return 0
    
    # Output the date range in a format that can be used by the main ETL script
    print(f"# Running STATS_1D ETL job from {start_date} to {today}")
    print(f"--date-from {start_date} --date-to {today}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())