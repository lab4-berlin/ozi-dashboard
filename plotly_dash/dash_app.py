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
country_names_ru = {}
country_names_en = {}
CACHE_TTL_SECONDS = 60  # Cache will be considered stale after 60 seconds


def fetch_data():
    global last_data_fetch_time, cached_df, country_names_ru, country_names_en

    # Check if cached data is still fresh
    if (
        cached_df is not None
        and last_data_fetch_time is not None
        and (datetime.now() - last_data_fetch_time).total_seconds() < CACHE_TTL_SECONDS
    ):
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

    print("\n--- Original DataFrame (df) ---")
    print(df.head())
    print(df.info())
    return df


def fetch_connectivity_data():
    global last_connectivity_fetch_time, cached_connectivity_df

    # Check if cached data is still fresh
    if (
        cached_connectivity_df is not None
        and last_connectivity_fetch_time is not None
        and (datetime.now() - last_connectivity_fetch_time).total_seconds() < CACHE_TTL_SECONDS
    ):
        print("Serving connectivity data from cache.")
        return cached_connectivity_df

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


df = fetch_data()

# Melt the DataFrame to long format for easier plotting of multiple metrics
df_melted = df.melt(
    id_vars=["cs_country_iso2", "cs_stats_timestamp"],
    value_vars=["cs_asns_ris", "cs_asns_stats"],
    var_name="metric",
    value_name="value",
)

print("\n--- Melted DataFrame (df_melted) ---")
print(df_melted.head())
print(df_melted.info())


# Function to create control panel (country + date range)
def create_control_panel(page_id, dropdown_options, language='en', data_source='connectivity'):
    """
    Creates a reusable control panel with country selection and date range picker.
    
    Args:
        page_id: Unique identifier for the page (e.g., 'page3', 'page4')
        dropdown_options: List of dropdown options for country selection
        language: 'en' or 'ru' for labels
        data_source: 'connectivity' for connectivity index pages, 'country_stat' for country statistics pages
    """
    if data_source == 'country_stat':
        # Use country_stat data for pages 1 and 2
        country_stat_df = fetch_data()
        min_date = country_stat_df['cs_stats_timestamp'].min() if len(country_stat_df) > 0 else None
        max_date = country_stat_df['cs_stats_timestamp'].max() if len(country_stat_df) > 0 else None
    else:
        # Use connectivity data for all other pages
        connectivity_df = fetch_connectivity_data()
        min_date = connectivity_df['date'].min() if len(connectivity_df) > 0 else None
        max_date = connectivity_df['date'].max() if len(connectivity_df) > 0 else None
    
    labels = {
        'en': {'country': 'Country:', 'date_range': 'Date Range:', 'date_from': 'Date from', 'date_to': 'Date to'},
        'ru': {'country': 'Страна:', 'date_range': 'Диапазон дат:', 'date_from': 'Date from', 'date_to': 'Date to'}
    }
    lang = labels.get(language, labels['en'])
    
    return html.Div(
        [
            # Country selection
            html.Div([
                html.Label(lang['country'], style={
                    "display": "block", 
                    "marginBottom": "8px", 
                    "fontWeight": "600", 
                    "fontSize": "12px",
                    "color": "#000",
                    "textTransform": "uppercase",
                    "letterSpacing": "0.5px"
                }),
                dcc.Dropdown(
                    id=f"country-dropdown-{page_id}",
                    options=dropdown_options,
                    value="RU",
                    multi=False,
                    placeholder=lang['country'].replace(':', ''),
                    closeOnSelect=True,
                    clearable=False,
                    style={"fontSize": "14px", "width": "100%"}
                )
            ], style={"marginBottom": "20px"}),
            
            # Date range selection
            html.Div([
                html.Label(lang['date_range'], style={
                    "display": "block", 
                    "marginBottom": "6px", 
                    "fontWeight": "600", 
                    "fontSize": "12px",
                    "color": "#000",
                    "textTransform": "uppercase",
                    "letterSpacing": "0.5px"
                }),
                html.Div([
                    dcc.DatePickerSingle(
                        id=f'date-from-{page_id}',
                        min_date_allowed=min_date,
                        max_date_allowed=max_date,
                        initial_visible_month=min_date,
                        date=min_date,
                        display_format='YYYY-MM-DD',
                        placeholder=lang['date_from'],
                        style={"fontSize": "13px", "marginRight": "8px"}
                    ),
                    html.Span("—", style={
                        "margin": "0 6px", 
                        "fontSize": "13px", 
                        "color": "#999",
                        "display": "inline-block",
                        "fontWeight": "300"
                    }),
                    dcc.DatePickerSingle(
                        id=f'date-to-{page_id}',
                        min_date_allowed=min_date,
                        max_date_allowed=max_date,
                        initial_visible_month=max_date,
                        date=max_date,
                        display_format='YYYY-MM-DD',
                        placeholder=lang['date_to'],
                        style={"fontSize": "13px", "marginRight": "12px"}
                    ),
                    html.Button('Apply', id=f'apply-dates-{page_id}', n_clicks=0, 
                              style={
                                  "padding": "6px 18px", 
                                  "cursor": "pointer", 
                                  "backgroundColor": "#1f77b4", 
                                  "color": "white", 
                                  "border": "none", 
                                  "borderRadius": "5px", 
                                  "fontWeight": "600", 
                                  "fontSize": "12px",
                                  "boxShadow": "0 2px 5px rgba(31, 119, 180, 0.3)",
                                  "transition": "all 0.2s",
                                  "height": "32px",
                                  "textTransform": "uppercase",
                                  "letterSpacing": "0.5px"
                              })
                ], style={
                    "display": "flex", 
                    "alignItems": "center",
                    "flexWrap": "wrap",
                    "gap": "6px"
                }),
            ]),
        ],
        style={
            "width": "100%", 
            "maxWidth": "1200px",
            "padding": "25px 30px", 
            "backgroundColor": "#f8f9fa",
            "borderRadius": "10px",
            "marginBottom": "25px",
            "margin": "0 auto",
            "boxShadow": "0 2px 8px rgba(0,0,0,0.05)"
        },
    )


