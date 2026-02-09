# Copyright (c) Mike Kipnis - DashQL

import traceback

import dash
import dash_ag_grid as dag
from dash import Input, Output, html, dcc, State, ctx
import dash_bootstrap_components as dbc
import QuantLib as ql

from Common.Components import DataGridPanel, SchedulePanel, TenorPanel
from Common.Utils import ComponentUtils, CurveUtils, ConvertUtils, BondUtils
from Common.Utils.Constants import PricingConstants, RoundingConstants


class FloatingRateBondPanel:
    _callbacks_registered = set()  # class-level tracker

    def __init__(self, app: dash.Dash, prefix: str):
        self.app = app
        self.user_market_data = f"{prefix}-user-market-data"

        self.bond_prefix = f"{prefix}-floating-rate-bond"
        self.output_id = f"{self.bond_prefix}-output"
        self.day_counter_id = f"{self.bond_prefix}-day-counter-id"

        self.error_prefix_id = f"{self.bond_prefix}-error"

        # Panels
        self.schedule_panel = SchedulePanel.SchedulePanel(self.app, self.bond_prefix)
        self.tenor_panel = TenorPanel.TenorPanel(self.app, self.schedule_panel.prefix)

        # Inputs
        self.spread_id = f"{self.bond_prefix}-spread"
        self.payment_lag_id = f"{self.bond_prefix}-payment-lag"
        self.price_id = f"{self.bond_prefix}-price"
        self.yield_id = f"{self.bond_prefix}-yield"
        self.settlement_days_id = f"{self.bond_prefix}-settlement-days"
        self.notional_id = f"{self.bond_prefix}-notional"

        # Cashflows grid
        cashflow_columns = [
            {"headerName": "Date", "field": "business_date", "sortable": True, "flex": 2, "filter": "agTextColumnFilter"},
            {"headerName": "Nominal", "field": "nominal", "sortable": True, "flex": 2},
            {"headerName": "Rate", "field": "rate"},
            {"headerName": "Amount", "field": "amount"}
        ]
        self.cashflow_data_grid_panel = DataGridPanel.DataGridPanel(
            self.app,
            prefix=f"{self.bond_prefix}-cashflow-panel",
            column_defs=cashflow_columns
        )

        # Pricing results grid
        self.pricing_results_data_grid_panel = DataGridPanel.DataGridPanel(
            self.app,
            prefix=f"{self.bond_prefix}-pricing-results-panel",
            column_defs=[
                {"headerName": "Param", "field": "key"},
                {"headerName": "Result", "field": "result",
                 "cellDataType": "text", "cellStyle": {"textAlign": "right"},
                 },
            ],
            dashGridOptions={"headerHeight": 0},
        )

        # Curves
        self.discount_curve_id = f"{self.bond_prefix}-discount-curve"
        self.discount_curve_data_id = f"{self.bond_prefix}-discount-curve-data"
        self.forecast_curve_id = f"{self.bond_prefix}-forecast-curve"
        self.forecast_curve_data_id = f"{self.bond_prefix}-forecast-curve-data"

        # Stores
        self.pricing_results_id = f"{self.bond_prefix}-pricing-results"

        if self.bond_prefix not in FloatingRateBondPanel._callbacks_registered:
            self._register_callbacks()
            FloatingRateBondPanel._callbacks_registered.add(self.bond_prefix)

    def layout(self) -> html.Div:
        COLUMN_WIDTH = "300px"

        discount_dropdown = dcc.Dropdown(id=self.discount_curve_id,
                                         clearable=False,
                                         searchable=False,
                                         className="dark-dropdown",
                                         )
        forecast_dropdown = dcc.Dropdown(id=self.forecast_curve_id,
                                         clearable=False,
                                         searchable=False,
                                         className="dark-dropdown",
                                         )

        # ---- Bond inputs (fixed width) ----
        bond_inputs = html.Div(
            [
                dcc.Store(id=self.forecast_curve_data_id),
                ComponentUtils.horizontal_labeled_dropdown("Forecast Curve", forecast_dropdown),
                dcc.Store(id=self.discount_curve_data_id),
                ComponentUtils.horizontal_labeled_dropdown("Discount Curve", discount_dropdown),
                self.tenor_panel.layout(),
                ComponentUtils.labeled_number_input("Spread(BPS)", self.spread_id, step=1),
                ComponentUtils.labeled_number_input("Payment Lag", self.payment_lag_id, value=2, step=1),
                ComponentUtils.labeled_number_input("Price", self.price_id, step=PricingConstants.PRICE_TICK_SIZE),
                ComponentUtils.labeled_number_input("Yield", self.yield_id, step=0.001),
                ComponentUtils.labeled_number_input("Settlement Days", self.settlement_days_id, value=1, step=1),
                ComponentUtils.labeled_number_input("Notional", self.notional_id, value=10000, step=1000),
            ],
            style={
                "flex": f"0 0 {COLUMN_WIDTH}",
                "width": COLUMN_WIDTH,
                "display": "flex",
                "flexDirection": "column",
                "gap": "8px",
                "padding": "0 12px"
            },
        )

        # ---- Pricing results (same width as inputs) ----
        bond_results = html.Div(
            [
                self.pricing_results_data_grid_panel.layout(),
                dcc.Store(id=self.pricing_results_id),
            ],
            style={
                "flex": f"0 0 {COLUMN_WIDTH}",
                "width": COLUMN_WIDTH,
                "minWidth": 0,  # required for AG Grid
            },
        )

        # ---- Floating Rate Bond panel (inputs + results) ----
        bond_panel = html.Div(
            [bond_inputs, bond_results],
            style={"display": "flex", "gap": "12px", "alignItems": "stretch", "borderLeft": "1px solid #2a2f42",
                   "padding": "0 12px"},

        )

        # ---- Schedule panel ----
        schedule_panel_section = html.Div(
            ComponentUtils.panel_section("", [self.schedule_panel.layout()], bordered=False),
            style={"flex": "0 0 auto", "whiteSpace": "nowrap"},
        )

        # ---- Cashflows panel (fill remaining space) ----
        cashflows_panel_section = html.Div(
            ComponentUtils.panel_section("", [self.cashflow_data_grid_panel.layout()]),
            style={"flex": "1 1 auto", "minWidth": 0, "borderLeft": "1px solid #2a2f42"},
        )

        return html.Div(
            [
                ComponentUtils.panel_label("Floating Rate Bond"),
                html.Hr(className="divider"),
                html.Div(
                    [
                        schedule_panel_section,
                        html.Div(
                            ComponentUtils.panel_section("", bond_panel),
                            style={"flex": "0 0 auto"},
                        ),
                        cashflows_panel_section,
                    ],
                    style={"display": "flex", "width": "100%"},
                ),
                dcc.Store(id=self.bond_prefix),
                dcc.Store(id=self.output_id),
                #dcc.Store(id="curve_market_data"),
            ]
        )

    # =========================
    # Callbacks
    # =========================
    def _register_callbacks(self):
        # --- Populate curve dropdowns ---
        @self.app.callback(
            Output(self.discount_curve_id, "options"),
            Output(self.discount_curve_id, "value"),
            Output(self.forecast_curve_id, "options"),
            Output(self.forecast_curve_id, "value"),
            Input("portal-curves", "data"),
        )
        def on_curve_data_change(user_market_data):
            if not user_market_data:
                return [], None, [], None

            discount_curves = []
            forecast_curves = []

            for name, curve in user_market_data.items():
                discount_curves.append({"label": name, "value": name})
                if isinstance(curve.get("Curve"), dict) and "Index" in curve["Curve"]:
                    forecast_curves.append({"label": name, "value": name})

            discount_value = discount_curves[0]["value"] if discount_curves else None
            forecast_value = forecast_curves[0]["value"] if forecast_curves else None
            return discount_curves, discount_value, forecast_curves, forecast_value

        # --- Spread auto-fill ---
        @self.app.callback(
            Output(self.spread_id, "value"),
            Input(self.discount_curve_data_id, "data"),
            Input(self.schedule_panel.output_id, "data"),
            Input(self.tenor_panel.tenor_id, "value"),
        )
        def on_term_structure_market_data(curve_data, schedule_data, _):
            if curve_data is None or schedule_data is None:
                return dash.no_update
            return 0.0

        # --- Bond setup ---
        @self.app.callback(
            Output(self.bond_prefix, "data"),
            Input(self.spread_id, "value"),
            Input(self.settlement_days_id, "value"),
            Input(self.notional_id, "value"),
            Input(self.payment_lag_id, "value"),
        )
        def on_bond_setup(spread, settlement_days, notional, payment_lag):
            if None in (spread, settlement_days, notional, payment_lag):
                return dash.no_update
            overnight_leg = {"nominals": [notional], "spreads": [spread/PricingConstants.BPS_FACTOR], "paymentLag": payment_lag}
            floating_rate_bond = {"SettlementDays": settlement_days}
            return {"overnight_leg": overnight_leg, "floating_rate_bond": floating_rate_bond}

        # --- Pricing & yield ---
        @self.app.callback(
            Output(self.price_id, "value"),
            Output(self.yield_id, "value"),
            Output(self.cashflow_data_grid_panel.row_data_id, "data"),
            Output(self.pricing_results_id, "data"),
            Output(self.error_prefix_id, "data"),
            Input(self.forecast_curve_data_id, "data"),
            Input(self.discount_curve_data_id, "data"),
            Input("index-fixings", "data"),
            Input(self.price_id, "value"),
            Input(self.yield_id, "value"),
            Input(self.spread_id, "value"),
            Input(self.schedule_panel.output_id, "data"),
            Input(self.bond_prefix, "data"),
            Input(self.tenor_panel.tenor_id, "value"),
        )
        def on_reprice(forecast_curve_data, discount_curve_data, index_fixings, price, yield_in, spread, schedule, bond_data, _):
            if not (forecast_curve_data and discount_curve_data and schedule and bond_data):
                return (dash.no_update,) * 5

            trigger = ctx.triggered_id
            overnight_leg = bond_data["overnight_leg"]
            floating_rate_bond = bond_data["floating_rate_bond"]

            try:
                if trigger == self.spread_id:
                    overnight_leg["spreads"] = [spread/PricingConstants.BPS_FACTOR]
                    bond_data["overnight_leg"] = overnight_leg

                bond = BondUtils.get_floating_rate_bond(forecast_curve_data, index_fixings, schedule, overnight_leg, floating_rate_bond)
                day_counter = forecast_curve_data["Curve"]["DayCounter"]

                curve, discount = CurveUtils.bootstrap(CurveUtils.create_rate_helpers(discount_curve_data["MarketData"]))

                if trigger in [self.schedule_panel.output_id, self.tenor_panel.tenor_id,
                           "index-fixings",self.forecast_curve_data_id,
                           self.discount_curve_data_id, self.bond_prefix]:
                    clean_price = ql.BondPrice(PricingConstants.PAR, ql.BondPrice.Clean)
                    yield_out = bond.bondYield(clean_price, ConvertUtils.day_counter_from_string(day_counter),
                                           ConvertUtils.enum_from_string(schedule["Compounding"]),
                                           ConvertUtils.enum_from_string(schedule["Frequency"]))
                    pricing = BondUtils.get_pricing_results(curve, discount, bond, clean_price.amount(),
                                                       day_counter, schedule["Compounding"], schedule["Frequency"])
                    return PricingConstants.PAR, round(yield_out * PricingConstants.RATE_FACTOR, RoundingConstants.ROUND_RATE), BondUtils.get_cashflows(bond), pricing, None

                if trigger == self.price_id:
                    clean_price = ql.BondPrice(price, ql.BondPrice.Clean)
                    yield_out = bond.bondYield(clean_price, ConvertUtils.day_counter_from_string(day_counter),
                                           ConvertUtils.enum_from_string(schedule["Compounding"]),
                                           ConvertUtils.enum_from_string(schedule["Frequency"]))
                    pricing = BondUtils.get_pricing_results(curve, discount, bond, clean_price.amount(),
                                                       day_counter, schedule["Compounding"], schedule["Frequency"])
                    return (dash.no_update, round(yield_out * PricingConstants.RATE_FACTOR, RoundingConstants.ROUND_RATE),
                            BondUtils.get_cashflows(bond), pricing, None)

                if trigger == self.yield_id:
                    clean_price = bond.cleanPrice(yield_in /  PricingConstants.RATE_FACTOR, ConvertUtils.day_counter_from_string(day_counter),
                                              ConvertUtils.enum_from_string(schedule["Compounding"]),
                                              ConvertUtils.enum_from_string(schedule["Frequency"]))
                    pricing = BondUtils.get_pricing_results(curve, discount, bond, clean_price,
                                                       day_counter, schedule["Compounding"], schedule["Frequency"])
                    return ComponentUtils.round_to_rational_fraction(PricingConstants.PRICE_TICK_SIZE, clean_price), dash.no_update, BondUtils.get_cashflows(bond), pricing, None

                # Spread trigger just recalculates pricing
                if trigger == self.spread_id:
                    clean_price = ql.BondPrice(price if price else PricingConstants.PAR, ql.BondPrice.Clean)
                    yield_out = bond.bondYield(clean_price, ConvertUtils.day_counter_from_string(day_counter),
                                           ConvertUtils.enum_from_string(schedule["Compounding"]),
                                           ConvertUtils.enum_from_string(schedule["Frequency"]))
                    pricing = BondUtils.get_pricing_results(curve, discount, bond, clean_price.amount(),
                                                       day_counter, schedule["Compounding"], schedule["Frequency"])
                    return dash.no_update, round(yield_out * PricingConstants.RATE_FACTOR, RoundingConstants.ROUND_RATE), BondUtils.get_cashflows(bond), pricing, None

                return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

            except Exception as e:
                return (dash.no_update,) * 4, {
                    "message": str(e),
                    "traceback": traceback.format_exc(),
                }

        # --- Pricing results grid ---
        @self.app.callback(
            Output(self.pricing_results_data_grid_panel.row_data_id, "data"),
            Input(self.pricing_results_id, "data"),
        )
        def on_pricing_results(results):
            if not results:
                return []
            return [{"key": k, "result": v} for k, v in results.items()]

        # --- Curve data stores ---
        @self.app.callback(
            Output(self.discount_curve_data_id, "data"),
            Input(self.discount_curve_id, "value"),
            Input(self.user_market_data, "data"),
        )
        def update_discount_curve(value, curves):
            if value and curves:
                return curves[value]
            return dash.no_update

        @self.app.callback(
            Output(self.forecast_curve_data_id, "data"),
            Input(self.forecast_curve_id, "value"),
            Input(self.user_market_data, "data"),
        )
        def update_forecast_curve(value, curves):
            if value and curves:
                return curves[value]
            return dash.no_update
