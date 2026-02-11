# Copyright (c) Mike Kipnis - DashQL

import json
import os
from datetime import datetime, date, timedelta

import QuantLib as ql
import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output
import dash_ag_grid as dag

from Common.Components import UnderlyingSymbolMarketDataPanel
from Vol import VolPanel, OptionsPanel
from Vol import SurfacePanel


# =============================
# Vol Analytics Class
# =============================
class VolAnalytics:
    def __init__(self, app: dash.Dash):
        self.app = app
        self.prefix = "vol-analytics"

        # Panels
        self.underlying_symbol_market_data_panel = UnderlyingSymbolMarketDataPanel.UnderlyingSymbolMarketDataPanel(
            self.app, prefix=self.prefix
        )

        self.vol_panel = VolPanel.VolPanel(
            self.app, prefix=self.prefix
        )

        self.surface_panel = SurfacePanel.SurfacePanel(
            self.app, prefix=self.prefix, user_vol_market_data_id = self.vol_panel.user_vol_market_data_id
        )

        self.options_panel = OptionsPanel.OptionsPanel(
            self.app, prefix=self.prefix, user_market_data_id = self.underlying_symbol_market_data_panel.user_market_data_id
        )


    def layout(self):
        # Accordion with curve chart and bond panels
        accordion = dbc.Accordion(
            [
                dbc.AccordionItem(
                    [self.vol_panel.layout()],
                    title="Vols",
                    item_id="vols",
                ),
                dbc.AccordionItem(
                    [self.surface_panel.layout()],
                    title="Surfaces",
                    item_id="surfaces",
                ),
                dbc.AccordionItem(
                    [self.options_panel.layout()],
                    title="Options",
                    item_id="options",
                ),
            ],
            always_open=True,
            active_item=["vols", "options"],
        )

        # Full layout function
        return dbc.Container(
            fluid=True,
            children=[
                # Navbar
                dbc.Navbar(
                    dbc.Container(
                        [
                            dbc.NavbarBrand("Options", href="#", className="navbar-brand-custom"),
                            html.Div(
                                [
                                    dbc.Label(
                                        [
                                            html.Span("Evaluation Date: ", className="fw-bold"),
                                            html.Span(id="eval-date")
                                        ],
                                        className="navbar-label"
                                    )
                                ],
                                className="d-flex align-items-center",
                            ),
                        ],
                        fluid=True,
                    ),
                    className="custom-navbar",
                ),

                # Error Stores
                dcc.Store(id=self.vol_panel.error_prefix_id),
                dcc.Store(id=self.surface_panel.error_prefix_id),
                dcc.Store(id=self.options_panel.error_prefix_id),

                # Error banner
                html.Div(id="error-banner"),

                # Divider
                html.Hr(className="divider"),

                # Main content
                dbc.Row(
                    className="main-content-row flex-nowrap",
                    children=[
                        dbc.Col(
                            html.Div(
                                [
                                    html.Div(
                                        "S&P 100",
                                        style={
                                            "fontSize": "18px",
                                            "color": "#cccccc",
                                            "textAlign": "left",
                                            "margin": "4px",
                                        },
                                    ),
                                    self.underlying_symbol_market_data_panel.layout(),
                                    html.Div(
                                        "double-click quote to update the market data",
                                        style={
                                            "fontSize": "12px",
                                            "color": "#cccccc",
                                            "marginTop": "4px",
                                            "textAlign": "center",
                                        },
                                    ),
                                ],
                                style={"display": "flex", "flexDirection": "column"},
                            ),
                            width="auto",
                            style={"minWidth": "280px", "maxWidth": "280px"},
                            className="panel-col",
                        ),

                        # Right: Accordion + Support (full width)
                        dbc.Col(
                            html.Div(
                                [

                                    html.Div(
                                        id="underlying-symbol-description",
                                        style={
                                            "fontSize": "18px",
                                            "color": "#cccccc",
                                            "textAlign": "left",
                                            "margin": "4px",
                                        },
                                    ),
                                    accordion,  # existing accordion
                                    # Support section under accordion
                                    html.Div(
                                        [
                                            html.Div(
                                                [
                                                    html.Span(
                                                        [
                                                            "For support, contact: ",
                                                            html.A(
                                                                "mike.kipnis@gmail.com",
                                                                href="mailto:mike.kipnis@gmail.com",
                                                                style={
                                                                    "textDecoration": "underline",
                                                                    "color": "#cccccc",
                                                                },
                                                            ),
                                                        ]
                                                    ),
                                                    html.A(
                                                        "https://options.alpharesearch.online",
                                                        href="https://options.alpharesearch.online",
                                                        style={"textDecoration": "underline"},
                                                    ),
                                                ],
                                                style={
                                                    "display": "flex",
                                                    "justifyContent": "space-between",
                                                    "alignItems": "center",
                                                },
                                            )
                                        ],
                                        style={
                                            "fontSize": "12px",
                                            "color": "#AAAAAA",
                                            "marginTop": "8px",
                                            "textAlign": "center",  # center horizontally
                                            "width": "100%",  # make full width
                                        },
                                    ),
                                ],
                                style={
                                    "display": "flex",
                                    "flexDirection": "column",
                                    "width": "100%",  # container full width
                                },
                            ),
                            style={"flex": "1 1 auto", "minWidth": 0},
                            className="panel-col",
                        ),
                    ],
                ),

                dcc.Interval(id="startup", n_intervals=0, max_intervals=1),
                dcc.Store(id="underlying-symbol-market-data"),
                dcc.Store(id="vol-market-data"),
                dcc.Store(id="expiration-dates"),
                dcc.Store(id="selected-underlying-symbol"),
                dcc.Store(id="selected-underlying-vols"),
                dcc.Store(id="selected-expiration-date"),
            ],
        )