# Layout for Page 1 (Original Dashboard)
def layout_page1_content():
    # Create dropdown options with English names
    dropdown_options = []
    for country_iso in df["cs_country_iso2"].unique():
        english_name = country_names_en.get(
            country_iso, country_iso
        )  # Fallback to ISO if English name not found
        dropdown_options.append(
            {"label": f"{country_iso}, {english_name}", "value": country_iso}
        )
    dropdown_options = sorted(dropdown_options, key=lambda k: k["label"])

    return html.Div(
        [
            html.H1("Country Statistics Time Series", style={
                "marginBottom": "25px",
                "fontSize": "28px",
                "fontWeight": "600",
                "color": "#1a1a1a"
            }),
            create_control_panel('page1', dropdown_options, 'en', data_source='country_stat'),
            dcc.Graph(
                id="time-series-graph-page1",
                config={'responsive': True},
                style={"width": "100%", "height": "70vh", "minHeight": "400px", "paddingLeft": "20px", "paddingRight": "20px"}
            ),
            dcc.Store(id='date-range-store-page1'),
            dcc.Interval(
                id="interval-component-page1", interval=5 * 60 * 1000, n_intervals=0
            ),
        ],
        style={
            "padding": "20px 20px",
            "maxWidth": "100%",
            "margin": "0 auto"
        }
    )


# Layout for Page 2 (Copy of Original Dashboard, can be modified later)
def layout_page2_content():
    # Create dropdown options with Russian names
    dropdown_options = []
    for country_iso in df["cs_country_iso2"].unique():
        russian_name = country_names_ru.get(
            country_iso, country_iso
        )  # Fallback to ISO if Russian name not found
        dropdown_options.append(
            {"label": f"{country_iso}, {russian_name}", "value": country_iso}
        )
    dropdown_options = sorted(dropdown_options, key=lambda k: k["label"])

    return html.Div(
        [
            html.H1("Статистика стран - временные ряды", style={
                "marginBottom": "25px",
                "fontSize": "28px",
                "fontWeight": "600",
                "color": "#1a1a1a"
            }),
            create_control_panel('page2', dropdown_options, 'ru', data_source='country_stat'),
            dcc.Graph(
                id="time-series-graph-page2",
                config={'responsive': True},
                style={"width": "100%", "height": "70vh", "minHeight": "400px", "paddingLeft": "20px", "paddingRight": "20px"}
            ),
            dcc.Store(id='date-range-store-page2'),
            dcc.Interval(
                id="interval-component-page2", interval=5 * 60 * 1000, n_intervals=0
            ),
        ],
        style={
            "padding": "20px 20px",
            "maxWidth": "100%",
            "margin": "0 auto"
        }
    )


# Layout for Page 3 - Foreign Neighbours (English)
def layout_page3_content():
    connectivity_df = fetch_connectivity_data()
    dropdown_options = []
    for country_iso in connectivity_df["asn_country"].unique():
        english_name = country_names_en.get(country_iso, country_iso)
        dropdown_options.append(
            {"label": f"{country_iso}, {english_name}", "value": country_iso}
        )
    dropdown_options = sorted(dropdown_options, key=lambda k: k["label"])

    return html.Div(
        [
            html.H1("Global connectivity statistics", style={
                "marginBottom": "25px",
                "fontSize": "28px",
                "fontWeight": "600",
                "color": "#1a1a1a"
            }),
            create_control_panel('page3', dropdown_options, 'en'),
            dcc.Graph(
                id="time-series-graph-page3",
                config={'responsive': True},
                style={"width": "100%", "height": "70vh", "minHeight": "400px", "paddingLeft": "20px", "paddingRight": "20px"}
            ),
            dcc.Store(id='date-range-store-page3'),
            dcc.Interval(
                id="interval-component-page3", interval=5 * 60 * 1000, n_intervals=0
            ),
        ],
        style={
            "padding": "20px 20px",
            "maxWidth": "100%",
            "margin": "0 auto"
        }
    )


