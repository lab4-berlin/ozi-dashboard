import os
import dash
from dash import html, dcc, Input, Output, State
import plotly.express as px
import sqlalchemy
import pandas as pd
from datetime import datetime

# Global variables for caching
last_data_fetch_time = None
cached_df = None
last_connectivity_fetch_time = None
cached_connectivity_df = None
last_date_range_fetch_time = {}  # Cache per source_type
cached_date_ranges = {}  # Cache per source_type
country_names_ru = {}
country_names_en = {}
CACHE_TTL_SECONDS = 300  # Cache will be considered stale after 5 minutes (was 60)
DATE_RANGE_CACHE_TTL = 600  # Date ranges cache for 10 minutes


def fetch_data(start_date=None, end_date=None):
    global last_data_fetch_time, cached_df, country_names_ru, country_names_en

    # Check if cached data is still fresh
    if (
        cached_df is not None
        and last_data_fetch_time is not None
        and (datetime.now() - last_data_fetch_time).total_seconds() < CACHE_TTL_SECONDS
    ):
        print("Serving data from cache.")
        df = cached_df
    else:
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

        # Fetch country names in Russian and English
        query_countries = "SELECT c_iso2, c_name_ru, c_name FROM data.country;"
        df_countries = pd.read_sql(query_countries, engine)
        engine.dispose()

        # Populate country_names_ru and country_names_en dictionaries
        country_names_ru = {
            row["c_iso2"]: row["c_name_ru"] for index, row in df_countries.iterrows()
        }
        country_names_en = {
            row["c_iso2"]: row["c_name"] for index, row in df_countries.iterrows()
        }

        # Update cache and timestamp
        cached_df = df
        last_data_fetch_time = datetime.now()

        print(f"Fetched {len(df)} records from database")

    # Filter by date if provided
    if start_date and end_date:
        mask = (df["cs_stats_timestamp"] >= start_date) & (df["cs_stats_timestamp"] <= end_date)
        return df.loc[mask]
    
    return df


def fetch_connectivity_data(start_date=None, end_date=None):
    global last_connectivity_fetch_time, cached_connectivity_df

    # Check if cached data is still fresh
    if (
        cached_connectivity_df is not None
        and last_connectivity_fetch_time is not None
        and (datetime.now() - last_connectivity_fetch_time).total_seconds() < CACHE_TTL_SECONDS
    ):
        print("Serving connectivity data from cache.")
        df = cached_connectivity_df
    else:
        print("Fetching connectivity data from database...")
        db_url = (
            f"postgresql://{os.environ.get('POSTGRES_OZI_USER', 'user')}:"
            f"{os.environ.get('POSTGRES_OZI_PASSWORD', 'password')}"
            f"@{os.environ.get('DASH_DB_HOST', 'localhost')}:"
            f"{os.environ.get('DASH_DB_PORT', '5432')}/"
            f"{os.environ.get('DASH_DB_NAME', 'exampledb')}"
        )
        engine = sqlalchemy.create_engine(db_url)

        query = """SELECT 
                    asn_country,
                    date,
                    asn_count,
                    foreign_neighbour_count,
                    local_neighbour_count,
                    total_neighbour_count,
                    foreign_share_pct
                 FROM data.v_connectivity_index_distinct
                 ORDER BY date;"""
        df = pd.read_sql(query, engine)
        engine.dispose()

        # Update cache and timestamp
        cached_connectivity_df = df
        last_connectivity_fetch_time = datetime.now()

    # Filter by date if provided
    if start_date and end_date:
        mask = (df["date"] >= start_date) & (df["date"] <= end_date)
        return df.loc[mask]

    return df


app = dash.Dash(__name__)
app.suppress_callback_exceptions = True

