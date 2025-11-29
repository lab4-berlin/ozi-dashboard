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
            html.Div(
                [
                    dcc.Dropdown(
                        id="country-dropdown-page1",
                        options=dropdown_options,
                        value="RU",
                        multi=False,
                        placeholder="Select a country",
                        closeOnSelect=True,
                        clearable=False,  # Prevent deselection
                    )
                ],
                style={"width": "50%", "padding": "20px"},
            ),
            html.Div(
                [dcc.Graph(id="time-series-graph-page1", style={"height": "100%"})],
                style={"flexGrow": "1", "height": "calc(100vh - 120px)"},
            ),  # Use flexGrow and 100% height, adjusted for header/footer if any
            dcc.Interval(
                id="interval-component-page1", interval=5 * 60 * 1000, n_intervals=0
            ),
        ]
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
            html.H1(f"Country Statistics Time Series - Page 2"),
            html.Div(
                [
                    dcc.Dropdown(
                        id="country-dropdown-page2-single",
                        options=dropdown_options,
                        multi=False,  # Single selection
                        value="RU",  # Default selected country
                        placeholder="Select a country",
                        closeOnSelect=True,
                    )
                ],
                style={"width": "50%", "padding": "20px"},
            ),
            dcc.Graph(id="time-series-graph-page2"),
            dcc.Interval(
                id="interval-component-page2", interval=5 * 60 * 1000, n_intervals=0
            ),
        ]
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
            html.H1("Global connectivity statistics"),
            html.Div(
                [
                    dcc.Dropdown(
                        id="country-dropdown-page3",
                        options=dropdown_options,
                        value="UA",
                        multi=False,
                        placeholder="Select a country",
                        closeOnSelect=True,
                        clearable=False,
                    )
                ],
                style={"width": "50%", "padding": "20px"},
            ),
            dcc.Graph(id="time-series-graph-page3"),
            dcc.Interval(
                id="interval-component-page3", interval=5 * 60 * 1000, n_intervals=0
            ),
        ]
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
            html.H1("Статистика глобальной связанности"),
            html.Div(
                [
                    dcc.Dropdown(
                        id="country-dropdown-page4",
                        options=dropdown_options,
                        value="UA",
                        multi=False,
                        placeholder="Выберите страну",
                        closeOnSelect=True,
                        clearable=False,
                    )
                ],
                style={"width": "50%", "padding": "20px"},
            ),
            dcc.Graph(id="time-series-graph-page4"),
            dcc.Interval(
                id="interval-component-page4", interval=5 * 60 * 1000, n_intervals=0
            ),
        ]
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
            html.H1("Local connectivity statistics"),
            html.Div(
                [
                    dcc.Dropdown(
                        id="country-dropdown-page5",
                        options=dropdown_options,
                        value="UA",
                        multi=False,
                        placeholder="Select a country",
                        closeOnSelect=True,
                        clearable=False,
                    )
                ],
                style={"width": "50%", "padding": "20px"},
            ),
            dcc.Graph(id="time-series-graph-page5"),
            dcc.Interval(
                id="interval-component-page5", interval=5 * 60 * 1000, n_intervals=0
            ),
        ]
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
            html.H1("Статистика локальной связанности"),
            html.Div(
                [
                    dcc.Dropdown(
                        id="country-dropdown-page6",
                        options=dropdown_options,
                        value="UA",
                        multi=False,
                        placeholder="Выберите страну",
                        closeOnSelect=True,
                        clearable=False,
                    )
                ],
                style={"width": "50%", "padding": "20px"},
            ),
            dcc.Graph(id="time-series-graph-page6"),
            dcc.Interval(
                id="interval-component-page6", interval=5 * 60 * 1000, n_intervals=0
            ),
        ]
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
            html.H1("Total connectivity share"),
            html.Div(
                [
                    dcc.Dropdown(
                        id="country-dropdown-page7",
                        options=dropdown_options,
                        value="UA",
                        multi=False,
                        placeholder="Select a country",
                        closeOnSelect=True,
                        clearable=False,
                    )
                ],
                style={"width": "50%", "padding": "20px"},
            ),
            dcc.Graph(id="time-series-graph-page7"),
            dcc.Interval(
                id="interval-component-page7", interval=5 * 60 * 1000, n_intervals=0
            ),
        ]
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
            html.H1("Общая доля связанности"),
            html.Div(
                [
                    dcc.Dropdown(
                        id="country-dropdown-page8",
                        options=dropdown_options,
                        value="UA",
                        multi=False,
                        placeholder="Выберите страну",
                        closeOnSelect=True,
                        clearable=False,
                    )
                ],
                style={"width": "50%", "padding": "20px"},
            ),
            dcc.Graph(id="time-series-graph-page8"),
            dcc.Interval(
                id="interval-component-page8", interval=5 * 60 * 1000, n_intervals=0
            ),
        ]
    )