# Layout for Page 4 - Foreign Neighbours (Russian)
def layout_page4_content():
    connectivity_df = fetch_connectivity_data()
    dropdown_options = []
    for country_iso in connectivity_df["asn_country"].unique():
        russian_name = country_names_ru.get(country_iso, country_iso)
        dropdown_options.append(
            {"label": f"{country_iso}, {russian_name}", "value": country_iso}
        )
    dropdown_options = sorted(dropdown_options, key=lambda k: k["label"])

    return html.Div(
        [
            html.H1("Статистика глобальной связанности", style={
                "marginBottom": "25px",
                "fontSize": "28px",
                "fontWeight": "600",
                "color": "#1a1a1a"
            }),
            create_control_panel('page4', dropdown_options, 'ru'),
            dcc.Graph(
                id="time-series-graph-page4",
                config={'responsive': True},
                style={"width": "100%", "height": "70vh", "minHeight": "400px", "paddingLeft": "20px", "paddingRight": "20px"}
            ),
            dcc.Store(id='date-range-store-page4'),
            dcc.Interval(
                id="interval-component-page4", interval=5 * 60 * 1000, n_intervals=0
            ),
        ],
        style={
            "padding": "20px 20px",
            "maxWidth": "100%",
            "margin": "0 auto"
        }
    )


# Layout for Page 5 - Local Neighbours (English)
def layout_page5_content():
    connectivity_df = fetch_connectivity_data()
    dropdown_options = []
    for country_iso in connectivity_df["asn_country"].unique():
        english_name = country_names_en.get(country_iso, country_iso)
        dropdown_options.append(
            {"label": f"{country_iso}, {english_name}", "value": country_iso}
        )
    dropdown_options = sorted(dropdown_options, key=lambda k: k["label"])

    return html.Div(
        [
            html.H1("Local connectivity statistics", style={
                "marginBottom": "25px",
                "fontSize": "28px",
                "fontWeight": "600",
                "color": "#1a1a1a"
            }),
            create_control_panel('page5', dropdown_options, 'en'),
            dcc.Graph(
                id="time-series-graph-page5",
                config={'responsive': True},
                style={"width": "100%", "height": "70vh", "minHeight": "400px", "paddingLeft": "20px", "paddingRight": "20px"}
            ),
            dcc.Store(id='date-range-store-page5'),
            dcc.Interval(
                id="interval-component-page5", interval=5 * 60 * 1000, n_intervals=0
            ),
        ],
        style={
            "padding": "20px 20px",
            "maxWidth": "100%",
            "margin": "0 auto"
        }
    )


# Layout for Page 6 - Local Neighbours (Russian)
def layout_page6_content():
    connectivity_df = fetch_connectivity_data()
    dropdown_options = []
    for country_iso in connectivity_df["asn_country"].unique():
        russian_name = country_names_ru.get(country_iso, country_iso)
        dropdown_options.append(
            {"label": f"{country_iso}, {russian_name}", "value": country_iso}
        )
    dropdown_options = sorted(dropdown_options, key=lambda k: k["label"])

    return html.Div(
        [
            html.H1("Статистика локальной связанности", style={
                "marginBottom": "25px",
                "fontSize": "28px",
                "fontWeight": "600",
                "color": "#1a1a1a"
            }),
            create_control_panel('page6', dropdown_options, 'ru'),
            dcc.Graph(
                id="time-series-graph-page6",
                config={'responsive': True},
                style={"width": "100%", "height": "70vh", "minHeight": "400px", "paddingLeft": "20px", "paddingRight": "20px"}
            ),
            dcc.Store(id='date-range-store-page6'),
            dcc.Interval(
                id="interval-component-page6", interval=5 * 60 * 1000, n_intervals=0
            ),
        ],
        style={
            "padding": "20px 20px",
            "maxWidth": "100%",
            "margin": "0 auto"
        }
    )


