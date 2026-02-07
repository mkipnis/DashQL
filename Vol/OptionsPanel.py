# Copyright (c) Mike Kipnis - DashQL

import traceback
import QuantLib
import dash
import dash_ag_grid as dag
from dash import Input, Output, html, dcc

from Common.Utils.ConvertUtils import to_ql_date
from Common.Utils.VolUtils import price_european_option


class OptionsPanel:
    def __init__(self, app: dash.Dash, prefix: str, user_market_data_id: str = ""):
        self.app = app
        self.prefix = f"{prefix}-options-panel-id"
        self.user_market_data_id = user_market_data_id

        self.error_prefix_id = f"{self.prefix}-error"

        CALL_CLASS_RULES = {
            "otm": "params.data && params.data.spot != null && Number(params.data.strike) >= Number(params.data.spot)",
            "itm": "params.data && params.data.spot != null && Number(params.data.strike) < Number(params.data.spot)",
        }

        PUT_CLASS_RULES = {
            "otm": "params.data && params.data.spot != null && Number(params.data.strike) <= Number(params.data.spot)",
            "itm": "params.data && params.data.spot != null && Number(params.data.strike) > Number(params.data.spot)",
        }

        self.options_panel_grid = dag.AgGrid(
            id="options-panel-grid",
            columnDefs=[
                {
                    "headerName": "Calls",
                    "children": [
                        {"field": "call_rho", "headerName": "Rho", "cellClassRules": CALL_CLASS_RULES},
                        {"field": "call_theta", "headerName": "Theta", "cellClassRules": CALL_CLASS_RULES},
                        {"field": "call_vega", "headerName": "Vega", "cellClassRules": CALL_CLASS_RULES},
                        {"field": "call_gamma", "headerName": "Gamma", "cellClassRules": CALL_CLASS_RULES},
                        {"field": "call_delta", "headerName": "Delta", "cellClassRules": CALL_CLASS_RULES},
                        {"field": "call_npv", "headerName": "Price", "cellClassRules": CALL_CLASS_RULES, "cellStyle":{"color":"#FFA500"}},
                        {
                            "field": "call_vol",
                            "headerName": "Vol",
                            "cellStyle": {
                                "textAlign": "right",
                                "color": "#4bc0c0",
                            },
                        },
                    ],
                },
                {
                    "headerName": "Option",
                    "children": [
                        {"field": "spot", "headerName": "Spot", "cellStyle": {"textAlign": "right"}},
                        {
                            "field": "strike",
                            "headerName": "Strike",
                            "cellStyle": {"textAlign": "right", "color": "#70b676"},
                            "sort": "asc",  # initial sort
                        },
                        {"field": "expirationDate", "headerName": "Expiration", "cellStyle": {"textAlign": "right"}},

                    ],
                },
                {
                    "headerName": "Puts",
                    "children": [
                        {
                            "field": "put_vol",
                            "headerName": "Vol",
                            "cellStyle": {
                                "textAlign": "right",
                                "color": "#ff6284",
                            },
                        },
                        {"field": "put_npv", "headerName": "Price", "cellClassRules": PUT_CLASS_RULES, "cellStyle":{"color":"#FFA500"}},
                        {"field": "put_delta", "headerName": "Delta", "cellClassRules": PUT_CLASS_RULES},
                        {"field": "put_gamma", "headerName": "Gamma", "cellClassRules": PUT_CLASS_RULES},
                        {"field": "put_vega", "headerName": "Vega", "cellClassRules": PUT_CLASS_RULES},
                        {"field": "put_theta", "headerName": "Theta", "cellClassRules": PUT_CLASS_RULES},
                        {"field": "put_rho", "headerName": "Rho", "cellClassRules": PUT_CLASS_RULES},
                    ],
                },
            ],
            rowData=[],
            getRowId="params.data.strike",  # ✅ REQUIRED for rowTransaction
            defaultColDef={"flex": 1, "minWidth": 60, "resizable": False,  "cellStyle": {"textAlign": "right"}},
            dashGridOptions={
                "rowSelection": "single",
                "animateRows": True,
                "suppressMaintainUnsortedOrder": True,  # 👈 critical
            },
            style={"height": "450px", "width": "100%"},
            className="ag-theme-balham-dark",
        )

        self._register_callbacks()

    def layout(self):
        return html.Div(
            [
                self.options_panel_grid,
                dcc.Store(id="risk-free-rates"),
                dcc.Store(id=f"{self.prefix}-atm-strike"),
                dcc.Store(id=f"{self.prefix}-symbol"),
                dcc.Store(id=self.error_prefix_id),
                dcc.Store(id=f"{self.prefix}-reset-scroll"),
            ],
            style={"display": "flex", "flexDirection": "column", "height": "100%"},
        )

    def _register_callbacks(self):

        # ----------------------------------------------------
        # Callback 1: populate grid with strikes + vols
        # ----------------------------------------------------
        @self.app.callback(
            Output(f"{self.prefix}-symbol", "data"),
            Input("selected-underlying-symbol", "data"),
            prevent_initial_call=True,
        )
        def setup_instrument(selected_instrument):
            try:
                if not selected_instrument:
                    raise dash.exceptions.PreventUpdate

                return selected_instrument

            except Exception:
                return []

        # ----------------------------------------------------
        # Callback 1: populate grid with strikes + vols
        # ----------------------------------------------------
        @self.app.callback(
            Output("options-panel-grid", "rowData"),
            Output(f"{self.prefix}-reset-scroll", "data"),
            Input(f"{self.prefix}-symbol", "data"),
            Input("selected-expiration-vols", "data"),
            prevent_initial_call=True,
        )
        def setup_option(selected_instrument, selected_exp_vols):
            try:
                if not selected_exp_vols:
                    raise dash.exceptions.PreventUpdate

                rows = []
                expiration_date = selected_exp_vols["expiration_date"]

                for strike in selected_exp_vols["strikes"]:
                    strike_str = str(strike)
                    rows.append(
                        {
                            "strike": strike,
                            "expirationDate": expiration_date,
                            "call_vol": selected_exp_vols["call_vols"][strike_str],
                            "put_vol": selected_exp_vols["put_vols"][strike_str],
                        }
                    )

                return rows, "reset"

            except Exception:
                return []

        # ----------------------------------------------------
        # Callback 2: reprice options (rowTransaction)
        # ----------------------------------------------------
        @self.app.callback(
            Output("options-panel-grid", "rowTransaction"),
            Output(f"{self.prefix}-atm-strike", "data"),
            Output(self.error_prefix_id, "data"),
            Input(f"{self.prefix}-symbol", "data"),
            Input("options-panel-grid", "rowData"),
            Input("eval-date", "children"),
            Input("risk-free-rates", "data"),
            prevent_initial_call=True,
        )
        def reprice_option(symbol, row_data, eval_date, risk_free_rates):
            try:
                if not row_data:
                    raise dash.exceptions.PreventUpdate

                spot = float(symbol["price"])
                updates = []
                atm_strike = None

                for row in row_data:
                    strike = row["strike"]
                    call_vol = row["call_vol"]
                    put_vol = row["put_vol"]
                    expiration_date = row["expirationDate"]

                    call = price_european_option(
                        spot,
                        strike,
                        to_ql_date(expiration_date),
                        QuantLib.Option.Call,
                        float(risk_free_rates["1Y"]) / 100.0,
                        float(symbol.get("dividend", 0)) / spot,
                        float(call_vol) / 100.0,
                        valuation_date=to_ql_date(eval_date),
                    )

                    put = price_european_option(
                        spot,
                        strike,
                        to_ql_date(expiration_date),
                        QuantLib.Option.Put,
                        float(risk_free_rates["1Y"]) / 100.0,
                        float(symbol.get("dividend", 0)) / spot,
                        float(put_vol) / 100.0,
                        valuation_date=to_ql_date(eval_date),
                    )

                    updates.append(
                        {
                            "strike": row["strike"],  # rowId key
                            "spot": spot,
                            "expirationDate": expiration_date,
                            "call_vol": call_vol,
                            "call_npv": call["npv"],
                            "call_delta": call["delta"],
                            "call_gamma": call["gamma"],
                            "call_vega": call["vega"],
                            "call_theta": call["theta"],
                            "call_rho": call["rho"],
                            "put_vol": put_vol,
                            "put_npv": put["npv"],
                            "put_delta": put["delta"],
                            "put_gamma": put["gamma"],
                            "put_vega": put["vega"],
                            "put_theta": put["theta"],
                            "put_rho": put["rho"],
                        }
                    )

                    if strike <= spot:
                        atm_strike = row["strike"]

                return {"update": updates}, atm_strike, dash.no_update

            except Exception:
                return dash.no_update, dash.no_update, traceback.format_exc()

        @self.app.callback(
            Output("options-panel-grid", "dashGridOptions"),
            Input(f"{self.prefix}-reset-scroll", "data"),
            Input(f"{self.prefix}-atm-strike", "data"),
            Input("options-panel-grid", "rowData"),
            prevent_initial_call=True,
        )
        def control_grid_scroll(reset_scroll, atm_strike, rows):
            if not rows:
                raise dash.exceptions.PreventUpdate

            # 1️⃣ Highest priority: reset → scroll to top
            if reset_scroll:
                return {
                    "ensureIndexVisible": 0,
                    "position": "top",
            }

            # 2️⃣ Otherwise scroll to ATM
            if atm_strike:
                return {
                    "ensureNodeVisible": {"rowId": atm_strike, "position": "middle"},
                    "setSelectedRowIds": [atm_strike],
            }

            raise dash.exceptions.PreventUpdate
