import json
import inspect
from datetime import datetime

import QuantLib as ql
import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output


import Common.Components.CurveChartPanel
from Common.Components import CurveMarketDataPanel
from Common.Utils import CurveUtils
from Rates import FixedRateBondPanel
from Rates import FloatingRateBondPanel
from Rates import ZeroCouponBondPanel
from Rates import CurvePanel
from Rates import OISMidCurvePanel


class RatesAnalytics:

    def __init__(self, app: dash.Dash):
        self.app = app
        self.prefix = 'rates-analytics'

        self.curve_market_data_panel = CurveMarketDataPanel.CurveMarketDataPanel(
                                self.app, prefix=self.prefix
                            )

        self.curve_chart_panel = CurvePanel.CurvePanel(app, curve_market_data_panel=self.curve_market_data_panel, prefix=self.prefix)
        self.fixed_rate_bond_panel = FixedRateBondPanel.FixedRateBondPanel(app, prefix=self.prefix, user_market_data_id=self.curve_market_data_panel.user_market_data_id)
        self.floating_rate_bond_panel = FloatingRateBondPanel.FloatingRateBondPanel(app, prefix=self.prefix)
        self.zero_coupon_bond_panel = ZeroCouponBondPanel.ZeroCouponBondPanel(app, prefix=self.prefix)
        self.ois_mid_curve_panel = OISMidCurvePanel.OISMidCurvePanel(app, prefix=self.prefix, user_market_data_id=self.curve_market_data_panel.user_market_data_id)

    def layout(self):
        accordion = html.Div(
            dbc.Accordion(
                [

                    dbc.AccordionItem(
                        [
                            self.curve_chart_panel.layout(),
                        ],
                        title="Curve Chart",
                        item_id="curve",
                    ),
                    dbc.AccordionItem(
                        [
                            dcc.Tabs(
                                className="custom-tabs",  # apply the CSS class for tabs
                                children=[
                                    dcc.Tab(
                                        label='Fixed Rate Bond',
                                        className="custom-tab",
                                        selected_className="custom-tab--selected",
                                        children=[
                                            html.Div(
                                                self.fixed_rate_bond_panel.layout(),
                                                className="ag-theme-balham-dark"
                                            )
                                        ]
                                    ),
                                    dcc.Tab(
                                        label='Floating Rate Bond',
                                        className="custom-tab",
                                        selected_className="custom-tab--selected",
                                        children=[
                                            html.Div(
                                                self.floating_rate_bond_panel.layout(),
                                                className="ag-theme-balham-dark"
                                            )
                                        ]
                                    ),
                                    dcc.Tab(
                                        label='Zeros',
                                        className="custom-tab",
                                        selected_className="custom-tab--selected",
                                        children=[
                                            html.Div(
                                                self.zero_coupon_bond_panel.layout(),
                                                className="ag-theme-balham-dark"
                                            )
                                        ]
                                    ),
                                    dcc.Tab(
                                        label='OIS/MidCurve',
                                        className="custom-tab",
                                        selected_className="custom-tab--selected",
                                        children=[
                                            html.Div(
                                                self.ois_mid_curve_panel.layout(),
                                                className="ag-theme-balham-dark"
                                            )
                                        ]
                                    ),
                                ]
                            )
                        ],
                        title="Rates Analytics",
                        item_id="bonds",
                    )
                ], always_open=True,active_item=["bonds"],
            )
        )

        return dbc.Container(
            fluid=True,
            children=[
                # ===== Navbar =====
                dbc.Navbar(
                    dbc.Container(
                        [
                            dbc.NavbarBrand(
                                "Rates",
                                href="#",
                                className="navbar-brand-custom",
                            ),
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

                # ===== Divider =====
                html.Hr(className="divider"),

                # ===== Main content =====
                dbc.Row(
                    className="main-content-row flex-nowrap",
                    children=[
                        # ---- Left: Curve Market Data ----
                        dbc.Col(
                            self.curve_market_data_panel.layout(),
                            width="auto",
                            style={
                                "minWidth": "280px",
                                "maxWidth": "280px",
                            },
                            className="panel-col",
                        ),

                        # ---- Right: Accordion ----
                        dbc.Col(
                            accordion,
                            style={
                                "flex": "1 1 auto",
                                "minWidth": 0,
                            },
                            className="panel-col",
                        ),
                    ],
                ),

                # ===== Stores =====
                dcc.Store(id="portal-curves"),
                dcc.Store(id="index-fixings"),
            ],
        )

# -----------------------------
# Main
# -----------------------------

if __name__ == '__main__':

    #symbols = scan(ql)

    app = dash.Dash(
        __name__,
        suppress_callback_exceptions=True,
        title="Rates",
        external_stylesheets=[dbc.themes.SUPERHERO]
    )

    rates_analytics = RatesAnalytics(app)
    app.layout = rates_analytics.layout()

    # Callback to compute QuantLib business date on startup
    @app.callback(
        Output("eval-date", "children"),
        Output("portal-curves", "data"),
        Output("index-fixings", "data"),
        Input("eval-date", "id")  # dummy input to trigger on load
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
            curve_name = curve['Name']
            transformed_curve = CurveUtils.transform_curve_components(curve)
            bond_portal_curve_dict[curve_name] = {
                'Curve': curve,
                'MarketData': transformed_curve
            }

        return f'Evaluation Date: {business_date_py}', bond_portal_curve_dict, index_fixings

    app.run(debug=True)
