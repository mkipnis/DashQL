# Copyright (c) Mike Kipnis - DashQL

from typing import Optional, Dict, Any

import dash
import dash_ag_grid as dag
from dash import Input, Output, html, dcc

class DataGridPanel(object):

    def __init__(
            self,
            app: dash.Dash,
            column_defs: list,
            prefix: str,
            default_column_defs: Optional[Dict[str, Any]] = None,
            dashGridOptions: Optional[Dict[str, Any]] = {},
    ):
        self.app = app
        self.data_grid_id = f"{prefix}-grid-id"
        self.row_data_id = f"{prefix}-row-data-id"

        # Provide default if None
        if default_column_defs is None:
            default_column_defs = {
                "flex": 1,
                "minWidth": 50,
                "resizable": False
            }

        dashGridOptions["theme"] = "legacy"

        self.grid = dag.AgGrid(
            id=self.data_grid_id,
            columnDefs=column_defs,
            rowData=[],
            defaultColDef=default_column_defs,
            dashGridOptions=dashGridOptions,
            style={"height": "450px", "width": "100%"},
            className="ag-theme-balham-dark",
        )

        self._register_callbacks()

    #def get_data_grid_id(self):
    #    return self.data_grid_id

    def get_row_data_id(self):
        return self.row_data_id

    def layout(self):
        return html.Div(
            [
                # Store that feeds the grid
                dcc.Store(id=self.row_data_id),

                html.Div(
                    self.grid,
                    style={"flex": "1"},
                ),
            ],
            style={
                "display": "flex",
                "flexDirection": "row",
                "flexWrap": "nowrap",
                "gap": "10px",
                "alignItems": "stretch",
            }
        )

    def _register_callbacks(self):
        @self.app.callback(
            Output(self.data_grid_id, "rowData"),
            Input(self.row_data_id, "data"),
        )
        def on_data_ready(row_data):
            return row_data or []

