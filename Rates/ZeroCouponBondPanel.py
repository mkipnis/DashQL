# Copyright (c) Mike Kipnis - DashQL

import traceback

import QuantLib as ql
import dash
from dash import Input, Output, html, dcc

from Common.Utils import ComponentUtils, CurveUtils, ConvertUtils, BondUtils
from Common.Components import SchedulePanel, TenorPanel, DataGridPanel


class ZeroCouponBondPanel:
    _callbacks_registered = set()  # class-level tracker

    def __init__(self, app: dash.Dash, prefix: str):
        self.app = app
        self.user_market_data = f"{prefix}-user-market-data"

        # Generate IDs for this instance
        self.bond_prefix = f"{prefix}-zero-coupon-bond"
        self.day_counter_id = f"{self.bond_prefix}-day_counter_id"
        self.schedule_id = f"{self.bond_prefix}-schedule"

        self.error_prefix_id = f"{self.bond_prefix}-error"

        self.tenor_panel = TenorPanel.TenorPanel(self.app, self.schedule_id)
        self.schedule_panel = SchedulePanel.SchedulePanel(self.app, self.schedule_id)

        self.settlement_days_id = f"{self.bond_prefix}-settlement-days"
        self.notional_id = f"{self.bond_prefix}-notional"

        self.discount_curve_id = f"{self.bond_prefix}-discount-curve"
        self.discount_curve_data_id = f"{self.bond_prefix}-discount-curve-data"

        defaultColDef = {
            "resizable": True,
            "minWidth": 80,
            "cellStyle": {"textAlign": "right"},
            "flex": 1,
            "headerClass": "right-header",
        }

        # AG Grid for zero-coupon bonds
        zero_coupon_columns = [
    {
        "headerName": "Maturity Date",
        "field": "Maturity Date",
        "sortable": True,
        "filter": "agTextColumnFilter",
        "cellDataType": "text",
        "width": 150,          # override
        "minWidth": 150,
        "maxWidth": 150,
        "cellStyle": {"textAlign": "center"},
        "headerClass": "left-header",
    },
    {"headerName": "Price", "field": "Price(Curve)", "cellDataType": "number"},
    {"headerName": "NPV", "field": "NPV", "cellDataType": "number"},
    {"headerName": "Yield", "field": "Yield", "cellDataType": "number"},
    {"headerName": "DV01", "field": "DV01", "cellDataType": "number"},
    {"headerName": "Convexity", "field": "Convexity", "cellDataType": "number"},
    {"headerName": "Modified Duration", "field": "Modified Duration", "cellDataType": "number"},
    {"headerName": "Macaulay Duration", "field": "Macaulay Duration", "cellDataType": "number"},
]

        self.zero_coupon_grid = DataGridPanel.DataGridPanel(
            self.app,
            default_column_defs=defaultColDef,
            column_defs=zero_coupon_columns,
            prefix=f"{self.bond_prefix}-zeros-panel"
        )

        # Register callbacks once per prefix
        if self.bond_prefix not in ZeroCouponBondPanel._callbacks_registered:
            self._register_callbacks()
            ZeroCouponBondPanel._callbacks_registered.add(self.bond_prefix)

    def layout(self) -> html.Div:
        COLUMN_WIDTH = "300px"

        daycounter_dropdown = dcc.Dropdown(
            id=self.day_counter_id,
            options=ComponentUtils.dict_to_options(ConvertUtils.DayCounterNames),
            value="ActualActual_Bond",
            clearable=False,
            searchable=False,
            className="dark-dropdown",
        )

        discount_curve_dropdown = dcc.Dropdown(
            id=self.discount_curve_id,
            clearable=False,
            searchable=False,
            className="dark-dropdown",
        )

        # ---- Zero-coupon inputs (fixed width) ----
        bond_inputs = html.Div(
            [
                ComponentUtils.horizontal_labeled_dropdown(
                    "Discount Curve", discount_curve_dropdown
                ),
                self.tenor_panel.layout(),
                dcc.Store(id=self.discount_curve_data_id),
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
                "padding": "0 12px"
            },
        )

        # ---- Results: fill remaining space ----
        bond_results = html.Div(
            [
                self.zero_coupon_grid.layout(),
            ],
            style={
                "flex": "1 1 auto",
                "minWidth": 0,  # REQUIRED for AG Grid to grow
                "display": "flex",
                "flexDirection": "column",
            },
        )

        return html.Div(
            [
                ComponentUtils.panel_label("Zero Coupon Bonds"),
                html.Hr(className="divider"),

                html.Div(
                    [
                        # ---- Schedule ----
                        html.Div(
                            ComponentUtils.panel_section(
                                "",
                                [
                                    self.schedule_panel.layout(),
                                    dcc.Store(id=self.schedule_panel.output_id),
                                ],
                                bordered=False,
                            ),
                            style={
                                "flex": "0 0 auto",
                                "whiteSpace": "nowrap",
                            },
                        ),

                        # ---- Inputs + Results ----
                        html.Div(
                            ComponentUtils.panel_section(
                                "",
                                html.Div(
                                    [bond_inputs, bond_results],
                                    style={
                                        "display": "flex",
                                        "gap": "12px",
                                        "alignItems": "stretch",
                                        "width": "100%",
                                    },
                                ),
                            ),
                            style={
                                "flex": "1 1 auto",
                                "minWidth": 0,
                                "borderLeft": "1px solid #2a2f42"
                            },
                        ),
                    ],
                    style={
                        "display": "flex",
                        "width": "100%",
                        "gap": "12px",
                    },
                ),

                # ---- Global stores ----
                dcc.Store(id=self.bond_prefix),
                #dcc.Store(id="curve_market_data"),
            ]
        )

    def _register_callbacks(self):
        """Register all Dash callbacks."""

        @self.app.callback(
            Output(self.discount_curve_id, "options"),
            Output(self.discount_curve_id, "value"),
            Input("portal-curves", "data"),
        )
        def update_curve_options(user_market_data):
            if not user_market_data:
                return [], None
            options = [{"label": name, "value": name} for name in user_market_data.keys()]
            return options, options[0]["value"]

        @self.app.callback(
            Output(self.bond_prefix, "data"),
            Input(self.settlement_days_id, "value"),
            Input(self.notional_id, "value"),
        )
        def update_bond_data(settlement_days, notional):
            if settlement_days is None or notional is None:
                return dash.no_update
            return {"SettlementDays": settlement_days, "FaceAmount": notional}

        @self.app.callback(
            Output(self.zero_coupon_grid.row_data_id, "data"),
            Output(self.error_prefix_id, "data"),
            Input(self.discount_curve_data_id, "data"),
            Input(self.schedule_panel.output_id, "data"),
            Input(self.bond_prefix, "data"),
            Input(self.tenor_panel.tenor_id, "value"),
        )
        def reprice_zero_coupon(discount_curve_data, schedule_data, bond_data, _):
            if discount_curve_data is None or schedule_data is None or bond_data is None:
                return [], None

            try:
                market_data = discount_curve_data["MarketData"]
                rate_helpers = CurveUtils.create_rate_helpers(market_data)
                curve, discount_curve = CurveUtils.bootstrap(rate_helpers)
                day_counter = discount_curve_data["Curve"]["DayCounter"]

                zeros = BondUtils.get_zeros(schedule_data, bond_data)
                data_out = []
                for bond in zeros:
                    engine = ql.DiscountingBondEngine(discount_curve)
                    bond.setPricingEngine(engine)
                    if bond.isExpired() or bond.settlementDate() > bond.maturityDate():
                        continue
                    pricing_results = BondUtils.get_pricing_results(
                        curve, discount_curve, bond, bond.cleanPrice(),
                        day_counter, schedule_data["Compounding"], schedule_data["Frequency"]
                    )
                    data_out.append(pricing_results)

                return data_out, None
            except Exception as e:
                return dash.no_update, {
                    "message": str(e),
                    "traceback": traceback.format_exc(),
                }

        @self.app.callback(
            Output(self.discount_curve_data_id, "data"),
            Input(self.discount_curve_id, "value"),
            Input(self.user_market_data, "data"),
        )
        def update_discount_curve_data(selected_curve, market_data):
            if selected_curve and market_data:
                return market_data[selected_curve]
            return dash.no_update
