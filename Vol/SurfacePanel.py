# Copyright (c) Mike Kipnis - DashQL

import traceback

import dash
import dash_ag_grid as dag
from dash import Input, Output, html, dcc
import plotly.graph_objs as go


from Common.Utils import ComponentUtils, CurveUtils


class SurfacePanel(object):

    def __init__(self, app: dash.Dash, prefix: str, user_vol_market_data_id: str = ""):
        self.app = app
        self.prefix = f"{prefix}-surface-panel-id"
        self.user_vol_market_data_id = user_vol_market_data_id

        self.error_prefix_id = f"{self.prefix}-error"


        self.calls_panel_graph = dcc.Graph(id="calls-panel-graph")
        self.puts_panel_graph = dcc.Graph(id="puts-panel-graph")

        self._register_callbacks()

    def layout(self):

        return html.Div(
    [
        # ---- Row 2: Two Graphs side by side ----
        html.Div(
            [
                # Calls graph - 50%
                html.Div(
                    self.calls_panel_graph,
                    style={
                        "flex": "1 1 50%",  # 50% width
                        "minHeight": 0,
                        "display": "flex",
                        "flexDirection": "column",
                    },
                ),
                # Puts graph - 50%
                html.Div(
                    self.puts_panel_graph,
                    style={
                        "flex": "1 1 50%",  # 50% width
                        "minHeight": 0,
                        "display": "flex",
                        "flexDirection": "column",
                    },
                ),
            ],
            style={
                "display": "flex",
                "flex": "1 1 auto",
                "gap": "8px",
                "minHeight": 0,  # critical for AG Grid / graphs
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
            Output("calls-panel-graph", "figure"),
            Output("puts-panel-graph", "figure"),
            Output(self.error_prefix_id, "data"),
            Input("expiration-dates", "data"),
            Input(self.user_vol_market_data_id, "data"),
        )
        def update_forecast_curve(expiration_dates, vols):

            if not expiration_dates or not vols:
                return dash.no_update, dash.no_update, dash.no_update

            strikes = []
            calls = []
            puts = []
            for expiration_date in expiration_dates:
                call_column = expiration_date + '_call'
                put_column = expiration_date + '_put'
                strike_calls = []
                strike_puts = []
                for vol in vols:
                    strikes.append(vol['strike'])
                    strike_calls.append(vol[call_column])
                    strike_puts.append(vol[put_column])
                calls.append(strike_calls)
                puts.append(strike_puts)

            fig_calls = go.Figure(
                data=[
                    go.Surface(
                        x=strikes,
                        y=expiration_dates,
                        z=calls,
                        hovertemplate="Strike:%{x}<br>Exp.Date:%{y}<br>Vol: %{z:.2f}<extra></extra>",
                        type="surface",
                        colorscale="Viridis",
                        # opacity=0.90,
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
                        text=f"Calls",
                        x=0.01,
                        xanchor="left",
                        yanchor="top",
                        font=dict(color="#f5f5f5", size=18),
                        pad=dict(t=25, b=10)
                    ),
                    scene=dict(
                        xaxis=dict(
                            title="Strike",
                            color="white",  # axis label color
                            tickfont=dict(color="white"),  # tick labels color
                            gridcolor="rgba(140,143,144,0.05)",
                            gridwidth=1,
                            showbackground=False,
                        ),
                        yaxis=dict(
                            title="Exp.Date",
                            color="white",
                            tickfont=dict(color="white"),
                            gridcolor="rgba(140,143,144,0.05)",
                            gridwidth=1,
                            showbackground=False,
                        ),
                        zaxis=dict(
                            title="Vol",
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

            fig_puts = go.Figure(
                data=[
                    go.Surface(
                        x=strikes,
                        y=expiration_dates,
                        z=puts,
                        hovertemplate="Strike:%{x}<br>Exp.Date:%{y}<br>Vol: %{z:.2f}<extra></extra>",
                        type="surface",
                        colorscale="Viridis",
                        # opacity=0.90,
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
                        text=f"Puts",
                        x=0.01,
                        xanchor="left",
                        yanchor="top",
                        font=dict(color="#f5f5f5", size=18),
                        pad=dict(t=25, b=10)
                    ),
                    scene=dict(
                        xaxis=dict(
                            title="Strike",
                            color="white",  # axis label color
                            tickfont=dict(color="white"),  # tick labels color
                            gridcolor="rgba(140,143,144,0.05)",
                            gridwidth=1,
                            showbackground=False,
                        ),
                        yaxis=dict(
                            title="Exp.Date",
                            color="white",
                            tickfont=dict(color="white"),
                            gridcolor="rgba(140,143,144,0.05)",
                            gridwidth=1,
                            showbackground=False,
                        ),
                        zaxis=dict(
                            title="Vol",
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


            return fig_calls, fig_puts, dash.no_update
