# Copyright (c) Mike Kipnis - DashQL

import datetime

import QuantLib as ql
import dash
from dash import Input, Output, html, dcc
from dash import callback_context
from Common.Utils import ComponentUtils
from Common.Utils import ConvertUtils

class TenorPanel(object):
    _callbacks_registered = set()  # class-level tracker

    def __init__(self, app: dash.Dash, prefix="tenor", default_tenor="10Y"):
        self.app = app
        self.prefix = prefix

        self.tenor_id = f"{prefix}-tenor-id"
        self.issue_date_id = f"{prefix}-issue-date"
        self.maturity_date_id = f"{prefix}-maturity-date"
        self.default_tenor = default_tenor

        if prefix not in TenorPanel._callbacks_registered:
            self._register_callbacks()
            TenorPanel._callbacks_registered.add(prefix)

    def layout(self):

        return html.Div([
            ComponentUtils.labeled_text_input("Tenor", self.tenor_id, placeholder="e.g. 5Y", value=self.default_tenor, label_color="#61cae9", font_color="#ffa501"),
        ])

    def _register_callbacks(self):

        # ---------- UPDATE ISSUE/MATURITY WHEN TENOR CHANGES ----------
        @self.app.callback(
            Output(self.issue_date_id, "date"),
            Output(self.maturity_date_id, "date"),
            Input(self.tenor_id, "value"),
        )
        def update_dates(tenor_value):

            if tenor_value is None:
                return dash.no_update

            today = ql.Date.todaysDate()
            issue_date = ql.Date(1, today.month(), today.year())

            tenor = ql.Period(tenor_value)
            calendar = ql.NullCalendar()

            advanced_date = calendar.advance(issue_date, tenor, ql.Unadjusted)
            maturity_date = calendar.endOfMonth(
                advanced_date - ql.Period(1, ql.Months)
            )

            # Convert to ISO strings for DatePicker
            issue_iso = issue_date.to_date().isoformat()
            maturity_iso = maturity_date.to_date().isoformat()

            return issue_iso, maturity_iso