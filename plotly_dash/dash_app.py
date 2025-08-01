import os
import dash
from dash import html, dcc, Input, Output
import plotly.express as px
import sqlalchemy
import pandas as pd
from datetime import datetime, timedelta

# Global variables for caching
last_data_fetch_time = None
cached_df = None
CACHE_TTL_SECONDS = 60 # Cache will be considered stale after 60 seconds

def fetch_data():
    global last_data_fetch_time, cached_df

    # Check if cached data is still fresh
    if cached_df is not None and last_data_fetch_time is not None and \
       (datetime.now() - last_data_fetch_time).total_seconds() < CACHE_TTL_SECONDS:
        print("Serving data from cache.")
        return cached_df

    print("Fetching new data from database...")
    db_url = (
        f"postgresql://{os.environ.get('DASH_DB_USER', 'user')}:"
        f"{os.environ.get('DASH_DB_PASSWORD', 'password')}@"
        f"{os.environ.get('DASH_DB_HOST', 'localhost')}:"
        f"{os.environ.get('DASH_DB_PORT', '5432')}/"
        f"{os.environ.get('DASH_DB_NAME', 'exampledb')}"
    )
    engine = sqlalchemy.create_engine(db_url)
    query = """SELECT 
                cs_country_iso2,
                cs_stats_timestamp,
                cs_v4_prefixes_ris,
                cs_v6_prefixes_ris,
                cs_asns_ris,
                cs_v4_prefixes_stats,
                cs_v6_prefixes_stats,
                cs_asns_stats
             FROM data.country_stat 
             ORDER BY cs_stats_timestamp;"""
    df = pd.read_sql(query, engine)
    engine.dispose()
    
    # Update cache and timestamp
    cached_df = df
    last_data_fetch_time = datetime.now()

    print("\n--- Original DataFrame (df) ---")
    print(df.head())
    print(df.info())
    return df

app = dash.Dash(__name__)

df = fetch_data()

# Melt the DataFrame to long format for easier plotting of multiple metrics
df_melted = df.melt(id_vars=['cs_country_iso2', 'cs_stats_timestamp'],
                    value_vars=['cs_v4_prefixes_ris', 'cs_v6_prefixes_ris', 'cs_asns_ris',
                                  'cs_v4_prefixes_stats', 'cs_v6_prefixes_stats', 'cs_asns_stats'],
                    var_name='metric', value_name='value')

print("\n--- Melted DataFrame (df_melted) ---")
print(df_melted.head())
print(df_melted.info())

app.layout = html.Div([
    html.H1("Country Statistics Time Series"),
    dcc.Graph(id='time-series-graph'),
    dcc.Interval(
        id='interval-component',
        interval=5*60*1000, # in milliseconds, 5 minutes
        n_intervals=0
    )
])

@app.callback(
    Output('time-series-graph', 'figure'),
    Input('interval-component', 'n_intervals') # Triggered by interval
)
def update_graph(n_intervals):
    # Re-fetch data (which will use cache if fresh)
    current_df = fetch_data()
    current_df_melted = current_df.melt(id_vars=['cs_country_iso2', 'cs_stats_timestamp'],
                                        value_vars=['cs_v4_prefixes_ris', 'cs_v6_prefixes_ris', 'cs_asns_ris',
                                                      'cs_v4_prefixes_stats', 'cs_v6_prefixes_stats', 'cs_asns_stats'],
                                        var_name='metric', value_name='value')

    fig = px.line(current_df_melted, 
                  x='cs_stats_timestamp', 
                  y='value', 
                  color='cs_country_iso2', 
                  facet_col='metric', 
                  facet_col_wrap=1, 
                  title='Country Statistics Over Time',
                  labels={'cs_stats_timestamp': 'Date', 'value': 'Value', 'cs_country_iso2': 'Country'},
                  height=3600) 
    
    fig.for_each_annotation(lambda a: a.update(text=a.text.replace("metric=", "")))
    fig.update_layout(hovermode="x unified", 
                      legend_itemclick="toggleothers",
                      legend=dict(x=1.02, y=1, xanchor='left', yanchor='top')) 

    return fig

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8050, debug=True)