# Layout for Page 7 - Foreign Share (English)
def layout_page7_content():
    connectivity_df = fetch_connectivity_data()
    dropdown_options = []
    for country_iso in connectivity_df["asn_country"].unique():
        english_name = country_names_en.get(country_iso, country_iso)
        dropdown_options.append(
            {"label": f"{country_iso}, {english_name}", "value": country_iso}
        )
    dropdown_options = sorted(dropdown_options, key=lambda k: k["label"])

    return html.Div(
        [
            html.H1("Total connectivity share", style={
                "marginBottom": "25px",
                "fontSize": "28px",
                "fontWeight": "600",
                "color": "#1a1a1a"
            }),
            create_control_panel('page7', dropdown_options, 'en'),
            dcc.Graph(
                id="time-series-graph-page7",
                config={'responsive': True},
                style={"width": "100%", "height": "70vh", "minHeight": "400px", "paddingLeft": "20px", "paddingRight": "20px"}
            ),
            dcc.Store(id='date-range-store-page7'),
            dcc.Interval(
                id="interval-component-page7", interval=5 * 60 * 1000, n_intervals=0
            ),
        ],
        style={
            "padding": "20px 20px",
            "maxWidth": "100%",
            "margin": "0 auto"
        }
    )


# Layout for Page 8 - Foreign Share (Russian)
def layout_page8_content():
    connectivity_df = fetch_connectivity_data()
    dropdown_options = []
    for country_iso in connectivity_df["asn_country"].unique():
        russian_name = country_names_ru.get(country_iso, country_iso)
        dropdown_options.append(
            {"label": f"{country_iso}, {russian_name}", "value": country_iso}
        )
    dropdown_options = sorted(dropdown_options, key=lambda k: k["label"])

    return html.Div(
        [
            html.H1("Общая доля связанности", style={
                "marginBottom": "25px",
                "fontSize": "28px",
                "fontWeight": "600",
                "color": "#1a1a1a"
            }),
            create_control_panel('page8', dropdown_options, 'ru'),
            dcc.Graph(
                id="time-series-graph-page8",
                config={'responsive': True},
                style={"width": "100%", "height": "70vh", "minHeight": "400px", "paddingLeft": "20px", "paddingRight": "20px"}
            ),
            dcc.Store(id='date-range-store-page8'),
            dcc.Interval(
                id="interval-component-page8", interval=5 * 60 * 1000, n_intervals=0
            ),
        ],
        style={
            "padding": "20px 20px",
            "maxWidth": "100%",
            "margin": "0 auto"
        }
    )


app.layout = html.Div(
    [
        dcc.Location(id="url", refresh=False),
        # Navigation menu
        html.Div(
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
        ),
        html.Div(
            id="page-1-container",
            children=layout_page1_content(),
            style={"display": "none"},
        ),
        html.Div(
            id="page-2-container",
            children=layout_page2_content(),
            style={"display": "none"},
        ),
        html.Div(
            id="page-3-container",
            children=layout_page3_content(),
            style={"display": "none"},
        ),
        html.Div(
            id="page-4-container",
            children=layout_page4_content(),
            style={"display": "none"},
        ),
        html.Div(
            id="page-5-container",
            children=layout_page5_content(),
            style={"display": "none"},
        ),
        html.Div(
            id="page-6-container",
            children=layout_page6_content(),
            style={"display": "none"},
        ),
        html.Div(
            id="page-7-container",
            children=layout_page7_content(),
            style={"display": "none"},
        ),
        html.Div(
            id="page-8-container",
            children=layout_page8_content(),
            style={"display": "none"},
        ),
    ]
)


# Update the callback for Page 1
@app.callback(
    Output("time-series-graph-page1", "figure"),
    Output("date-range-store-page1", "data"),
    Input("interval-component-page1", "n_intervals"),
    Input("country-dropdown-page1", "value"),
    Input("apply-dates-page1", "n_clicks"),
    State("date-from-page1", "date"),
    State("date-to-page1", "date"),
)
def update_graph_page1(n_intervals, selected_country, n_clicks, date_from, date_to):
    current_df = fetch_data()
    current_df_melted = current_df.melt(
        id_vars=["cs_country_iso2", "cs_stats_timestamp"],
        value_vars=["cs_asns_ris", "cs_asns_stats"],
        var_name="metric",
        value_name="value",
    )

    if selected_country:
        current_df_melted = current_df_melted[
            current_df_melted["cs_country_iso2"] == selected_country
        ]
    
    # Apply date filtering
    if date_from and date_to:
        current_df_melted = current_df_melted[
            (current_df_melted["cs_stats_timestamp"] >= date_from) &
            (current_df_melted["cs_stats_timestamp"] <= date_to)
        ]

    fig = px.scatter(
        current_df_melted,
        x="cs_stats_timestamp",
        y="value",
        color="metric",  # Color by metric to differentiate lines
        category_orders={"metric": ["cs_asns_stats", "cs_asns_ris"]}, # Order legends
        labels={
            "cs_stats_timestamp": "",
            "value": "Number of Autonomous Systems (ASN)",
            "metric": "Metric",
        },
        template="plotly_white",
    )  # Use a light but contrasting style

    fig.for_each_trace(
        lambda t: t.update(
            name=t.name.replace("cs_asns_ris", "ASN RIS").replace(
                "cs_asns_stats", "ASN Stat"
            )
        )
    )
    # fig.update_traces(line=dict(width=3))  # Make lines thicker

    fig.update_yaxes(rangemode="tozero")  # Ensure y-axis starts from 0
    fig.update_layout(
        hovermode="x unified",
        legend_itemclick="toggleothers",
        legend=dict(
            x=0.5,
            y=1.05,
            xanchor="center",
            yanchor="bottom",
            orientation="h",
            title_text="",
        ),
    )

    date_range = {"start": date_from, "end": date_to} if date_from and date_to else None
    return fig, date_range


