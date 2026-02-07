# Copyright (c) Mike Kipnis - DashQL

import traceback

import dash
from dash import Input, Output, html, dcc, State, ctx
import QuantLib as ql

from Common.Utils.Constants import PricingConstants, RoundingConstants
from Common.Utils import (
    ComponentUtils,
    CurveUtils,
    ConvertUtils,
    BondUtils
)
from Common.Components import (
    SchedulePanel,
    TenorPanel,
    DataGridPanel,
)


class FixedRateBondPanel:
    _callbacks_registered = set()

    # =========================
    # Construction
    # =========================
    def __init__(self, app: dash.Dash, prefix: str = "bond", user_market_data_id: str = ""):
        self.app = app
        self.prefix = prefix

        # ---- IDs ----
        self.user_market_data_id = user_market_data_id
        self.bond_prefix = f"{prefix}-fixed-rate-bond"

        self.error_prefix_id = f"{self.bond_prefix}-error"

        self.output_id = f"{self.bond_prefix}-output"
        self.day_counter_id = f"{self.bond_prefix}-day-counter-id"
        self.discount_curve_id = f"{self.bond_prefix}-discount-curve"
        self.discount_curve_data_id = f"{self.bond_prefix}-discount-curve-data"

        self.coupon_id = f"{self.bond_prefix}-coupon"
        self.price_id = f"{self.bond_prefix}-price"
        self.yield_id = f"{self.bond_prefix}-yield"
        self.settlement_days_id = f"{self.bond_prefix}-settlement-days"
        self.notional_id = f"{self.bond_prefix}-notional"
        self.pricing_results_id = f"{self.bond_prefix}-pricing-results"

        # ---- Panels ----
        self.schedule_panel = SchedulePanel.SchedulePanel(app, self.bond_prefix)
        self.tenor_panel = TenorPanel.TenorPanel(app, self.schedule_panel.prefix)

        self.cashflow_data_grid_panel = DataGridPanel.DataGridPanel(
            app,
            prefix=f"{self.bond_prefix}-cashflow-panel",
            column_defs=[
                {"headerName": "Date", "field": "business_date", "flex": 2},
                {"headerName": "Nominal", "field": "nominal", "flex": 2},
                {"headerName": "Rate", "field": "rate"},
                {"headerName": "Amount", "field": "amount"},
            ],
        )

        self.pricing_results_data_grid_panel = DataGridPanel.DataGridPanel(
            app,
            prefix=f"{self.bond_prefix}-pricing-results-panel",
            column_defs=[
                {"headerName": "Param", "field": "key"},
                {"headerName": "Result", "field": "result",
                 "cellDataType": "text","cellStyle": {"textAlign": "right"},
                 },
            ],
            dashGridOptions={"headerHeight": 0},
        )

        if self.bond_prefix not in self._callbacks_registered:
            self._register_callbacks()
            self._callbacks_registered.add(self.bond_prefix)

    # =========================
    # Layout
    # =========================
    def layout(self) -> html.Div:
        COLUMN_WIDTH = "300px"

        daycounter_dropdown = dcc.Dropdown(
            id=self.day_counter_id,
            options=ComponentUtils.dict_to_options(ConvertUtils.DayCounterNames),
            value="ActualActual_Bond",
            clearable=False,
        )

        discount_curve_dropdown = dcc.Dropdown(
            id=self.discount_curve_id,
            clearable=False,
        )

        # ---- Bond inputs (fixed width) ----
        bond_inputs = html.Div(
            [
                ComponentUtils.horizontal_labeled_dropdown(
                    "Discount Curve", discount_curve_dropdown
                ),
                self.tenor_panel.layout(),
                dcc.Store(id=self.discount_curve_data_id),
                ComponentUtils.labeled_number_input("Coupon", self.coupon_id, step=PricingConstants.COUPON_TICK_SIZE),
                ComponentUtils.labeled_number_input("Price", self.price_id, step=PricingConstants.PRICE_TICK_SIZE),
                ComponentUtils.labeled_number_input("Yield", self.yield_id, step=0.001),
                ComponentUtils.labeled_number_input(
                    "Settlement Days", self.settlement_days_id, value=1, step=1
                ),
                ComponentUtils.labeled_number_input(
                    "Notional", self.notional_id, value=10000, step=1000
                ),
                ComponentUtils.horizontal_labeled_dropdown(
                    "Payment DayCounter", daycounter_dropdown
                ),
            ],
            style={
                "flex": f"0 0 {COLUMN_WIDTH}",
                "width": COLUMN_WIDTH,
                "display": "flex",
                "flexDirection": "column",
                "gap": "8px",
            },
        )

        # ---- Pricing results (SAME width as inputs) ----
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

        return html.Div(
            [
                ComponentUtils.panel_label("Fixed Rate Bond"),
                html.Hr(className="divider"),
                html.Div(
                    [
                        # ---- Schedule ----
                        html.Div(
                            ComponentUtils.panel_section(
                                "",
                                [self.schedule_panel.layout()],
                                bordered=False,
                            ),
                            style={
                                "flex": "0 0 auto",
                                "whiteSpace": "nowrap",
                            },
                        ),

                        # ---- Bond (inputs + results) ----
                        html.Div(
                            ComponentUtils.panel_section(
                                "",
                                html.Div(
                                    [bond_inputs, bond_results],
                                    style={
                                        "display": "flex",
                                        "gap": "12px",
                                        "alignItems": "stretch",
                                    },
                                ),
                            ),
                            style={
                                "flex": "0 0 auto",
                                "borderLeft": "1px solid #2a2f42",  # vertical divider on the left
                            },
                        ),

                        # ---- Cashflows (fill remaining space) ----
                        html.Div(
                            ComponentUtils.panel_section(
                                "",
                                [self.cashflow_data_grid_panel.layout()],
                            ),
                            style={
                                "flex": "1 1 auto",
                                "minWidth": 0,
                                "borderLeft": "1px solid #2a2f42",  # vertical divider on the left
                            },
                        ),
                    ],
                    style={"display": "flex", "width": "100%"},
                ),
                dcc.Store(id=self.bond_prefix),
                dcc.Store(id=self.output_id),
                dcc.Store(id="curve_market_data"),
            ]
        )

    # =========================
    # Helpers
    # =========================
    @staticmethod
    def _build_curve(curve_market_data):
        market_data = curve_market_data["MarketData"]
        helpers = CurveUtils.create_rate_helpers(market_data)
        return CurveUtils.bootstrap(helpers)

    @staticmethod
    def _bond_yield(bond, price, day_counter, comp, freq):
        clean_price = ql.BondPrice(price, ql.BondPrice.Clean)
        return bond.bondYield(
            clean_price,
            ConvertUtils.day_counter_from_string(day_counter),
            ConvertUtils.enum_from_string(comp),
            ConvertUtils.enum_from_string(freq),
        )

    # =========================
    # Callbacks
    # =========================
    def _register_callbacks(self):
        @self.app.callback(
            Output(self.discount_curve_id, "options"),
            Output(self.discount_curve_id, "value"),
            Input("portal-curves", "data"),
        )
        def _update_curve_dropdown(user_market_data):
            if not user_market_data:
                return [], None

            options = [{"label": k, "value": k} for k in user_market_data.keys()]
            return options, options[0]["value"]

        @self.app.callback(
            Output(self.coupon_id, "value"),
            Input(self.discount_curve_data_id, "data"),
            Input(self.schedule_panel.output_id, "data"),
            Input(self.tenor_panel.tenor_id, "value"),
            State(self.coupon_id, "value"),
        )
        def _update_coupon(curve_data, schedule_data, tenor, coupon):
            if not curve_data or not schedule_data:
                return dash.no_update

            if coupon is not None and ctx.triggered_id != self.tenor_panel.tenor_id:
                return coupon

            curve, _ = self._build_curve(curve_data)
            maturity = ql.DateParser.parseISO(schedule_data["maturity_date"])
            zero = curve.zeroRate(
                maturity,
                ql.ActualActual(ql.ActualActual.ISDA),
                ql.Compounded,
                ql.Semiannual,
            )
            return ComponentUtils.round_to_rational_fraction(PricingConstants.COUPON_TICK_SIZE, zero.rate() * PricingConstants.RATE_FACTOR)

        @self.app.callback(
            Output(self.bond_prefix, "data"),
            Input(self.coupon_id, "value"),
            Input(self.day_counter_id, "value"),
            Input(self.settlement_days_id, "value"),
            Input(self.notional_id, "value"),
        )
        def _build_bond(coupon, day_counter, settlement_days, notional):
            if None in (coupon, day_counter, settlement_days, notional):
                return dash.no_update

            return {
                "Coupon": [coupon / PricingConstants.RATE_FACTOR],
                "SettlementDays": settlement_days,
                "DayCounter": day_counter,
                "FaceAmount": notional,
            }

        @self.app.callback(
            Output(self.price_id, "value"),
            Output(self.yield_id, "value"),
            Output(self.cashflow_data_grid_panel.row_data_id, "data"),
            Output(self.pricing_results_id, "data"),
            Output(self.error_prefix_id, "data"),
            Input(self.discount_curve_data_id, "data"),
            Input(self.price_id, "value"),
            Input(self.yield_id, "value"),
            Input(self.schedule_panel.output_id, "data"),
            Input(self.bond_prefix, "data"),
            Input(self.tenor_panel.tenor_id, "value"),
        )
        def _reprice(curve_data, price, yield_in, schedule, bond_data, _):
            """
            Reprice the fixed rate bond, update price, yield, cashflows, and pricing results.

            This function handles:
            - Initial load: sets default Price=100 and computes Yield.
            - User changes to Price or Yield: updates the other accordingly.
            """

            # --- If any required data is missing, do nothing ---
            if not curve_data or not schedule or not bond_data:
                return (dash.no_update,) * 5

            try:
                # --- Build bond and curves ---
                bond = BondUtils.get_fixed_rate_bond(schedule, bond_data)
                curve, discount = self._build_curve(curve_data)

                comp = schedule["Compounding"]
                freq = schedule["Frequency"]
                dc = bond_data["DayCounter"]

                trigger = ctx.triggered_id

                # --- Determine price and yield ---
                if trigger is None:
                    # Initial load: set price to 100 and calculate yield
                    price = PricingConstants.PAR
                    yield_out = round(
                        self._bond_yield(bond, price, dc, comp, freq) * PricingConstants.RATE_FACTOR, PricingConstants.ROUND_RATE
                    )
                elif trigger == self.price_id:
                    # User updated price: recalc yield
                    price = price or PricingConstants.PAR
                    yield_out = round(
                        self._bond_yield(bond, price, dc, comp, freq) * PricingConstants.RATE_FACTOR, RoundingConstants.ROUND_RATE
                    )
                elif trigger == self.yield_id:
                    # User updated yield: recalc price
                    clean_price = bond.cleanPrice(
                        yield_in / PricingConstants.RATE_FACTOR,
                        ConvertUtils.day_counter_from_string(dc),
                        ConvertUtils.enum_from_string(comp),
                        ConvertUtils.enum_from_string(freq),
                    )
                    price = ComponentUtils.round_to_rational_fraction(PricingConstants.PRICE_TICK_SIZE, clean_price)
                    yield_out = dash.no_update
                else:
                    # Any other trigger (schedule change, bond setup, tenor): keep price, recalc yield
                    price = price or PricingConstants.PAR
                    yield_out = round(
                        self._bond_yield(bond, price, dc, comp, freq) * PricingConstants.RATE_FACTOR, RoundingConstants.ROUND_RATE
                    )

                # --- Compute pricing results and cashflows ---
                pricing = BondUtils.get_pricing_results(
                    curve, discount, bond, price, dc, comp, freq
                )
                cashflows = BondUtils.get_cashflows(bond)

                return price, yield_out, cashflows, pricing, None

            except Exception as e:
                return (dash.no_update,) * 4, {
                    "message": str(e),
                    "traceback": traceback.format_exc(),
                }

        @self.app.callback(
            Output(self.pricing_results_data_grid_panel.row_data_id, "data"),
            Input(self.pricing_results_id, "data"),
        )
        def _format_pricing_results(results):
            if not results:
                return []
            return [{"key": k, "result": v} for k, v in results.items()]

        @self.app.callback(
            Output(self.discount_curve_data_id, "data"),
            Input(self.discount_curve_id, "value"),
            Input(self.user_market_data_id, "data"),
        )
        def _select_curve(name, curves):
            return curves.get(name) if name and curves else dash.no_update
