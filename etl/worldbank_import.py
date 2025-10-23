import argparse
import math
import os
import time
from datetime import date

import pandas as pd
import requests
from sqlalchemy import create_engine, text

# --- Database connection config ---
DB_HOST = os.getenv("POSTGRES_HOST", "ozi-postgres")
DB_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
DB_NAME = os.getenv("POSTGRES_DB", "ozi_db2")
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "postgres")

# --- Indicators from World Bank ---
INDICATORS = {
    "population": "SP.POP.TOTL",        # Population, total
    "gdp_per_capita": "NY.GDP.PCAP.CD"  # GDP per capita (current US$)
}

BASE_URL = "https://api.worldbank.org/v2"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "ozi-worldbank-import/1.0"})


def fetch_indicator(indicator_code: str, year_from: int, year_to: int) -> pd.DataFrame:
    """Fetch data for all countries for a given indicator and time range."""
    params = {"date": f"{year_from}:{year_to}", "format": "json", "per_page": 20000}
    url = f"{BASE_URL}/country/all/indicator/{indicator_code}"

    # First page (to get pagination info)
    r = SESSION.get(url, params=params, timeout=60)
    r.raise_for_status()
    payload = r.json()

    if not isinstance(payload, list) or len(payload) < 2:
        raise RuntimeError(f"Unexpected API response for {indicator_code}: {payload}")

    meta, data = payload[0], payload[1]
    total = int(meta.get("total", 0))
    per_page = int(meta.get("per_page", 50))
    pages = int(meta.get("pages", max(1, math.ceil(total / max(1, per_page))))) or 1

    def normalize(item):
        country_obj = item.get("country") or {}
        return {
            "country": country_obj.get("value"),
            "country_iso2": country_obj.get("id"),          # ISO2
            "countryiso3code": item.get("countryiso3code"), # ISO3
            "date": int(item.get("date")),
            "value": item.get("value"),
        }

    rows = [normalize(x) for x in data]

    # Fetch remaining pages
    for page in range(2, pages + 1):
        params_page = dict(params, page=page)
        for attempt in range(5):
            try:
                rp = SESSION.get(url, params=params_page, timeout=60)
                rp.raise_for_status()
                payload_p = rp.json()
                _, data_p = payload_p[0], payload_p[1]
                rows.extend([normalize(x) for x in data_p])
                break
            except Exception:
                time.sleep(2 ** attempt)
                if attempt == 4:
                    raise

    df = pd.DataFrame(rows)
    # Keep only countries (exclude aggregates like "World", "EU", etc.)
    df = df[df["countryiso3code"].astype(str).str.len() == 3]
    df = df.dropna(subset=["value"])
    return df


def build_dataset(year_from: int, year_to: int) -> pd.DataFrame:
    """Combine Population and GDP per capita data into one dataset."""
    pop = fetch_indicator(INDICATORS["population"], year_from, year_to).rename(columns={"value": "population"})
    gdp = fetch_indicator(INDICATORS["gdp_per_capita"], year_from, year_to).rename(columns={"value": "gdp_per_capita"})

    # Merge by ISO2 + ISO3 + year
    df = pd.merge(
        pop[["country", "country_iso2", "countryiso3code", "date", "population"]],
        gdp[["country_iso2", "countryiso3code", "date", "gdp_per_capita"]],
        on=["country_iso2", "countryiso3code", "date"],
        how="outer"
    )

    df = df.rename(columns={
        "countryiso3code": "country_code",  # ISO3
        "date": "year",
    })

    df["year"] = df["year"].astype(int)
    df["population"] = pd.to_numeric(df["population"], errors="coerce")
    df["gdp_per_capita"] = pd.to_numeric(df["gdp_per_capita"], errors="coerce")

    df = df.drop_duplicates(subset=["country_iso2", "country_code", "year"])

    df = df[["country", "country_iso2", "country_code", "year", "population", "gdp_per_capita"]]
    return df


def upsert_to_postgres(df: pd.DataFrame, table: str = "worldbank_country_stats"):
    """Upsert dataframe into Postgres table."""
    engine = create_engine(
        f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}",
        pool_pre_ping=True,
    )

    with engine.begin() as conn:
        # Create temporary table with same structure
        conn.execute(text(f"CREATE TEMP TABLE tmp_wb (LIKE {table} INCLUDING ALL);"))

        # Load data into temp table
        df.to_sql("tmp_wb", con=conn, if_exists="append", index=False)

        # Upsert into main table
        conn.execute(text(f"""
            INSERT INTO {table} (country, country_iso2, country_code, year, population, gdp_per_capita)
            SELECT country, country_iso2, country_code, year, population, gdp_per_capita
            FROM tmp_wb
            ON CONFLICT (country_code, year) DO UPDATE SET
                country = EXCLUDED.country,
                country_iso2 = COALESCE(EXCLUDED.country_iso2, {table}.country_iso2),
                population = COALESCE(EXCLUDED.population, {table}.population),
                gdp_per_capita = COALESCE(EXCLUDED.gdp_per_capita, {table}.gdp_per_capita);
        """))


def main():
    parser = argparse.ArgumentParser(description="Import World Bank indicators into Postgres")
    parser.add_argument("--from-year", type=int, default=2015)
    parser.add_argument("--to-year", type=int, default=date.today().year)
    parser.add_argument("--table", type=str, default="worldbank_country_stats")
    args = parser.parse_args()

    df = build_dataset(args.from_year, args.to_year)
    if df.empty:
        print("No data fetched.")
        return

    print(f"Fetched rows: {len(df)}")
    upsert_to_postgres(df, table=args.table)
    print(f"Upserted into {args.table}")


if __name__ == "__main__":
    main()