# New callback for Page 2
@app.callback(
    Output("time-series-graph-page2", "figure"),
    Output("date-range-store-page2", "data"),
    Input("interval-component-page2", "n_intervals"),
    Input("country-dropdown-page2", "value"),
    Input("apply-dates-page2", "n_clicks"),
    State("date-from-page2", "date"),
    State("date-to-page2", "date"),
)
def update_graph_page2(n_intervals, selected_country, n_clicks, date_from, date_to):
    current_df = fetch_data()
    current_df_melted = current_df.melt(
        id_vars=["cs_country_iso2", "cs_stats_timestamp"],
        value_vars=["cs_asns_ris", "cs_asns_stats"],
        var_name="metric",
        value_name="value",
    )

    if selected_country:
        current_df_melted = current_df_melted[
            current_df_melted["cs_country_iso2"] == selected_country
        ]
    
    # Apply date filtering
    if date_from and date_to:
        current_df_melted = current_df_melted[
            (current_df_melted["cs_stats_timestamp"] >= date_from) &
            (current_df_melted["cs_stats_timestamp"] <= date_to)
        ]

    fig = px.scatter(
        current_df_melted,
        x="cs_stats_timestamp",
        y="value",
        color="metric",  # Color by metric to differentiate lines
        title=f'Country Statistics Over Time - Page 2 ({selected_country if selected_country else ""}) - ASNs RIS vs Stats',
        labels={
            "cs_stats_timestamp": "Date",
            "value": "Value",
            "cs_country_iso2": "Country",
        },
        height=600,
    )  # Adjusted height as there are no facets

    fig.update_layout(
        hovermode="x unified",
        legend_itemclick="toggleothers",
        legend=dict(
            x=0.01,
            y=0.99,
            xanchor="left",
            yanchor="top",
            bgcolor="rgba(255,255,255,0.5)",
        ),
        yaxis_rangemode="tozero",
    )

    date_range = {"start": date_from, "end": date_to} if date_from and date_to else None
    return fig, date_range


# Callback for Page 3 - Foreign Neighbours (English)
@app.callback(
    Output("time-series-graph-page3", "figure"),
    Output("date-range-store-page3", "data"),
    Input("interval-component-page3", "n_intervals"),
    Input("country-dropdown-page3", "value"),
    Input("apply-dates-page3", "n_clicks"),
    State("date-from-page3", "date"),
    State("date-to-page3", "date"),
)
def update_graph_page3(n_intervals, selected_country, n_clicks, date_from, date_to):
    current_df = fetch_connectivity_data()
    
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
        labels={
            "date": "",
            "foreign_neighbour_count": "Foreign Neighbours",
        },
        template="plotly_white",
    )
    
    fig.update_traces(name="Foreign Neighbours", showlegend=False)
    fig.update_yaxes(rangemode="tozero")
    fig.update_layout(hovermode="x unified")
    
    # Store current date range
    date_range = {"start": date_from, "end": date_to}
    
    return fig, date_range


# Callback to sync date pickers when graph is zoomed - Page 1
@app.callback(
    Output("date-from-page1", "date"),
    Output("date-to-page1", "date"),
    Input("time-series-graph-page1", "relayoutData"),
    State("date-range-store-page1", "data"),
    prevent_initial_call=True
)
def sync_dates_from_graph_page1(relayout_data, current_range):
    if relayout_data and 'xaxis.range[0]' in relayout_data and 'xaxis.range[1]' in relayout_data:
        start_date = relayout_data['xaxis.range[0]'].split('T')[0] if 'T' in relayout_data['xaxis.range[0]'] else relayout_data['xaxis.range[0]']
        end_date = relayout_data['xaxis.range[1]'].split('T')[0] if 'T' in relayout_data['xaxis.range[1]'] else relayout_data['xaxis.range[1]']
        return start_date, end_date
    if current_range:
        return current_range.get("start"), current_range.get("end")
    return None, None


