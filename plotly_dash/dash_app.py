import os
import dash
from dash import html, dcc, Input, Output
import plotly.express as px
import sqlalchemy
import pandas as pd
from datetime import datetime, timedelta
import random

# Global variables for caching
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

    print("\n--- Original DataFrame (df) ---")
    print(df.head())
    print(df.info())
    return df

app = dash.Dash(__name__)
app.suppress_callback_exceptions = True

df = fetch_data()

# Melt the DataFrame to long format for easier plotting of multiple metrics
df_melted = df.melt(id_vars=['cs_country_iso2', 'cs_stats_timestamp'],
                    value_vars=['cs_asns_ris', 'cs_asns_stats'],
                    var_name='metric', value_name='value')

print("\n--- Melted DataFrame (df_melted) ---")
print(df_melted.head())
print(df_melted.info())


# Layout for Page 1 (Original Dashboard)
def layout_page1_content():
    # Create dropdown options with Russian names
    dropdown_options = []
    for country_iso in df['cs_country_iso2'].unique():
        russian_name = country_names_ru.get(country_iso, country_iso) # Fallback to ISO if Russian name not found
        dropdown_options.append({'label': f"{country_iso}, {russian_name}", 'value': country_iso})

    return html.Div([
        html.H1("Количественная автономных систем по странам"),
        html.Div([
            dcc.Dropdown(
                id="country-dropdown-page1",
                options=dropdown_options,
                value=["RU"],
                multi=True,
                placeholder="Выберите страну",
                closeOnSelect=False,
            )
        ], style={"width": "50%", "padding": "20px"}),
        dcc.Graph(id="time-series-graph-page1"),
        dcc.Interval(
            id="interval-component-page1",
            interval=5*60*1000,
            n_intervals=0
        )
    ])

# Layout for Page 2 (Copy of Original Dashboard, can be modified later)
def layout_page2_content():
    # Create dropdown options with Russian names
    dropdown_options = []
    for country_iso in df['cs_country_iso2'].unique():
        russian_name = country_names_ru.get(country_iso, country_iso) # Fallback to ISO if Russian name not found
        dropdown_options.append({'label': f"{country_iso}, {russian_name}", 'value': country_iso})

    return html.Div([
        html.H1(f"Country Statistics Time Series - Page 2"),
        html.Div([
            dcc.Dropdown(
                id='country-dropdown-page2-single',
                options=dropdown_options,
                multi=False, # Single selection
                value='RU', # Default selected country
                placeholder="Select a country",
                closeOnSelect=True,
            )
        ], style={'width': '50%', 'padding': '20px'}),
        dcc.Graph(id='time-series-graph-page2'),
        dcc.Interval(
            id='interval-component-page2',
            interval=5*60*1000,
            n_intervals=0
        )
    ])

app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    
    html.Div(id='page-1-container', children=layout_page1_content(), style={'display': 'none'}),
    html.Div(id='page-2-container', children=layout_page2_content(), style={'display': 'none'}),
])

# Update the callback for Page 1
@app.callback(
    Output('time-series-graph-page1', 'figure'),
    Input('interval-component-page1', 'n_intervals'),
    Input('country-dropdown-page1', 'value')
)
def update_graph_page1(n_intervals, selected_countries):
    current_df = fetch_data()
    current_df_melted = current_df.melt(id_vars=['cs_country_iso2', 'cs_stats_timestamp'],
                                        value_vars=['cs_asns_ris', 'cs_asns_stats'],
                                        var_name='metric', value_name='value')

    if selected_countries:
        current_df_melted = current_df_melted[current_df_melted['cs_country_iso2'].isin(selected_countries)]

    fig = px.line(current_df_melted,
                  x='cs_stats_timestamp',
                  y='value',
                  color='cs_country_iso2',
                  facet_col='metric',
                  facet_col_wrap=1,
                  title='Количественная автономных систем по странам',
                  labels={'cs_stats_timestamp': 'Дата', 'value': 'ASN', 'cs_country_iso2': 'Country'},
                  height=800)

    fig.update_yaxes(matches=None, rangemode="tozero")
    fig.for_each_annotation(lambda a: a.update(text=a.text.replace("metric=", "")))
    fig.update_layout(hovermode="x unified",
                      legend_itemclick="toggleothers",
                      legend=dict(x=1.02, y=1, xanchor='left', yanchor='top'))

    return fig

# New callback for Page 2
@app.callback(
    Output('time-series-graph-page2', 'figure'),
    Input('interval-component-page2', 'n_intervals'),
    Input('country-dropdown-page2-single', 'value') # Changed ID for single select
)
def update_graph_page2(n_intervals, selected_country): # Changed argument name
    current_df = fetch_data()
    current_df_melted = current_df.melt(id_vars=['cs_country_iso2', 'cs_stats_timestamp'],
                                        value_vars=['cs_asns_ris', 'cs_asns_stats'],
                                        var_name='metric', value_name='value')

    if selected_country: # Now a single country string
        current_df_melted = current_df_melted[current_df_melted['cs_country_iso2'] == selected_country]

    fig = px.line(current_df_melted,
                  x='cs_stats_timestamp',
                  y='value',
                  color='metric', # Color by metric to differentiate lines
                  line_dash='metric', # Use line dash to differentiate metrics
                  title=f'Country Statistics Over Time - Page 2 ({selected_country if selected_country else ""}) - ASNs RIS vs Stats',
                  labels={'cs_stats_timestamp': 'Date', 'value': 'Value', 'cs_country_iso2': 'Country'},
                  height=600) # Adjusted height as there are no facets

    fig.update_layout(hovermode="x unified",
                      legend_itemclick="toggleothers",
                      legend=dict(x=0.01, y=0.99, xanchor='left', yanchor='top', bgcolor='rgba(255,255,255,0.5)'),
                      yaxis_rangemode="tozero")

    return fig

@app.callback(
    Output('page-1-container', 'style'),
    Output('page-2-container', 'style'),
    Input('url', 'pathname')
)
def display_page(pathname):
    style_page1 = {'display': 'none'}
    style_page2 = {'display': 'none'}

    if pathname == '/page1':
        style_page1 = {'display': 'block'}
    elif pathname.startswith('/page2'):
        style_page2 = {'display': 'block'}
    else:
        style_page1 = {'display': 'block'} # Default to page 1

    return style_page1, style_page2

# New callback to update dropdown based on URL
@app.callback(
    Output('country-dropdown-page2-single', 'value'),
    Input('url', 'pathname')
)
def set_dropdown_value_from_url(pathname):
    if pathname and pathname.startswith('/page2/'):
        parts = pathname.split('/')
        if len(parts) > 2:
            country_code = parts[2].upper()
            if country_code in df['cs_country_iso2'].unique():
                return country_code
    return 'RU' # Default to RU if no country selected from URL


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8050, debug=True)
