import dash

from dash import Input, Output, html, dcc, State, ctx

from Common.Components import CurveChartPanel
from Common.Components import CurveMarketDataPanel
from Common.Utils import CurveUtils


class CurvePanel:
    _callbacks_registered = set()

    # =========================
    # Construction
    # =========================
    def __init__(self, app: dash.Dash, curve_market_data_panel: CurveMarketDataPanel, prefix: str = "curve-panel"):
        self.app = app
        self.prefix = prefix
        self.curve_market_data_panel = curve_market_data_panel
        self.curve_chart_panel = CurveChartPanel.CurveChartPanel(app, prefix=self.prefix)

        if self.prefix not in self._callbacks_registered:
            self._register_callbacks()
            self._callbacks_registered.add(self.prefix)

    def layout(self):
        return html.Div([
            self.curve_chart_panel.layout()
            ])

    def _register_callbacks(self):
        @self.app.callback(
            Output(self.curve_chart_panel.curve_chart_data_id, "data"),
            Input(self.curve_market_data_panel.index_dropdown_id, "value"),
            Input(self.curve_market_data_panel.user_market_data_id, "data"),
        )
        def _select_curve(name, curves):

            discount_curve_data = curves[name]
            market_data = discount_curve_data["MarketData"]
            rate_helpers = CurveUtils.create_rate_helpers(market_data)
            curve, discount_curve = CurveUtils.bootstrap(rate_helpers)
            day_counter = discount_curve_data["Curve"]["DayCounter"]

            curve_tenors = ["1M", "3M", "6M"]

            for curve_tenor in range(1, 31):  # 1 to 30 inclusive
                swap_curve_tenor = f"{curve_tenor}Y"
                curve_tenors.append(swap_curve_tenor)

            if 'Index' in discount_curve_data['Curve']:
                index = discount_curve_data['Curve']['Index']
                index_obj, tenors, rates = CurveUtils.price_ois_curve(index,discount_curve, curve_tenors)

                return {'name': name,'tenors': tenors, 'rates': rates}

            else:
                default_bond_setup = discount_curve_data['Curve']['DefaultBondSetup']
                tenors, rates = CurveUtils.price_yield_curve(default_bond_setup,discount_curve, curve_tenors)

                return {'name': name, 'tenors': tenors, 'rates': rates}