# Callback to sync date pickers when graph is zoomed - Page 2
@app.callback(
    Output("date-from-page2", "date"),
    Output("date-to-page2", "date"),
    Input("time-series-graph-page2", "relayoutData"),
    State("date-range-store-page2", "data"),
    prevent_initial_call=True
)
def sync_dates_from_graph_page2(relayout_data, current_range):
    if relayout_data and 'xaxis.range[0]' in relayout_data and 'xaxis.range[1]' in relayout_data:
        start_date = relayout_data['xaxis.range[0]'].split('T')[0] if 'T' in relayout_data['xaxis.range[0]'] else relayout_data['xaxis.range[0]']
        end_date = relayout_data['xaxis.range[1]'].split('T')[0] if 'T' in relayout_data['xaxis.range[1]'] else relayout_data['xaxis.range[1]']
        return start_date, end_date
    if current_range:
        return current_range.get("start"), current_range.get("end")
    return None, None


# Callback to sync date pickers when graph is zoomed - Page 3
@app.callback(
    Output("date-from-page3", "date"),
    Output("date-to-page3", "date"),
    Input("time-series-graph-page3", "relayoutData"),
    State("date-range-store-page3", "data"),
    prevent_initial_call=True
)
def sync_dates_from_graph_page3(relayout_data, current_range):
    if relayout_data and 'xaxis.range[0]' in relayout_data and 'xaxis.range[1]' in relayout_data:
        # Extract date range from zoom/pan
        start_date = relayout_data['xaxis.range[0]'].split('T')[0] if 'T' in relayout_data['xaxis.range[0]'] else relayout_data['xaxis.range[0]']
        end_date = relayout_data['xaxis.range[1]'].split('T')[0] if 'T' in relayout_data['xaxis.range[1]'] else relayout_data['xaxis.range[1]']
        return start_date, end_date
    
    # Return current values if no zoom
    if current_range:
        return current_range.get("start"), current_range.get("end")
    
    return None, None


# Callback to sync date pickers when graph is zoomed - Page 4
@app.callback(
    Output("date-from-page4", "date"),
    Output("date-to-page4", "date"),
    Input("time-series-graph-page4", "relayoutData"),
    State("date-range-store-page4", "data"),
    prevent_initial_call=True
)
def sync_dates_from_graph_page4(relayout_data, current_range):
    if relayout_data and 'xaxis.range[0]' in relayout_data and 'xaxis.range[1]' in relayout_data:
        start_date = relayout_data['xaxis.range[0]'].split('T')[0] if 'T' in relayout_data['xaxis.range[0]'] else relayout_data['xaxis.range[0]']
        end_date = relayout_data['xaxis.range[1]'].split('T')[0] if 'T' in relayout_data['xaxis.range[1]'] else relayout_data['xaxis.range[1]']
        return start_date, end_date
    if current_range:
        return current_range.get("start"), current_range.get("end")
    return None, None


# Callback to sync date pickers when graph is zoomed - Page 5
@app.callback(
    Output("date-from-page5", "date"),
    Output("date-to-page5", "date"),
    Input("time-series-graph-page5", "relayoutData"),
    State("date-range-store-page5", "data"),
    prevent_initial_call=True
)
def sync_dates_from_graph_page5(relayout_data, current_range):
    if relayout_data and 'xaxis.range[0]' in relayout_data and 'xaxis.range[1]' in relayout_data:
        start_date = relayout_data['xaxis.range[0]'].split('T')[0] if 'T' in relayout_data['xaxis.range[0]'] else relayout_data['xaxis.range[0]']
        end_date = relayout_data['xaxis.range[1]'].split('T')[0] if 'T' in relayout_data['xaxis.range[1]'] else relayout_data['xaxis.range[1]']
        return start_date, end_date
    if current_range:
        return current_range.get("start"), current_range.get("end")
    return None, None


# Callback to sync date pickers when graph is zoomed - Page 6
@app.callback(
    Output("date-from-page6", "date"),
    Output("date-to-page6", "date"),
    Input("time-series-graph-page6", "relayoutData"),
    State("date-range-store-page6", "data"),
    prevent_initial_call=True
)
def sync_dates_from_graph_page6(relayout_data, current_range):
    if relayout_data and 'xaxis.range[0]' in relayout_data and 'xaxis.range[1]' in relayout_data:
        start_date = relayout_data['xaxis.range[0]'].split('T')[0] if 'T' in relayout_data['xaxis.range[0]'] else relayout_data['xaxis.range[0]']
        end_date = relayout_data['xaxis.range[1]'].split('T')[0] if 'T' in relayout_data['xaxis.range[1]'] else relayout_data['xaxis.range[1]']
        return start_date, end_date
    if current_range:
        return current_range.get("start"), current_range.get("end")
    return None, None


