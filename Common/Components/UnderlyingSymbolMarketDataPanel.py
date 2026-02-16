# Copyright (c) Mike Kipnis - DashQL

import copy

import dash
import dash_ag_grid as dag
from dash import Input, Output, State
from dash import dcc, html
from dash import callback_context as ctx 


class UnderlyingSymbolMarketDataPanel(object):

    def __init__(self, app: dash.Dash, prefix="underlying-symbol-market-data"):
        self.app = app

        self.market_data_grid_id = f"{prefix}-market-data-grid"
        self.user_market_data_id = f"{prefix}-user-market-data"

        self.grid = dag.AgGrid(
            id=self.market_data_grid_id,
            columnDefs=[
                {
                    "headerName": "Symbol",
                    "field": "symbol",
                    "cellStyle": {"textAlign": "left"},
                },
                {
                    "headerName": "Name",
                    "field": "name",
                    "cellClass": "text-left",
                    "hide": True
                },
                {
                    "headerName": "Price",
                    "field": "price",
                    "editable": True,
                    "cellClass": "text-right"
                },
                {
                    "headerName": "Dividend",
                    "field": "dividend",
                    "editable": True,
                    "cellClass": "text-right"
                },

            ],
            rowData=[],
            dashGridOptions={
                "rowSelection": "single",
                "theme": "legacy"
            },

            # 🟦 GLOBAL cellStyle applied to all cells
            defaultColDef={
                "flex": 1,
                "minWidth": 80,
                "resizable": False,
            },

            # ✅ style must be a dict, not a string
            style={"height": "80vh", "width": "100%"},

            className="ag-theme-balham-dark"

        )

        self._register_callbacks()

    def layout(self):
        return html.Div([
            self.grid,
            dcc.Store(id=self.user_market_data_id)
    ])


    def _register_callbacks(self):
        @self.app.callback(
            Output(self.market_data_grid_id, "rowData"),
            Output(self.market_data_grid_id, "selectedRows"),
            Input("underlying-symbol-market-data", "data"),
            prevent_initial_call=True
        )
        def on_data_ready(market_data):
            if not market_data:
                return [], []

            return market_data, [market_data[0]]

        @self.app.callback(
            Output(self.user_market_data_id, "data"),
            Input("underlying-symbol-market-data", "data"),
            State(self.user_market_data_id, "data"),
            Input(self.market_data_grid_id, "rowData"),
            prevent_initial_call=True
        )
        def on_market_data_update(portal_market_data, user_market_data, row_data):
            if not row_data:
                pass

            if user_market_data is None:
                user_market_data = copy.deepcopy(portal_market_data)

            return user_market_data

        # ✅ ROW SELECTION CALLBACK
        @self.app.callback(
            Output("selected-underlying-symbol", "data"),
            Input(self.market_data_grid_id, "selectedRows"),
            Input(self.market_data_grid_id, "cellValueChanged"),
            State("selected-underlying-symbol", "data"),
            prevent_initial_call=True
        )
        def on_row_selected_updated(selected_rows, user_market_data, current_symbol):

            if current_symbol is None:
                return selected_rows[0]

            if selected_rows[0]['symbol'] != current_symbol['symbol']:
                return selected_rows[0]

            if user_market_data:
                return user_market_data[0]['data']

            return selected_rows[0]