# =============================
# Dash App Initialization
# =============================
app = dash.Dash(
    __name__,
    title="Options Analytics",
    external_stylesheets=[dag.themes.BASE, dag.themes.BALHAM, dbc.themes.SUPERHERO],
    eager_loading=True
)

server = app.server  # Gunicorn expects this

vol_analytics = VolAnalytics(app)
app.layout = vol_analytics.layout()


# =============================
# Callbacks
# =============================
@app.callback(
    Output("eval-date", "children"),
    Output("underlying-symbol-market-data", "data"),
    Output("vol-market-data", "data"),
    Output("risk-free-rates", "data"),
    Input("startup", "n_intervals"),
)
def set_quantlib_business_date(_):
    debug_messages = []
    underlying_symbol_data = []
    risk_free_rates = []

    try:
        calendar = ql.TARGET()
        today = ql.Date.todaysDate()
        business_date = calendar.adjust(today, ql.ModifiedFollowing)
        ql.Settings.instance().evaluationDate = business_date

        debug_messages.append(f"Today: {today}, Business Date: {business_date}")

        with open("data/vols_indexed.json", "r") as f:
            options_pricing_data = json.load(f)

        weekday_cycle = [0, 2, 4]

        today_indexed = date.today()

        def next_future_weekday(start_date, target_weekday):
            days_ahead = (target_weekday - start_date.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7  # strictly future
            return start_date + timedelta(days=days_ahead)

        updated_exp_date_index = {}
        for symbol, indexed_vols in options_pricing_data['vols'].items():

            current_date = today_indexed

            vols_exp_date = {}
            for exp_date_index, vols in indexed_vols.items():
                idx = int(exp_date_index)

                weekday = weekday_cycle[(idx - 1) % 3]

                # ✅ always move forward from last expiration
                current_date = next_future_weekday(current_date, weekday)

                vols_float_keys = {'calls':vols['calls'], 'puts': vols['puts']}
                vols_exp_date[current_date.strftime('%Y-%m-%d')] = vols_float_keys

            updated_exp_date_index[symbol] = vols_exp_date

        underlying_symbol_data = options_pricing_data['underlying_symbols']
        vols_data = updated_exp_date_index
        risk_free_rates = options_pricing_data['rates']

    except Exception as e:
        debug_messages.append(f"Error: {str(e)}")

    return f"{business_date.to_date()}", underlying_symbol_data, vols_data, risk_free_rates


@app.callback(
    Output("error-banner", "children"),
    Output("error-banner", "style"),
    Input(vol_analytics.vol_panel.error_prefix_id, "data"),
    Input(vol_analytics.surface_panel.error_prefix_id, "data"),
    Input(vol_analytics.options_panel.error_prefix_id, "data"),
)
def set_global_error(*errors):
    for err in errors:
        if err:
            return html.Span(err["message"], style={"color": "#f75464"}), {"display": "block"}
    return None, {}

@app.callback(
    Output("underlying-symbol-description", "children"),
    Input("selected-underlying-symbol", "data"),
)
def set_description(underlying_symbol):
    return underlying_symbol['name']


# =============================
# Local Development
# =============================
if __name__ == "__main__":
    host = os.getenv("DASH_HOST", "127.0.0.1")
    port = int(os.getenv("DASH_PORT", "8050"))
    debug = os.getenv("DASH_DEBUG", "true").lower() == "true"

    app.run(host=host, port=port, debug=debug)