# Callback to sync date pickers when graph is zoomed - Page 7
@app.callback(
    Output("date-from-page7", "date"),
    Output("date-to-page7", "date"),
    Input("time-series-graph-page7", "relayoutData"),
    State("date-range-store-page7", "data"),
    prevent_initial_call=True
)
def sync_dates_from_graph_page7(relayout_data, current_range):
    if relayout_data and 'xaxis.range[0]' in relayout_data and 'xaxis.range[1]' in relayout_data:
        start_date = relayout_data['xaxis.range[0]'].split('T')[0] if 'T' in relayout_data['xaxis.range[0]'] else relayout_data['xaxis.range[0]']
        end_date = relayout_data['xaxis.range[1]'].split('T')[0] if 'T' in relayout_data['xaxis.range[1]'] else relayout_data['xaxis.range[1]']
        return start_date, end_date
    if current_range:
        return current_range.get("start"), current_range.get("end")
    return None, None


# Callback to sync date pickers when graph is zoomed - Page 8
@app.callback(
    Output("date-from-page8", "date"),
    Output("date-to-page8", "date"),
    Input("time-series-graph-page8", "relayoutData"),
    State("date-range-store-page8", "data"),
    prevent_initial_call=True
)
def sync_dates_from_graph_page8(relayout_data, current_range):
    if relayout_data and 'xaxis.range[0]' in relayout_data and 'xaxis.range[1]' in relayout_data:
        start_date = relayout_data['xaxis.range[0]'].split('T')[0] if 'T' in relayout_data['xaxis.range[0]'] else relayout_data['xaxis.range[0]']
        end_date = relayout_data['xaxis.range[1]'].split('T')[0] if 'T' in relayout_data['xaxis.range[1]'] else relayout_data['xaxis.range[1]']
        return start_date, end_date
    if current_range:
        return current_range.get("start"), current_range.get("end")
    return None, None


# Callback for Page 4 - Foreign Neighbours (Russian)
@app.callback(
    Output("time-series-graph-page4", "figure"),
    Output("date-range-store-page4", "data"),
    Input("interval-component-page4", "n_intervals"),
    Input("country-dropdown-page4", "value"),
    Input("apply-dates-page4", "n_clicks"),
    State("date-from-page4", "date"),
    State("date-to-page4", "date"),
)
def update_graph_page4(n_intervals, selected_country, n_clicks, date_from, date_to):
    current_df = fetch_connectivity_data()
    
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
        labels={
            "date": "",
            "foreign_neighbour_count": "Внешние соседи",
        },
    )
    
    fig.update_traces(name="Внешние соседи", showlegend=False)
    fig.update_yaxes(rangemode="tozero")
    fig.update_layout(hovermode="x unified")
    
    date_range = {"start": date_from, "end": date_to} if date_from and date_to else None
    return fig, date_range


# Callback for Page 5 - Local Neighbours (English)
@app.callback(
    Output("time-series-graph-page5", "figure"),
    Output("date-range-store-page5", "data"),
    Input("interval-component-page5", "n_intervals"),
    Input("country-dropdown-page5", "value"),
    Input("apply-dates-page5", "n_clicks"),
    State("date-from-page5", "date"),
    State("date-to-page5", "date"),
)
def update_graph_page5(n_intervals, selected_country, n_clicks, date_from, date_to):
    current_df = fetch_connectivity_data()
    
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
        labels={
            "date": "",
            "local_neighbour_count": "Local Neighbours",
        },
        template="plotly_white",
    )
    
    fig.update_traces(name="Local Neighbours", showlegend=False)
    fig.update_yaxes(rangemode="tozero")
    fig.update_layout(hovermode="x unified")
    
    date_range = {"start": date_from, "end": date_to} if date_from and date_to else None
    return fig, date_range


# Callback for Page 6 - Local Neighbours (Russian)
@app.callback(
    Output("time-series-graph-page6", "figure"),
    Output("date-range-store-page6", "data"),
    Input("interval-component-page6", "n_intervals"),
    Input("country-dropdown-page6", "value"),
    Input("apply-dates-page6", "n_clicks"),
    State("date-from-page6", "date"),
    State("date-to-page6", "date"),
)
def update_graph_page6(n_intervals, selected_country, n_clicks, date_from, date_to):
    current_df = fetch_connectivity_data()
    
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
        labels={
            "date": "",
            "local_neighbour_count": "Внутренние соседи",
        },
        template="plotly_white",
    )
    
    fig.update_traces(name="Внутренние соседи", showlegend=False)
    fig.update_yaxes(rangemode="tozero")
    fig.update_layout(hovermode="x unified")
    
    date_range = {"start": date_from, "end": date_to} if date_from and date_to else None
    return fig, date_range


