import json
import os
from datetime import datetime

import QuantLib as ql
import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output

from Common.Components import CurveMarketDataPanel
from Common.Utils import CurveUtils
from Rates import FixedRateBondPanel, FloatingRateBondPanel, ZeroCouponBondPanel, CurvePanel, OISMidCurvePanel


# =============================
# Rates Analytics Class
# =============================
class RatesAnalytics:
    def __init__(self, app: dash.Dash):
        self.app = app
        self.prefix = "rates-analytics"

        # Panels
        self.curve_market_data_panel = CurveMarketDataPanel.CurveMarketDataPanel(
            self.app, prefix=self.prefix
        )

        self.curve_chart_panel = CurvePanel.CurvePanel(
            self.app, curve_market_data_panel=self.curve_market_data_panel, prefix=self.prefix
        )

        self.fixed_rate_bond_panel = FixedRateBondPanel.FixedRateBondPanel(
            self.app, prefix=self.prefix, user_market_data_id=self.curve_market_data_panel.user_market_data_id
        )

        self.floating_rate_bond_panel = FloatingRateBondPanel.FloatingRateBondPanel(
            self.app, prefix=self.prefix
        )

        self.zero_coupon_bond_panel = ZeroCouponBondPanel.ZeroCouponBondPanel(
            self.app, prefix=self.prefix
        )

        self.ois_mid_curve_panel = OISMidCurvePanel.OISMidCurvePanel(
            self.app, prefix=self.prefix, user_market_data_id=self.curve_market_data_panel.user_market_data_id
        )

    def layout(self):
        # Accordion with curve chart and bond panels
        accordion = dbc.Accordion(
            [
                dbc.AccordionItem(
                    [self.curve_chart_panel.layout()],
                    title="Curve Chart",
                    item_id="curve",
                ),
                dbc.AccordionItem(
                    [
                        dcc.Tabs(
                            className="custom-tabs",
                            children=[
                                dcc.Tab(
                                    label="Fixed Rate Bond",
                                    className="custom-tab",
                                    selected_className="custom-tab--selected",
                                    children=html.Div(
                                        self.fixed_rate_bond_panel.layout(),
                                        className="ag-theme-balham-dark",
                                    ),
                                ),
                                dcc.Tab(
                                    label="Floating Rate Bond",
                                    className="custom-tab",
                                    selected_className="custom-tab--selected",
                                    children=html.Div(
                                        self.floating_rate_bond_panel.layout(),
                                        className="ag-theme-balham-dark",
                                    ),
                                ),
                                dcc.Tab(
                                    label="Zeros",
                                    className="custom-tab",
                                    selected_className="custom-tab--selected",
                                    children=html.Div(
                                        self.zero_coupon_bond_panel.layout(),
                                        className="ag-theme-balham-dark",
                                    ),
                                ),
                                dcc.Tab(
                                    label="OIS/MidCurves",
                                    className="custom-tab",
                                    selected_className="custom-tab--selected",
                                    children=html.Div(
                                        self.ois_mid_curve_panel.layout(),
                                        className="ag-theme-balham-dark",
                                    ),
                                ),
                            ],
                        )
                    ],
                    title="Rates Analytics",
                    item_id="bonds",
                ),
            ],
            always_open=True,
            active_item=["bonds"],
        )

        # Full layout
        return dbc.Container(
            fluid=True,
            children=[
                # Navbar
                dbc.Navbar(
                    dbc.Container(
                        [
                            dbc.NavbarBrand("Rates", href="#", className="navbar-brand-custom"),
                            html.Div(
                                [
                                    dbc.Label(id="eval-date", className="navbar-label"),
                                    dbc.Label(id="curve-data", className="navbar-label ms-3"),
                                ],
                                className="d-flex align-items-center",
                            ),
                        ],
                        fluid=True,
                    ),
                    className="custom-navbar",
                ),

                # Error Stores
                dcc.Store(id=self.curve_chart_panel.error_prefix_id),
                dcc.Store(id=self.fixed_rate_bond_panel.error_prefix_id),
                dcc.Store(id=self.floating_rate_bond_panel.error_prefix_id),
                dcc.Store(id=self.zero_coupon_bond_panel.error_prefix_id),
                dcc.Store(id=self.ois_mid_curve_panel.error_prefix_id),

                # Error banner
                html.Div(id="error-banner"),

                # Divider
                html.Hr(className="divider"),

                # Main content
                dbc.Row(
                    className="main-content-row flex-nowrap",
                    children=[
                        # Left: Curve Market Data
                        dbc.Col(
                            html.Div(
                                [
                                    self.curve_market_data_panel.layout(),
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
                        # Right: Accordion
                        dbc.Col(
                            accordion,
                            style={"flex": "1 1 auto", "minWidth": 0},
                            className="panel-col",
                        ),
                    ],
                ),

                # Global Stores
                dcc.Store(id="portal-curves"),
                dcc.Store(id="index-fixings"),
            ],
        )


# =============================
# Dash App Initialization
# =============================
app = dash.Dash(
    __name__,
    suppress_callback_exceptions=True,
    title="Rates Analytics",
    external_stylesheets=[dbc.themes.SUPERHERO],
)

server = app.server  # Gunicorn expects this

rates_analytics = RatesAnalytics(app)
app.layout = rates_analytics.layout()


# =============================
# Callbacks
# =============================
@app.callback(
    Output("eval-date", "children"),
    Output("portal-curves", "data"),
    Output("index-fixings", "data"),
    Input("eval-date", "id"),  # dummy input to trigger on load
)
def set_quantlib_business_date(_):
    calendar = ql.TARGET()
    today = ql.Date.todaysDate()
    business_date = calendar.adjust(today, ql.ModifiedFollowing)
    business_date = calendar.advance(business_date, 0, ql.Days)
    ql.Settings.instance().evaluationDate = business_date
    business_date_py = business_date.to_date()

    with open("data/curve_setup.json", "r") as f:
        curve_data = json.load(f)

    with open("data/index_fixings.json", "r") as f:
        index_fixings_data = json.load(f)

    index_fixings = CurveUtils.transform_index_fixings(index_fixings_data)

    bond_portal_curve_dict = {}
    for curve in curve_data:
        curve_name = curve["Name"]
        transformed_curve = CurveUtils.transform_curve_components(curve)
        bond_portal_curve_dict[curve_name] = {"Curve": curve, "MarketData": transformed_curve}

    return f"Evaluation Date: {business_date_py}", bond_portal_curve_dict, index_fixings


@app.callback(
    Output("error-banner", "children"),
    Output("error-banner", "style"),
    Input(rates_analytics.curve_chart_panel.error_prefix_id, "data"),
    Input(rates_analytics.fixed_rate_bond_panel.error_prefix_id, "data"),
    Input(rates_analytics.floating_rate_bond_panel.error_prefix_id, "data"),
    Input(rates_analytics.zero_coupon_bond_panel.error_prefix_id, "data"),
    Input(rates_analytics.ois_mid_curve_panel.error_prefix_id, "data"),
)
def set_global_error(*errors):
    for err in errors:
        if err:
            return html.Span(err["message"], style={"color": "#f75464"}), {"display": "block"}
    return None, {}


# =============================
# Local Development
# =============================
if __name__ == "__main__":
    host = os.getenv("DASH_HOST", "127.0.0.1")
    port = int(os.getenv("DASH_PORT", "8050"))
    debug = os.getenv("DASH_DEBUG", "true").lower() == "true"

    app.run(host=host, port=port, debug=debug)
