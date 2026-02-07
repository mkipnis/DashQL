# Copyright (c) Mike Kipnis - DashQL

import dash
from dash import dcc
from dash import Input, Output, html, dcc
import plotly.graph_objs as go

class CurveChartPanel(object):

    def __init__(self, app: dash.Dash,
                 prefix: str):
        self.app = app
        self.curve_chart_id = f"{prefix}-curve-chart"
        self.curve_chart_data_id = f"{prefix}-curve-chart-data"
        self._register_callbacks()

    def layout(self):
        return html.Div([
                dcc.Store(id=self.curve_chart_data_id),
                dcc.Graph(
                id=self.curve_chart_id,
                style={"width": "100%", "height": "400px",
                "border": "1px solid rgba(200, 200, 200, 0.15)"}),
            ])

    def _register_callbacks(self):
        @self.app.callback(
            Output(self.curve_chart_id, "figure"),
            Input(self.curve_chart_data_id, "data"),
            prevent_initial_call=True
        )
        def on_data_ready(pricer_results):
            if pricer_results:

                figure = go.Figure(
                    data=[
                        go.Scatter(
                            x=pricer_results['tenors'],
                            y=pricer_results['rates'],
                            mode="lines+markers",
                            name="Fair Rate",
                            line=dict(
                                color="rgba(101,210,241,1)",
                                width=1.25,
                                shape="spline"  # smooth curve (like lineTension)
                            ),
                            fill="tozeroy",  # fill under the curve
                            fillcolor="rgba(101,210,241,0.1)",  # semi-transparent fill
                        )
                    ],
                    layout=go.Layout(
                        title=dict(
                            text=f"{pricer_results['name']}",
                            x=0.01,
                            xanchor="left",  # 🔹 anchor title to left edge
                            yanchor="top",
                            font=dict(color="#f5f5f5", size=18)
                        ),
                        xaxis=dict(
                            title="Tenor",
                            color="white",
                            showline=False,
                            showgrid=True,  # show grid
                            gridcolor="rgba(200, 200, 200, 0.15)",  # very light gray grid
                            zeroline=False,
                            showticklabels=True,
                        ),
                        yaxis=dict(
                            title="Fair Rate",
                            color="white",
                            showline=False,
                            showgrid=True,
                            gridcolor="rgba(200, 200, 200, 0.15)",  # same faint grid color
                            zeroline=False,
                            showticklabels=True,
                        ),
                        plot_bgcolor="#171b26",
                        paper_bgcolor="#171b26",

                        font=dict(color="#f5f5f5"),
                        margin=dict(l=0, r=0, b=50, t=30),
                        shapes=[]  # no border rectangle
                    )
                )

                return figure
