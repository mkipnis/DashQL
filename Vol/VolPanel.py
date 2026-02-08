# Copyright (c) Mike Kipnis - DashQL

import copy
import traceback

import dash
import dash_ag_grid as dag
from dash import Input, Output, html, dcc, State
import plotly.graph_objs as go

from Common.Utils import ComponentUtils, CurveUtils


def normalize_strike_value(value):
    """
    Return int if the number is whole, otherwise float.
    """
    try:
        num = float(value)
        if num.is_integer():
            return str(int(num))
        return str(num)
    except (ValueError, TypeError):
        return str(value)

class VolPanel(object):

    def __init__(self, app: dash.Dash, prefix: str):
        self.app = app
        self.prefix = f"{prefix}-vol-panel-id"

        self.user_vol_market_data_id = f"{self.prefix}-user-vol-market-data"
        self.error_prefix_id = f"{self.prefix}-error"

        self.vol_panel_grid_id = f"{self.prefix}-vol-panel-grid"

        self.vol_panel_grid = dag.AgGrid(
            id=self.vol_panel_grid_id,
            columnDefs=[],
            rowData=[],
            defaultColDef={
                "flex": 1,
                "minWidth": 50,
                "resizable": False,
                "cellStyle": {"textAlign": "right"}
            },
            style={"height": "450px", "width": "100%"},
            className="ag-theme-balham-dark",
            dashGridOptions={
                "context": {"selectedExpiration": None},
                "suppressCellFocus": True,
                "theme": "legacy"
            },
        )

        self.vol_panel_graph = dcc.Graph(id="vol-panel-graph")

        self._register_callbacks()

    def layout(self):
        return html.Div(
            [
                html.Div(
                    [
                        html.Div(
                            [
                                # Left panel: AG Grid
                                html.Div(
                                    self.vol_panel_grid,
                                    style={
                                        "flex": "1 1 50%",  # 50% of width
                                        "minHeight": "0",
                                        "overflow": "auto",  # scroll if content exceeds height
                                    }
                                ),

                                # Right panel: Graph
                                html.Div(
                                    self.vol_panel_graph,
                                    style={
                                        "flex": "1 1 50%",  # 50% of width
                                        "minHeight": "0",
                                        "display": "flex",
                                        "flexDirection": "column",
                                    }
                                ),
                            ],
                            style={
                                "display": "flex",
                                "gap": "8px",
                                "minHeight": "0",
                                "height": "100%",  # make container take full available height
                            },
                        ),
                        html.Div(
                            "double-click quote to update the volatility",
                            style={
                                "fontSize": "12px",
                                "color": "#cccccc",
                                "marginTop": "4px",
                                "textAlign": "left",
                            },
                        ),
                        dcc.Store(id=self.user_vol_market_data_id),
                        dcc.Store(id="selected-expiration-vols"),
                    ],
                    style={
                        "display": "flex",
                        "flexDirection": "column",
                        "flex": "1 1 auto",
                        "gap": "6px",
                        "minHeight": 0,
                    },
                )
            ],
            style={
                "display": "flex",
                "flexDirection": "row",
                "flexWrap": "nowrap",
                "gap": "10px",
                "alignItems": "stretch",
            },
        )

    def _register_callbacks(self):

        # ---------------------------------------------------------
        # Populate grid
        # ---------------------------------------------------------
        @self.app.callback(
            Output("expiration-dates", "data"),
            Output(self.vol_panel_grid_id, "columnDefs"),
            Output(self.vol_panel_grid_id, "rowData"),
            Input("selected-underlying-symbol", "data"),
            Input("vol-market-data", "data"),
        )
        def populate_underlying_symbol_vol_data(underlying_symbol, vols):

            underlying_symbol_vols = vols[underlying_symbol["symbol"]]

            column_defs = [
                {
                    "field": "strike",
                    "minWidth": 60,
                    "maxWidth": 80,
                    "cellStyle": {"textAlign": "right", "color": "#70b676"},
                    "headerClass": "ag-right-aligned-header",
                    "sort": "asc",
                    "pinned": "left",
                    "lockPinned": True,
                    "suppressMovable": True
                }
            ]

            # ✅ merged_strikes as set
            merged_strikes = set()
            vols_for_exps_and_strikes = {}

            for expiration_date, vol_for_exp in underlying_symbol_vols.items():

                expiration_section = {
                    "headerName": expiration_date,
                    "children": [],
                }

                for side in ("call", "put"):
                    expiration_section["children"].append(
                        {
                            "headerName": side.capitalize(),
                            "field": f"{expiration_date}_{side}",
                            "editable": True,
                            "minWidth": 110,
                            "maxWidth": 160,
                            "cellStyle": {"textAlign": "right"},
                            "headerClass": "ag-right-aligned-header",
                            "cellClassRules": {
                                "selected-expiration-cell-call": """
                                    params.context.selectedExpiration &&
                                    params.colDef.field.includes(params.context.selectedExpiration) &&
                                    params.colDef.field.includes("call") 
                                """,
                                "selected-expiration-cell-put": """
                                    params.context.selectedExpiration &&
                                    params.colDef.field.includes(params.context.selectedExpiration) &&
                                    params.colDef.field.includes("put") 
                                """
                            },
                        }
                    )

                column_defs.append(expiration_section)

                merged_strikes = sorted({
                    float(row["strike"])
                    for side in ("calls", "puts")
                    for row in vol_for_exp.get(side, [])
                })

                for side in ("calls", "puts"):
                    side_map = vols_for_exps_and_strikes.setdefault(expiration_date, {}).setdefault(side, {})
                    for row in vol_for_exp.get(side, []):
                        side_map[row["strike"]] = row["vol"]

            row_data = []
            for strike in merged_strikes:
                row = {"strike": strike, 'strike_str': normalize_strike_value(strike)}
                for expiration_date, vol_for_exp in vols_for_exps_and_strikes.items():
                    row[f"{expiration_date}_call"] = vol_for_exp.get("calls", {}).get(strike)
                    row[f"{expiration_date}_put"] = vol_for_exp.get("puts", {}).get(strike)
                row_data.append(row)

            expiration_dates = list(underlying_symbol_vols.keys())

            return expiration_dates, column_defs, row_data

        # ---------------------------------------------------------
        # Update AG Grid context
        # ---------------------------------------------------------
        @self.app.callback(
            Output(self.vol_panel_grid_id, "dashGridOptions"),
            Input("selected-expiration-date", "data"),
            prevent_initial_call=True,
        )
        def update_grid_context(selected_exp):
            return {
                "context": {"selectedExpiration": selected_exp},
                "suppressCellFocus": True,
            }

        # ---------------------------------------------------------
        # Force column refresh (style update)
        # ---------------------------------------------------------
        @self.app.callback(
            Output(self.vol_panel_grid_id, "columnDefs", allow_duplicate=True),
            Input("selected-expiration-date", "data"),
            State(self.vol_panel_grid_id, "columnDefs"),
            prevent_initial_call=True,
        )
        def refresh_column_defs(_, column_defs):
            return copy.deepcopy(column_defs)

        # ---------------------------------------------------------
        # Store edited market data
        # ---------------------------------------------------------
        @self.app.callback(
            Output(self.user_vol_market_data_id, "data"),
            Input(self.vol_panel_grid_id, "rowData"),
            Input(self.vol_panel_grid_id, "cellValueChanged"),
        )
        def on_market_data_update(row_data, _):
            return row_data

        # ---------------------------------------------------------
        # Handle grid click → expiration selection
        # ---------------------------------------------------------
        @self.app.callback(
            Output("selected-expiration-date", "data"),
            Input(self.vol_panel_grid_id, "cellClicked"),
            Input("expiration-dates", "data"),
            State("selected-expiration-date", "data"),
            prevent_initial_call=True,
        )
        def on_cell_clicked(cell, expiration_dates, current_expiration_date):

            if not cell:
                return expiration_dates[0]

            col_id = cell["colId"]
            if col_id == "strike":
                return dash.no_update

            date_part = col_id.split("_")[0]
            expiration_date = date_part if date_part in expiration_dates else expiration_dates[0]

            if current_expiration_date != expiration_date:
                return expiration_date
            else:
                return dash.no_update


        # ---------------------------------------------------------
        # Update graph
        # ---------------------------------------------------------
        @self.app.callback(
            Output("selected-expiration-vols", "data"),
            Output("vol-panel-graph", "figure"),
            Input("selected-expiration-date", "data"),
            Input(self.user_vol_market_data_id, "data"),
            prevent_initial_call=True,
        )
        def update_graph(expiration_date, user_market_data):

            if not expiration_date or not user_market_data:
                raise dash.exceptions.PreventUpdate

            strikes = []
            call_vols = {}
            put_vols = {}

            for row in user_market_data:
                strike = row["strike"]
                strikes.append(strike)
                call_vols[strike] = float(row.get(f"{expiration_date}_call"))
                put_vols[strike] = float(row.get(f"{expiration_date}_put"))

            strike_normalized = [normalize_strike_value(v) for v in strikes]

            fig = go.Figure()

            # Calls
            fig.add_trace(go.Scatter(
                x=strike_normalized,
                y=list(call_vols.values()),
                mode='lines+markers',
                name='Calls',
                line=dict(color='rgba(75,192,192,1)', width=1.5, shape='spline'),
                fill='tozeroy',
                fillcolor='rgba(75,192,192,0.2)',
                marker=dict(size=4)
            ))

            # Puts
            fig.add_trace(go.Scatter(
                x=strike_normalized,
                y=list(put_vols.values()),
                mode='lines+markers',
                name='Puts',
                line=dict(color='rgba(255,99,132,1)', width=1.5, shape='spline'),
                fill='tozeroy',
                fillcolor='rgba(255,99,132,0.2)',
                marker=dict(size=4)
            ))

            # Layout with labels horizontally aligned
            fig.update_layout(
                paper_bgcolor='#192231',
                plot_bgcolor='#192231',
                font=dict(color='#ffeed9'),

                xaxis=dict(title='Strike', showgrid=True, gridcolor='#424242', color='#ffeed9'),
                yaxis=dict(title='Volatility', showgrid=True, gridcolor='#424242', color='#ffeed9'),
                margin=dict(l=50, r=50, t=50, b=50),

                showlegend=False,  # hide default legend

                annotations=[
                    # Calls label (left)
                    dict(
                        x=0.45,  # normalized x-position
                        y=1.05,
                        xref='paper',
                        yref='paper',
                        text='Calls',
                        showarrow=False,
                        font=dict(color='rgba(75,192,192,1)', size=14)
                    ),
                    # Puts label (right, next to Calls)
                    dict(
                        x=0.55,
                        y=1.05,
                        xref='paper',
                        yref='paper',
                        text='Puts',
                        showarrow=False,
                        font=dict(color='rgba(255,99,132,1)', size=14)
                    ),
                    # Expiration date (right top)
                    dict(
                        x=1.0,
                        y=1.05,
                        xref='paper',
                        yref='paper',
                        xanchor='right',
                        text=expiration_date,
                        showarrow=False,
                        font=dict(color='#FFA500', size=16)
                    )
                ]
            )

            return {
                "expiration_date": expiration_date,
                "strikes": strikes,
                "call_vols": call_vols,
                "put_vols": put_vols,
            }, fig