# Add custom CSS for DatePicker
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            .DateInput_input {
                font-size: 13px !important;
                color: #000 !important;
                font-weight: 400 !important;
                padding: 6px 8px !important;
                height: 32px !important;
                border-radius: 5px !important;
            }
            .DateInput_input::placeholder {
                color: #495057 !important;
                opacity: 1 !important;
            }
            .Select-placeholder {
                color: #495057 !important;
            }
            .SingleDatePickerInput {
                height: 32px !important;
                border-radius: 5px !important;
            }
            .DateInput {
                width: 110px !important;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

@app.server.after_request
def add_security_headers(response):
    response.headers["X-Frame-Options"] = "ALLOW-FROM https://ozi-ru.net"
    return response


# Create Navigation Bar
def create_navbar():
    return html.Div(
        [
            dcc.Link('ASN Stats', href='/asn-stats', style={'padding': '10px', 'textDecoration': 'none', 'color': '#1f77b4'}),
            html.Span(' | ', style={'padding': '0 5px'}),
            dcc.Link('ASN Time Series', href='/asn-timeseries/RU', style={'padding': '10px', 'textDecoration': 'none', 'color': '#1f77b4'}),
            html.Span(' | ', style={'padding': '0 5px'}),
            dcc.Link('Global Connectivity', href='/global-connectivity', style={'padding': '10px', 'textDecoration': 'none', 'color': '#1f77b4'}),
            html.Span(' | ', style={'padding': '0 5px'}),
            dcc.Link('Глобальная связанность', href='/ru/global-connectivity', style={'padding': '10px', 'textDecoration': 'none', 'color': '#1f77b4'}),
            html.Span(' | ', style={'padding': '0 5px'}),
            dcc.Link('Local Connectivity', href='/local-connectivity', style={'padding': '10px', 'textDecoration': 'none', 'color': '#1f77b4'}),
            html.Span(' | ', style={'padding': '0 5px'}),
            dcc.Link('Локальная связанность', href='/ru/local-connectivity', style={'padding': '10px', 'textDecoration': 'none', 'color': '#1f77b4'}),
            html.Span(' | ', style={'padding': '0 5px'}),
            dcc.Link('Total Share', href='/total-share', style={'padding': '10px', 'textDecoration': 'none', 'color': '#1f77b4'}),
            html.Span(' | ', style={'padding': '0 5px'}),
            dcc.Link('Общая доля', href='/ru/total-share', style={'padding': '10px', 'textDecoration': 'none', 'color': '#1f77b4'}),
        ],
        style={
            'padding': '15px',
            'backgroundColor': '#f8f9fa',
            'borderBottom': '2px solid #dee2e6',
            'textAlign': 'center'
        }
    )

# Helper function to get available date range from database
def get_available_date_range(source_type='combined'):
    """
    Query database to find min and max dates actually available in data
    
    Args:
        source_type: 'stats', 'connectivity', or 'combined' (default)
    """
    global last_date_range_fetch_time, cached_date_ranges
    
    # Check cache first
    cache_key = source_type
    if (
        cache_key in cached_date_ranges
        and cache_key in last_date_range_fetch_time
        and (datetime.now() - last_date_range_fetch_time[cache_key]).total_seconds() < DATE_RANGE_CACHE_TTL
    ):
        print(f"Serving date range for {source_type} from cache")
        return cached_date_ranges[cache_key]
    
    try:
        db_url = (
            f"postgresql://{os.environ.get('POSTGRES_OZI_USER', 'user')}:"
            f"{os.environ.get('POSTGRES_OZI_PASSWORD', 'password')}"
            f"@{os.environ.get('DASH_DB_HOST', 'localhost')}:"
            f"{os.environ.get('DASH_DB_PORT', '5432')}/"
            f"{os.environ.get('DASH_DB_NAME', 'exampledb')}"
        )
        engine = sqlalchemy.create_engine(db_url)
        
        # Choose query based on source type
        if source_type == 'stats':
            query = """
                SELECT 
                    MIN(cs_stats_timestamp::date) as min_date,
                    MAX(cs_stats_timestamp::date) as max_date
                FROM data.country_stat
            """
        elif source_type == 'connectivity':
            query = """
                SELECT 
                    MIN(date::date) as min_date,
                    MAX(date::date) as max_date
                FROM data.v_connectivity_index_distinct
            """
        else:  # combined
            query = """
                SELECT 
                    MIN(date_col) as min_date,
                    MAX(date_col) as max_date
                FROM (
                    SELECT cs_stats_timestamp::date as date_col FROM data.country_stat
                    UNION ALL
                    SELECT date::date as date_col FROM data.v_connectivity_index_distinct
                ) combined_dates
            """
        
        result = pd.read_sql(query, engine)
        engine.dispose()
        
        if not result.empty and result['min_date'].iloc[0] is not None:
            min_date = pd.to_datetime(result['min_date'].iloc[0]).date()
            max_date = pd.to_datetime(result['max_date'].iloc[0]).date()
            
            # Cache the result
            cached_date_ranges[cache_key] = (min_date, max_date)
            last_date_range_fetch_time[cache_key] = datetime.now()
            
            return min_date, max_date
        else:
            # Fallback to default range if no data
            today = datetime.now().date()
            return today - timedelta(days=365*3), today
    except Exception as e:
        print(f"Error fetching date range for {source_type}: {e}")
        # Fallback to default range on error
        today = datetime.now().date()
        return today - timedelta(days=365*3), today

# Date Picker for specific data source
def create_date_picker(picker_id="global-date-picker", source_type='combined', label_suffix=''):
    """
    Create a date picker with data range from specified source
    
    Args:
        picker_id: ID for the date picker component
        source_type: 'stats', 'connectivity', or 'combined'
        label_suffix: Additional text to add to the label (e.g., '(Stats data)')
    """
    min_date, max_date = get_available_date_range(source_type)
    # Default selection: show full available data range
    default_start = min_date
    default_end = max_date
    
    data_source_label = {
        'stats': ' (Stats data)',
        'connectivity': ' (Connectivity data)',
        'combined': ''
    }.get(source_type, '')
    
    return html.Div(
        [
            html.Div([
                html.Label(f"Select Date Range{data_source_label}:", style={"fontWeight": "bold", "marginRight": "10px", "fontSize": "14px"}),
                dcc.DatePickerRange(
                    id=picker_id,
                    min_date_allowed=min_date,
                    max_date_allowed=max_date,
                    initial_visible_month=max_date,
                    start_date=default_start,
                    end_date=default_end,
                    display_format="YYYY-MM-DD",
                    style={"fontSize": "14px"}
                )
            ], style={"display": "flex", "alignItems": "center", "justifyContent": "center"}),
            html.Div(
                f"Available: {min_date} to {max_date}",
                style={"fontSize": "12px", "color": "#666", "textAlign": "center", "marginTop": "5px"}
            )
        ],
        style={"padding": "10px", "marginBottom": "20px"}
    )

# Layout for Page 1 (Original Dashboard)
def layout_page1_content(df):
    dropdown_options = []
    for country_iso in df["cs_country_iso2"].unique():
        english_name = country_names_en.get(country_iso, country_iso)
        dropdown_options.append({"label": f"{country_iso}, {english_name}", "value": country_iso})
    dropdown_options = sorted(dropdown_options, key=lambda k: k["label"])

    return html.Div([
        create_date_picker(picker_id="global-date-picker", source_type="stats"),
        html.H1("ASN Statistics"),
        html.Div([
            dcc.Dropdown(
                id="country-dropdown-page1",
                options=dropdown_options,
                value="RU",
                multi=False,
                placeholder="Select a country",
                closeOnSelect=True,
                clearable=False,
            )
        ], style={"width": "50%", "padding": "20px"}),
        dcc.Graph(id="time-series-graph-page1", style={"height": "600px"}),
        dcc.Interval(id="interval-component-page1", interval=5 * 60 * 1000, n_intervals=0),
    ])


# Layout for Page 2 (Copy of Original Dashboard)
def layout_page2_content(df):
    dropdown_options = []
    for country_iso in df["cs_country_iso2"].unique():
        russian_name = country_names_ru.get(country_iso, country_iso)
        dropdown_options.append({"label": f"{country_iso}, {russian_name}", "value": country_iso})
    dropdown_options = sorted(dropdown_options, key=lambda k: k["label"])

    return html.Div([
        create_date_picker(picker_id="global-date-picker", source_type="stats"),
        html.H1(f"Country Statistics"),
        html.Div([
            dcc.Dropdown(
                id="country-dropdown-page2-single",
                options=dropdown_options,
                multi=False,
                value="RU",
                placeholder="Select a country",
                closeOnSelect=True,
            )
        ], style={"width": "50%", "padding": "20px"}),
        dcc.Graph(id="time-series-graph-page2", style={"height": "600px"}),
        dcc.Interval(id="interval-component-page2", interval=5 * 60 * 1000, n_intervals=0),
    ])


# Layout for Page 3 - Foreign Neighbours (English)
def layout_page3_content(connectivity_df):
    dropdown_options = []
    for country_iso in connectivity_df["asn_country"].unique():
        english_name = country_names_en.get(country_iso, country_iso)
        dropdown_options.append({"label": f"{country_iso}, {english_name}", "value": country_iso})
    dropdown_options = sorted(dropdown_options, key=lambda k: k["label"])

    return html.Div([
        create_date_picker(picker_id="global-date-picker", source_type="connectivity"),
        html.H1("Global Connectivity Statistics"),
        html.Div([
            dcc.Dropdown(
                id="country-dropdown-page3",
                options=dropdown_options,
                value="RU",
                multi=False,
                placeholder="Select a country",
                closeOnSelect=True,
                clearable=False,
            )
        ], style={"width": "50%", "padding": "20px"}),
        dcc.Graph(id="time-series-graph-page3", style={"height": "600px"}),
        dcc.Interval(id="interval-component-page3", interval=5 * 60 * 1000, n_intervals=0),
    ])


# Layout for Page 4 - Foreign Neighbours (Russian)
def layout_page4_content(connectivity_df):
    dropdown_options = []
    for country_iso in connectivity_df["asn_country"].unique():
        russian_name = country_names_ru.get(country_iso, country_iso)
        dropdown_options.append({"label": f"{country_iso}, {russian_name}", "value": country_iso})
    dropdown_options = sorted(dropdown_options, key=lambda k: k["label"])

    return html.Div([
        create_date_picker(picker_id="global-date-picker", source_type="connectivity"),
        html.H1("Статистика глобальной связанности"),
        html.Div([
            dcc.Dropdown(
                id="country-dropdown-page4",
                options=dropdown_options,
                value="RU",
                multi=False,
                placeholder="Выберите страну",
                closeOnSelect=True,
                clearable=False,
            )
        ], style={"width": "50%", "padding": "20px"}),
        dcc.Graph(id="time-series-graph-page4", style={"height": "600px"}),
        dcc.Interval(id="interval-component-page4", interval=5 * 60 * 1000, n_intervals=0),
    ])


# Layout for Page 5 - Local Neighbours (English)
def layout_page5_content(connectivity_df):
    dropdown_options = []
    for country_iso in connectivity_df["asn_country"].unique():
        english_name = country_names_en.get(country_iso, country_iso)
        dropdown_options.append({"label": f"{country_iso}, {english_name}", "value": country_iso})
    dropdown_options = sorted(dropdown_options, key=lambda k: k["label"])

    return html.Div([
        create_date_picker(picker_id="global-date-picker", source_type="connectivity"),
        html.H1("Local Connectivity Statistics"),
        html.Div([
            dcc.Dropdown(
                id="country-dropdown-page5",
                options=dropdown_options,
                value="RU",
                multi=False,
                placeholder="Select a country",
                closeOnSelect=True,
                clearable=False,
            )
        ], style={"width": "50%", "padding": "20px"}),
        dcc.Graph(id="time-series-graph-page5", style={"height": "600px"}),
        dcc.Interval(id="interval-component-page5", interval=5 * 60 * 1000, n_intervals=0),
    ])


# Layout for Page 6 - Local Neighbours (Russian)
def layout_page6_content(connectivity_df):
    dropdown_options = []
    for country_iso in connectivity_df["asn_country"].unique():
        russian_name = country_names_ru.get(country_iso, country_iso)
        dropdown_options.append({"label": f"{country_iso}, {russian_name}", "value": country_iso})
    dropdown_options = sorted(dropdown_options, key=lambda k: k["label"])

    return html.Div([
        create_date_picker(picker_id="global-date-picker", source_type="connectivity"),
        html.H1("Статистика локальной связанности"),
        html.Div([
            dcc.Dropdown(
                id="country-dropdown-page6",
                options=dropdown_options,
                value="RU",
                multi=False,
                placeholder="Выберите страну",
                closeOnSelect=True,
                clearable=False,
            )
        ], style={"width": "50%", "padding": "20px"}),
        dcc.Graph(id="time-series-graph-page6", style={"height": "600px"}),
        dcc.Interval(id="interval-component-page6", interval=5 * 60 * 1000, n_intervals=0),
    ])


# Layout for Page 7 - Foreign Share (English)
def layout_page7_content(connectivity_df):
    dropdown_options = []
    for country_iso in connectivity_df["asn_country"].unique():
        english_name = country_names_en.get(country_iso, country_iso)
        dropdown_options.append({"label": f"{country_iso}, {english_name}", "value": country_iso})
    dropdown_options = sorted(dropdown_options, key=lambda k: k["label"])

    return html.Div([
        create_date_picker(picker_id="global-date-picker", source_type="connectivity"),
        html.H1("Total Connectivity Share"),
        html.Div([
            dcc.Dropdown(
                id="country-dropdown-page7",
                options=dropdown_options,
                value="RU",
                multi=False,
                placeholder="Select a country",
                closeOnSelect=True,
                clearable=False,
            )
        ], style={"width": "50%", "padding": "20px"}),
        dcc.Graph(id="time-series-graph-page7", style={"height": "600px"}),
        dcc.Interval(id="interval-component-page7", interval=5 * 60 * 1000, n_intervals=0),
    ])


# Layout for Page 8 - Foreign Share (Russian)
def layout_page8_content(connectivity_df):
    dropdown_options = []
    for country_iso in connectivity_df["asn_country"].unique():
        russian_name = country_names_ru.get(country_iso, country_iso)
        dropdown_options.append({"label": f"{country_iso}, {russian_name}", "value": country_iso})
    dropdown_options = sorted(dropdown_options, key=lambda k: k["label"])

    return html.Div([
        create_date_picker(picker_id="global-date-picker", source_type="connectivity"),
        html.H1("Общая доля связанности"),
        html.Div([
            dcc.Dropdown(
                id="country-dropdown-page8",
                options=dropdown_options,
                value="RU",
                multi=False,
                placeholder="Выберите страну",
                closeOnSelect=True,
                clearable=False,
            )
        ], style={"width": "50%", "padding": "20px"}),
        dcc.Graph(id="time-series-graph-page8", style={"height": "600px"}),
        dcc.Interval(id="interval-component-page8", interval=5 * 60 * 1000, n_intervals=0),
    ])


# Initial Data Fetch for Layouts
initial_df = fetch_data()
initial_connectivity_df = fetch_connectivity_data()

app.layout = html.Div(
    [
        dcc.Location(id="url", refresh=False),
        create_navbar(),
        html.Div(id="page-content")
    ]
)


# Callback to update page content based on URL
@app.callback(Output("page-content", "children"), Input("url", "pathname"))
def display_page(pathname):
    if pathname == "/asn-stats" or pathname == "/" or pathname == "/page1":
        return layout_page1_content(fetch_data())
    elif pathname.startswith("/asn-timeseries") or pathname == "/page2":
        return layout_page2_content(fetch_data())
    elif pathname == "/global-connectivity" or pathname == "/page3":
        return layout_page3_content(fetch_connectivity_data())
    elif pathname == "/ru/global-connectivity" or pathname == "/page4":
        return layout_page4_content(fetch_connectivity_data())
    elif pathname == "/local-connectivity" or pathname == "/page5":
        return layout_page5_content(fetch_connectivity_data())
    elif pathname == "/ru/local-connectivity" or pathname == "/page6":
        return layout_page6_content(fetch_connectivity_data())
    elif pathname == "/total-share" or pathname == "/page7":
        return layout_page7_content(fetch_connectivity_data())
    elif pathname == "/ru/total-share" or pathname == "/page8":
        return layout_page8_content(fetch_connectivity_data())
    else:
        # Default to Page 1
        return layout_page1_content(fetch_data())


# --- Callbacks for Graphs ---

# Page 1 Callback
@app.callback(
    Output("time-series-graph-page1", "figure"),
    [Input("interval-component-page1", "n_intervals"),
     Input("country-dropdown-page1", "value"),
     Input("global-date-picker", "start_date"),
     Input("global-date-picker", "end_date")]
)
def update_graph_page1(n_intervals, selected_country, start_date, end_date):
    current_df = fetch_data(start_date, end_date)
    current_df_melted = current_df.melt(
        id_vars=["cs_country_iso2", "cs_stats_timestamp"],
        value_vars=["cs_asns_ris", "cs_asns_stats"],
        var_name="metric",
        value_name="value",
    )

    if selected_country:
        current_df_melted = current_df_melted[current_df_melted["cs_country_iso2"] == selected_country]

    fig = px.scatter(
        current_df_melted,
        x="cs_stats_timestamp",
        y="value",
        color="metric",
        category_orders={"metric": ["cs_asns_stats", "cs_asns_ris"]},
        labels={
            "cs_stats_timestamp": "",
            "value": "Number of Autonomous Systems (ASN)",
            "metric": "Metric",
        },
        template="plotly_white",
    )

    fig.for_each_trace(lambda t: t.update(name=t.name.replace("cs_asns_ris", "ASN RIS").replace("cs_asns_stats", "ASN Stat")))
    fig.update_yaxes(rangemode="tozero")
    fig.update_layout(hovermode="x unified", legend=dict(x=0.5, y=1.05, xanchor="center", yanchor="bottom", orientation="h"))
    return fig


# Page 2 Callback
@app.callback(
    Output("time-series-graph-page2", "figure"),
    [Input("interval-component-page2", "n_intervals"),
     Input("country-dropdown-page2-single", "value"),
     Input("global-date-picker", "start_date"),
     Input("global-date-picker", "end_date")]
)
def update_graph_page2(n_intervals, selected_country, start_date, end_date):
    current_df = fetch_data(start_date, end_date)
    current_df_melted = current_df.melt(
        id_vars=["cs_country_iso2", "cs_stats_timestamp"],
        value_vars=["cs_asns_ris", "cs_asns_stats"],
        var_name="metric",
        value_name="value",
    )

    if selected_country:
        current_df_melted = current_df_melted[current_df_melted["cs_country_iso2"] == selected_country]

    fig = px.scatter(
        current_df_melted,
        x="cs_stats_timestamp",
        y="value",
        color="metric",
        title=f'Country Statistics - Page 2 ({selected_country if selected_country else ""})',
        labels={"cs_stats_timestamp": "Date", "value": "Value", "cs_country_iso2": "Country"},
        height=600,
    )
    fig.update_layout(hovermode="x unified", legend=dict(x=0.01, y=0.99, xanchor="left", yanchor="top", bgcolor="rgba(255,255,255,0.5)"), yaxis_rangemode="tozero")
    return fig


# Page 3 Callback
@app.callback(
    Output("time-series-graph-page3", "figure"),
    [Input("interval-component-page3", "n_intervals"),
     Input("country-dropdown-page3", "value"),
     Input("global-date-picker", "start_date"),
     Input("global-date-picker", "end_date")]
)
def update_graph_page3(n_intervals, selected_country, start_date, end_date):
    current_df = fetch_connectivity_data(start_date, end_date)
    if selected_country:
        current_df = current_df[current_df["asn_country"] == selected_country]
    
    # Filter by date range if dates are provided
    if date_from and date_to:
        current_df['date'] = pd.to_datetime(current_df['date'])
        date_from_dt = pd.to_datetime(date_from)
        date_to_dt = pd.to_datetime(date_to)
        current_df = current_df[(current_df['date'] >= date_from_dt) & (current_df['date'] <= date_to_dt)]
    
    fig = px.area(
        current_df,
        x="date",
        y="foreign_neighbour_count",
        color_discrete_sequence=["#4285F4"],
        labels={"date": "", "foreign_neighbour_count": "Foreign Neighbours"},
        template="plotly_white",
    )
    fig.update_traces(name="Foreign Neighbours", showlegend=False)
    fig.update_yaxes(rangemode="tozero")
    fig.update_layout(hovermode="x unified")
    return fig


# Page 4 Callback
@app.callback(
    Output("time-series-graph-page4", "figure"),
    [Input("interval-component-page4", "n_intervals"),
     Input("country-dropdown-page4", "value"),
     Input("global-date-picker", "start_date"),
     Input("global-date-picker", "end_date")]
)
def update_graph_page4(n_intervals, selected_country, start_date, end_date):
    current_df = fetch_connectivity_data(start_date, end_date)
    if selected_country:
        current_df = current_df[current_df["asn_country"] == selected_country]
    
    if date_from and date_to:
        current_df = current_df[
            (current_df["date"] >= date_from) &
            (current_df["date"] <= date_to)
        ]
    
    fig = px.area(
        current_df,
        x="date",
        y="foreign_neighbour_count",
        color_discrete_sequence=["#4285F4"],
        labels={"date": "", "foreign_neighbour_count": "Внешние соседи"},
    )
    fig.update_traces(name="Внешние соседи", showlegend=False)
    fig.update_yaxes(rangemode="tozero")
    fig.update_layout(hovermode="x unified")
    return fig


# Page 5 Callback
@app.callback(
    Output("time-series-graph-page5", "figure"),
    [Input("interval-component-page5", "n_intervals"),
     Input("country-dropdown-page5", "value"),
     Input("global-date-picker", "start_date"),
     Input("global-date-picker", "end_date")]
)
def update_graph_page5(n_intervals, selected_country, start_date, end_date):
    current_df = fetch_connectivity_data(start_date, end_date)
    if selected_country:
        current_df = current_df[current_df["asn_country"] == selected_country]
    
    if date_from and date_to:
        current_df = current_df[
            (current_df["date"] >= date_from) &
            (current_df["date"] <= date_to)
        ]
    
    fig = px.area(
        current_df,
        x="date",
        y="local_neighbour_count",
        color_discrete_sequence=["#EA4335"],
        labels={"date": "", "local_neighbour_count": "Local Neighbours"},
        template="plotly_white",
    )
    fig.update_traces(name="Local Neighbours", showlegend=False)
    fig.update_yaxes(rangemode="tozero")
    fig.update_layout(hovermode="x unified")
    return fig


# Page 6 Callback
@app.callback(
    Output("time-series-graph-page6", "figure"),
    [Input("interval-component-page6", "n_intervals"),
     Input("country-dropdown-page6", "value"),
     Input("global-date-picker", "start_date"),
     Input("global-date-picker", "end_date")]
)
def update_graph_page6(n_intervals, selected_country, start_date, end_date):
    current_df = fetch_connectivity_data(start_date, end_date)
    if selected_country:
        current_df = current_df[current_df["asn_country"] == selected_country]
    
    if date_from and date_to:
        current_df = current_df[
            (current_df["date"] >= date_from) &
            (current_df["date"] <= date_to)
        ]
    
    fig = px.area(
        current_df,
        x="date",
        y="local_neighbour_count",
        color_discrete_sequence=["#EA4335"],
        labels={"date": "", "local_neighbour_count": "Внутренние соседи"},
        template="plotly_white",
    )
    fig.update_traces(name="Внутренние соседи", showlegend=False)
    fig.update_yaxes(rangemode="tozero")
    fig.update_layout(hovermode="x unified")
    return fig


# Page 7 Callback
@app.callback(
    Output("time-series-graph-page7", "figure"),
    [Input("interval-component-page7", "n_intervals"),
     Input("country-dropdown-page7", "value"),
     Input("global-date-picker", "start_date"),
     Input("global-date-picker", "end_date")]
)
def update_graph_page7(n_intervals, selected_country, start_date, end_date):
    current_df = fetch_connectivity_data(start_date, end_date)
    if selected_country:
        current_df = current_df[current_df["asn_country"] == selected_country]
    
    fig = px.area(
        current_df,
        x="date",
        y="foreign_share_pct",
        color_discrete_sequence=["#34A853"],
        labels={"date": "", "foreign_share_pct": "Foreign Neighbours Share %"},
        template="plotly_white",
    )
    fig.update_traces(name="Foreign Share %", showlegend=False)
    fig.update_yaxes(rangemode="tozero")
    fig.update_layout(hovermode="x unified")
    return fig


# Page 8 Callback
@app.callback(
    Output("time-series-graph-page8", "figure"),
    [Input("interval-component-page8", "n_intervals"),
     Input("country-dropdown-page8", "value"),
     Input("global-date-picker", "start_date"),
     Input("global-date-picker", "end_date")]
)
def update_graph_page8(n_intervals, selected_country, start_date, end_date):
    current_df = fetch_connectivity_data(start_date, end_date)
    if selected_country:
        current_df = current_df[current_df["asn_country"] == selected_country]
    
    fig = px.area(
        current_df,
        x="date",
        y="foreign_share_pct",
        color_discrete_sequence=["#34A853"],
        labels={"date": "", "foreign_share_pct": "Доля внешних соседей %"},
        template="plotly_white",
    )
    fig.update_traces(name="Доля внешних %", showlegend=False)
    fig.update_yaxes(rangemode="tozero")
    fig.update_layout(hovermode="x unified")
    return fig

if __name__ == "__main__":
    app.run_server(debug=True, host="0.0.0.0", port=8050)
