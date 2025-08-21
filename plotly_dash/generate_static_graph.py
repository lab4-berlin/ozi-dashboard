import os
import plotly.express as px
import sqlalchemy
import pandas as pd
from datetime import datetime, timedelta
import argparse

# Global variables for caching (though less critical for a one-off script, good practice)
last_data_fetch_time = None
cached_df = None
country_names_ru = {}
CACHE_TTL_SECONDS = 60 # Cache will be considered stale after 60 seconds

def fetch_data():
    global last_data_fetch_time, cached_df, country_names_ru

    # Check if cached data is still fresh
    if cached_df is not None and last_data_fetch_time is not None and \
       (datetime.now() - last_data_fetch_time).total_seconds() < CACHE_TTL_SECONDS:
        print("Serving data from cache.")
        return cached_df

    print("Fetching new data from database...")
    db_url = (
        f"postgresql://{os.environ.get('POSTGRES_OZI_USER', 'user')}:"
        f"{os.environ.get('POSTGRES_OZI_PASSWORD', 'password')}"
        f"@{os.environ.get('DASH_DB_HOST', 'localhost')}:"
        f"{os.environ.get('DASH_DB_PORT', '5432')}/"
        f"{os.environ.get('DASH_DB_NAME', 'exampledb')}"
    )
    engine = sqlalchemy.create_engine(db_url)

    # Fetch country statistics data
    query_stats = """SELECT
                cs_country_iso2,
                cs_stats_timestamp,
                cs_asns_ris,
                cs_asns_stats
             FROM data.country_stat
             ORDER BY cs_stats_timestamp;"""
    df = pd.read_sql(query_stats, engine)

    # Fetch country names in Russian
    query_countries = "SELECT c_iso2, c_name_ru FROM data.country;"
    df_countries = pd.read_sql(query_countries, engine)
    engine.dispose()

    # Populate country_names_ru dictionary
    country_names_ru = {row['c_iso2']: row['c_name_ru'] for index, row in df_countries.iterrows()}

    # Update cache and timestamp
    cached_df = df
    last_data_fetch_time = datetime.now()

    return df

def generate_graph_for_country(country_code):
    df = fetch_data()

    df_melted = df.melt(id_vars=['cs_country_iso2', 'cs_stats_timestamp'],
                        value_vars=['cs_asns_ris', 'cs_asns_stats'],
                        var_name='metric', value_name='value')

    if country_code:
        df_melted = df_melted[df_melted['cs_country_iso2'] == country_code]
    else:
        print("No country code provided. Cannot generate graph.")
        return None

    fig = px.line(df_melted,
                  x='cs_stats_timestamp',
                  y='value',
                  color='metric',
                  line_dash='metric',
                  title=f'Country Statistics Over Time ({country_code}) - ASNs RIS vs Stats',
                  labels={'cs_stats_timestamp': 'Date', 'value': 'Value', 'cs_country_iso2': 'Country'},
                  height=600)

    fig.update_layout(hovermode="x unified",
                      legend_itemclick="toggleothers",
                      legend=dict(x=0.01, y=0.99, xanchor='left', yanchor='top', bgcolor='rgba(255,255,255,0.5)'))
    return fig

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a static Plotly graph for a given country.")
    parser.add_argument("country_code", type=str, help="The ISO2 country code (e.g., RU, US).")
    parser.add_argument("--output_dir", type=str, default="./generated_graphs",
                        help="Directory to save the generated HTML file.")
    args = parser.parse_args()

    output_dir = args.output_dir
    os.makedirs(output_dir, exist_ok=True)

    fig = generate_graph_for_country(args.country_code.upper())
    if fig:
        output_filename = f"country_stats_{args.country_code.lower()}.html"
        output_path = os.path.join(output_dir, output_filename)
        # full_html=True ensures it's a complete HTML document, suitable for iframe embedding.
        # Plotly graphs are responsive by default within their container.
        # For embedding in Markdown, you'd typically use an iframe like:
        # <iframe src="path/to/your/graph.html" width="100%" height="600px" style="border:none;">
        # </iframe>
        # You might need to adjust the height or use CSS for more advanced responsiveness.
        fig.write_html(output_path, auto_open=False, full_html=True)
        print(f"Graph saved to {output_path}")
    else:
        print("Failed to generate graph.")