# Callback for Page 7 - Foreign Share (English)
@app.callback(
    Output("time-series-graph-page7", "figure"),
    Output("date-range-store-page7", "data"),
    Input("interval-component-page7", "n_intervals"),
    Input("country-dropdown-page7", "value"),
    Input("apply-dates-page7", "n_clicks"),
    State("date-from-page7", "date"),
    State("date-to-page7", "date"),
)
def update_graph_page7(n_intervals, selected_country, n_clicks, date_from, date_to):
    current_df = fetch_connectivity_data()
    
    if selected_country:
        current_df = current_df[current_df["asn_country"] == selected_country]
    
    if date_from and date_to:
        current_df = current_df[
            (current_df["date"] >= date_from) &
            (current_df["date"] <= date_to)
        ]
    
    # foreign_share_pct already in percent from view
    
    fig = px.area(
        current_df,
        x="date",
        y="foreign_share_pct",
        color_discrete_sequence=["#34A853"],
        labels={
            "date": "",
            "foreign_share_pct": "Foreign Neighbours Share %",
        },
        template="plotly_white",
    )
    
    fig.update_traces(name="Foreign Share %", showlegend=False)
    fig.update_yaxes(rangemode="tozero")
    fig.update_layout(hovermode="x unified")
    
    date_range = {"start": date_from, "end": date_to} if date_from and date_to else None
    return fig, date_range


# Callback for Page 8 - Foreign Share (Russian)
@app.callback(
    Output("time-series-graph-page8", "figure"),
    Output("date-range-store-page8", "data"),
    Input("interval-component-page8", "n_intervals"),
    Input("country-dropdown-page8", "value"),
    Input("apply-dates-page8", "n_clicks"),
    State("date-from-page8", "date"),
    State("date-to-page8", "date"),
)
def update_graph_page8(n_intervals, selected_country, n_clicks, date_from, date_to):
    current_df = fetch_connectivity_data()
    
    if selected_country:
        current_df = current_df[current_df["asn_country"] == selected_country]
    
    if date_from and date_to:
        current_df = current_df[
            (current_df["date"] >= date_from) &
            (current_df["date"] <= date_to)
        ]
    
    # foreign_share_pct already in percent from view
    
    fig = px.area(
        current_df,
        x="date",
        y="foreign_share_pct",
        color_discrete_sequence=["#34A853"],
        labels={
            "date": "",
            "foreign_share_pct": "Доля внешних соседей %",
        },
        template="plotly_white",
    )
    
    fig.update_traces(name="Доля внешних %", showlegend=False)
    fig.update_yaxes(rangemode="tozero")
    fig.update_layout(hovermode="x unified")
    
    date_range = {"start": date_from, "end": date_to} if date_from and date_to else None
    return fig, date_range


@app.callback(
    Output("page-1-container", "style"),
    Output("page-2-container", "style"),
    Output("page-3-container", "style"),
    Output("page-4-container", "style"),
    Output("page-5-container", "style"),
    Output("page-6-container", "style"),
    Output("page-7-container", "style"),
    Output("page-8-container", "style"),
    Input("url", "pathname"),
)
def display_page(pathname):
    styles = [{"display": "none"}] * 8

    if pathname == "/asn-stats" or pathname == "/page1":
        styles[0] = {"display": "block"}
    elif pathname.startswith("/asn-timeseries") or pathname.startswith("/page2"):
        styles[1] = {"display": "block"}
    elif pathname == "/global-connectivity" or pathname == "/page3":
        styles[2] = {"display": "block"}
    elif pathname == "/ru/global-connectivity" or pathname == "/page4":
        styles[3] = {"display": "block"}
    elif pathname == "/local-connectivity" or pathname == "/page5":
        styles[4] = {"display": "block"}
    elif pathname == "/ru/local-connectivity" or pathname == "/page6":
        styles[5] = {"display": "block"}
    elif pathname == "/total-share" or pathname == "/page7":
        styles[6] = {"display": "block"}
    elif pathname == "/ru/total-share" or pathname == "/page8":
        styles[7] = {"display": "block"}
    else:
        styles[0] = {"display": "block"}  # Default to page 1

    return styles[0], styles[1], styles[2], styles[3], styles[4], styles[5], styles[6], styles[7]


# New callback to update dropdown based on URL
@app.callback(
    Output("country-dropdown-page2", "value"), Input("url", "pathname")
)
def set_dropdown_value_from_url(pathname):
    if pathname and (pathname.startswith("/asn-timeseries/") or pathname.startswith("/page2/")):
        parts = pathname.split("/")
        if len(parts) > 2:
            country_code = parts[-1].upper()  # Get last part of URL
            if country_code in df["cs_country_iso2"].unique():
                return country_code
    return "RU"  # Default to RU if no country selected from URL


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8050, debug=False)
