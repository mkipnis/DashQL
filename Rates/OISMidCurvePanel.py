import traceback

import dash
import dash_ag_grid as dag
from dash import Input, Output, html, dcc
import plotly.graph_objs as go


from Common.Utils import ComponentUtils, CurveUtils


class OISMidCurvePanel(object):

    def __init__(self, app: dash.Dash, prefix: str, user_market_data_id: str = ""):
        self.app = app
        self.prefix = f"{prefix}-mid-curve-panel-id"
        self.user_market_data_id = user_market_data_id
        self.forecast_curve_id = f"{self.prefix}-forecast-curve"
        self.forecast_curve_data_id = f"{self.prefix}-forecast-curve-data"

        self.error_prefix_id = f"{self.prefix}-error"

        self.swap_tenors = [
            '6M', '1Y', '2Y', '3Y', '5Y', '7Y', '10Y', '15Y', '20Y', '25Y', '30Y', '40Y', '50Y'
        ]

        self.forward_start_tenors = [
            '0D', '1M', '2M', '3M', '6M', '9M', '1Y', '18M', '2Y',
            '3Y', '5Y', '10Y', '15Y', '30Y'
        ]

        self.grid = dag.AgGrid(
            id="mid-curve-grid",
            columnDefs=[
                {
                    "headerName": "Curve",
                    "children": [
                        {
                            "headerName": "Tenor",
                            "field": "Tenor",
                            "cellStyle": {"textAlign": "right", "color":"white"},
                            "pinned": "left",
                            "width": 80
                        }
                    ]
                },
                {
                    "headerName": "Forward Start",
                    "children": [
                        {"field": t, "headerName": t, "cellStyle": {"textAlign": "right"}}
                        for t in self.forward_start_tenors
                    ]
                }
            ],
            rowData=[],
            defaultColDef={"flex": 1, "minWidth": 50, "resizable": False},
            style={"height": "450px", "width": "100%"},
            className="ag-theme-balham-dark",
        )

        self.mid_curve_surface = dcc.Graph(id="mid_curve_surface")

        self._register_callbacks()

    def layout(self):
        forecast_dropdown = dcc.Dropdown(
            id=self.forecast_curve_id,
            clearable=False
        )

        return html.Div(
            [
                html.Div(
                    [
                        # ---- Row 1: Label + Dropdown ----
                        html.Div(
                            [
                                ComponentUtils.horizontal_labeled_dropdown(
                                    "Forecast Curve",
                                    forecast_dropdown
                                ),
                                ComponentUtils.panel_label("Forecast mid-curves"),
                            ],
                            style={
                                "display": "flex",
                                "alignItems": "center",
                                "justifyContent": "space-between",
                                "gap": "12px",
                                "width": "100%",
                            },
                        ),

                        dcc.Store(id=self.forecast_curve_data_id),

                        html.Hr(className="divider"),

                        # ---- Row 2: Grid + Graph ----
                        html.Div(
                            [
                                self.grid,
                                self.mid_curve_surface,
                            ],
                            style={
                                "display": "flex",
                                "flex": "1 1 auto",
                                "gap": "8px",
                                "minHeight": 0,  # critical for AG Grid / graphs
                            },
                        ),
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
        # --- Populate curve dropdowns ---
        @self.app.callback(
            Output(self.forecast_curve_id, "options"),
            Output(self.forecast_curve_id, "value"),
            Input("portal-curves", "data"),
        )
        def on_curve_data_change(user_market_data):
            if not user_market_data:
                return [], None

            forecast_curves = []

            for name, curve in user_market_data.items():
                if isinstance(curve.get("Curve"), dict) and "Index" in curve["Curve"]:
                    forecast_curves.append({"label": name, "value": name})

            forecast_value = forecast_curves[0]["value"] if forecast_curves else None
            return forecast_curves, forecast_value


        @self.app.callback(
            Output("mid-curve-grid", "rowData"),
            Output("mid_curve_surface", "figure"),
            Output(self.error_prefix_id, "data"),
            Input(self.forecast_curve_id, "value"),
            Input(self.user_market_data_id, "data"),
        )
        def update_forecast_curve(curve_name, curves):

            if curve_name and curves:

                try:
                    discount_curve_data = curves[curve_name]
                    market_data = discount_curve_data["MarketData"]
                    rate_helpers = CurveUtils.create_rate_helpers(market_data)
                    curve, discount_curve = CurveUtils.bootstrap(rate_helpers)

                    swap_index = curves[curve_name]['Curve']['Index']

                    ois_midcurves, ois_midcurves_results, ois_midcurve_surface_results = (
                        CurveUtils.price_mid_curve(swap_index, discount_curve, self.swap_tenors, self.forward_start_tenors))
                except Exception as e:
                    return (dash.no_update,) * 2, {
                        "message": str(e),
                        "traceback": traceback.format_exc(),
                    }

                fig = go.Figure(
                    data=[
                        go.Surface(
                            x=self.forward_start_tenors,
                            y=self.swap_tenors,
                            z=ois_midcurve_surface_results,
                            hovertemplate="Forward Start:%{x}<br>Tenor:%{y}<br>Fair Rate: %{z:.2f}<extra></extra>",
                            type="surface",
                            colorscale="Viridis",
                            #opacity=0.90,
                            contours=dict(
                                z=dict(
                                    show=True,
                                    usecolormap=True,
                                    highlightcolor="#42f462",
                                    project=dict(z=True)
                                )
                            ),
                            showscale=True,
                            colorbar=dict(
                                title=dict(
                                    text="Fair Rate",
                                    font=dict(color="#f5f5f5")
                                ),
                                tickcolor="#f5f5f5",
                                tickfont=dict(color="#f5f5f5"),
                                bgcolor="rgba(0,0,0,0)",
                                outlinecolor="rgba(255,255,255,0.1)",
                            ),
                        )
                    ],
                    layout=go.Layout(
                        title=dict(
                            text=f"Forward Rate Surface ({curve_name})",
                            x=0.01,
                            xanchor="left",
                            yanchor="top",
                            font=dict(color="#f5f5f5", size=18),
                            pad=dict(t=25, b=10)
                        ),
                        scene=dict(
                            xaxis=dict(
                                title="Forward Start",
                                color="white",  # axis label color
                                tickfont=dict(color="white"),  # tick labels color
                                gridcolor="rgba(140,143,144,0.05)",
                                gridwidth=1,
                                showbackground=False,
                            ),
                            yaxis=dict(
                                title="Swap Tenor",
                                color="white",
                                tickfont=dict(color="white"),
                                gridcolor="rgba(140,143,144,0.05)",
                                gridwidth=1,
                                showbackground=False,
                            ),
                            zaxis=dict(
                                title="Fair Rate",
                                color="white",
                                tickfont=dict(color="white"),
                                gridcolor="rgba(140,143,144,0.05)",
                                gridwidth=1,
                                showbackground=False,
                            ),
                            bgcolor="rgba(0,0,0,0)"
                        ),
                        plot_bgcolor="#171b26",
                        paper_bgcolor="#171b26",
                        font=dict(color="#f5f5f5"),
                        margin=dict(l=0, r=0, b=50, t=20),
                    )

                )


                return ois_midcurves_results, fig, None

            return (dash.no_update,) *3