app.layout = html.Div(
    [
        dcc.Location(id="url", refresh=False),
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
    Input("interval-component-page1", "n_intervals"),
    Input("country-dropdown-page1", "value"),
)
def update_graph_page1(n_intervals, selected_country):
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

    return fig


# New callback for Page 2
@app.callback(
    Output("time-series-graph-page2", "figure"),
    Input("interval-component-page2", "n_intervals"),
    Input("country-dropdown-page2-single", "value"),  # Changed ID for single select
)
def update_graph_page2(n_intervals, selected_country):  # Changed argument name
    current_df = fetch_data()
    current_df_melted = current_df.melt(
        id_vars=["cs_country_iso2", "cs_stats_timestamp"],
        value_vars=["cs_asns_ris", "cs_asns_stats"],
        var_name="metric",
        value_name="value",
    )

    if selected_country:  # Now a single country string
        current_df_melted = current_df_melted[
            current_df_melted["cs_country_iso2"] == selected_country
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

    return fig


# Callback for Page 3 - Foreign Neighbours (English)
@app.callback(
    Output("time-series-graph-page3", "figure"),
    Input("interval-component-page3", "n_intervals"),
    Input("country-dropdown-page3", "value"),
)
def update_graph_page3(n_intervals, selected_country):
    current_df = fetch_connectivity_data()
    
    if selected_country:
        current_df = current_df[current_df["asn_country"] == selected_country]
    
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
    
    return fig


# Callback for Page 4 - Foreign Neighbours (Russian)
@app.callback(
    Output("time-series-graph-page4", "figure"),
    Input("interval-component-page4", "n_intervals"),
    Input("country-dropdown-page4", "value"),
)
def update_graph_page4(n_intervals, selected_country):
    current_df = fetch_connectivity_data()
    
    if selected_country:
        current_df = current_df[current_df["asn_country"] == selected_country]
    
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
    
    return fig


# Callback for Page 5 - Local Neighbours (English)
@app.callback(
    Output("time-series-graph-page5", "figure"),
    Input("interval-component-page5", "n_intervals"),
    Input("country-dropdown-page5", "value"),
)
def update_graph_page5(n_intervals, selected_country):
    current_df = fetch_connectivity_data()
    
    if selected_country:
        current_df = current_df[current_df["asn_country"] == selected_country]
    
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
    
    return fig


# Callback for Page 6 - Local Neighbours (Russian)
@app.callback(
    Output("time-series-graph-page6", "figure"),
    Input("interval-component-page6", "n_intervals"),
    Input("country-dropdown-page6", "value"),
)
def update_graph_page6(n_intervals, selected_country):
    current_df = fetch_connectivity_data()
    
    if selected_country:
        current_df = current_df[current_df["asn_country"] == selected_country]
    
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
    
    return fig


# Callback for Page 7 - Foreign Share (English)
@app.callback(
    Output("time-series-graph-page7", "figure"),
    Input("interval-component-page7", "n_intervals"),
    Input("country-dropdown-page7", "value"),
)
def update_graph_page7(n_intervals, selected_country):
    current_df = fetch_connectivity_data()
    
    if selected_country:
        current_df = current_df[current_df["asn_country"] == selected_country]
    
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
    
    return fig


# Callback for Page 8 - Foreign Share (Russian)
@app.callback(
    Output("time-series-graph-page8", "figure"),
    Input("interval-component-page8", "n_intervals"),
    Input("country-dropdown-page8", "value"),
)
def update_graph_page8(n_intervals, selected_country):
    current_df = fetch_connectivity_data()
    
    if selected_country:
        current_df = current_df[current_df["asn_country"] == selected_country]
    
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
    
    return fig


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
    Output("country-dropdown-page2-single", "value"), Input("url", "pathname")
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
