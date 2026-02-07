# Copyright (c) Mike Kipnis - DashQL

import copy

import dash
import dash_ag_grid as dag
from dash import Input, Output, State
import QuantLib as ql
import plotly.graph_objs as go
from dash import dcc, html


class CurveMarketDataPanel(object):

    def __init__(self, app: dash.Dash, prefix="curve-market-data"):
        self.app = app

        self.market_data_grid_id = f"{prefix}-market-data-grid"
        self.index_dropdown_id = f"{prefix}-index-dropdown"
        self.user_market_data_id = f"{prefix}-user-market-data"

        self.grid = dag.AgGrid(
            id=self.market_data_grid_id,
            columnDefs=[
                {
                    "headerName": "Instrument",
                    "field": "instrument_type",
                    "cellStyle": {"textAlign": "right"},
                    "hide": True
                },
                {
                    "headerName": "Days to Maturity",
                    "field": "days_to_maturity",
                    "cellStyle": {"textAlign": "right"},
                    "sortable": True,
                    "sort": "asc",
                    "hide": True
                },
                {
                    "headerName": "Ticker",
                    "field": "ticker",
                    "cellClass": "text-right"
                },
                {
                    "headerName": "Quote",
                    "field": "quote",
                    "editable": True,
                    "cellClass": "text-right"
                },
                {
                    "headerName": "Tenor",
                    "field": "tenor",
                    "cellStyle": {"textAlign": "right"},
                    "hide": True
                },
            ],
            rowData=[],
            dashGridOptions={
                "rowSelection": "single"
            },

            # 🟦 GLOBAL cellStyle applied to all cells
            defaultColDef={
                "flex": 1,
                "minWidth": 100,
                "resizable": False,


                "cellStyle": {
                    "function": (
                        "params.data.instrument_type === 'Deposit' ? {color: '#98c379'} : "
                        "params.data.instrument_type === 'Future'  ? {color: '#2aabb8'} : "
                        "params.data.instrument_type === 'Swap' ? {color: '#FFFFFF'} : "
                        "params.data.instrument_type === 'Bond' ? {color: '#f09d08'} : "
                        "{color: '#99ff66', fontWeight: 600}"
                    )
                }
            },

            # ✅ style must be a dict, not a string
            style={"height": "80vh", "width": "100%"},

            className="ag-theme-balham-dark"

        )

        self._register_callbacks()

    def layout(self):
        return html.Div([
            dcc.Dropdown(
                id=self.index_dropdown_id,
                options=[],
                value=None,
                clearable=False
            ),
            self.grid,
            dcc.Store(id=self.user_market_data_id),
    ])


    def _register_callbacks(self):
        @self.app.callback(
            Output(self.index_dropdown_id, "options"),
            Output(self.index_dropdown_id, "value"),
            Input("portal-curves", "data"),
            prevent_initial_call=True
        )
        def on_index_data(swap_curves):
            if not swap_curves:
                return [], None

            options = [{"label": index, "value": index} for index in swap_curves.keys()]

            return options, next(iter(swap_curves))

        @self.app.callback(
            Output(self.market_data_grid_id, "rowData"),
            Input(self.index_dropdown_id, "value"),
            State("portal-curves", "data"),
            State(self.user_market_data_id, "data"),
            prevent_initial_call=True
        )
        def on_data_ready(curve_name, swap_data, user_market_data):
            if not curve_name:
                return [], None

            if user_market_data is not None and curve_name in user_market_data:
                curve = user_market_data[curve_name]
            else:
                curve = swap_data[curve_name]

            curve['MarketData'].sort(
                key=lambda x: (x['days_to_maturity'] if x['days_to_maturity'] is not None else float('inf'))
            )

            return curve['MarketData']

        @self.app.callback(
            Output(self.user_market_data_id, "data"),
            State(self.index_dropdown_id, "value"),
            State("portal-curves", "data"),
            State(self.user_market_data_id, "data"),
            Input(self.market_data_grid_id, "rowData"),
            Input(self.market_data_grid_id, "cellValueChanged")
        )
        def on_market_data_update(curve_name, portal_market_data, user_market_data, row_data, _):
            if row_data:
                pass

            if user_market_data is None:
                user_market_data = copy.deepcopy(portal_market_data)

            user_market_data[curve_name]['MarketData'] = row_data

            return user_market_data