# Copyright (c) Mike Kipnis - DashQL

import datetime
import QuantLib as ql
import dash
from dash import Input, Output, html, dcc
from Common.Utils import ComponentUtils, ConvertUtils


class SchedulePanel(object):
    _callbacks_registered = set()  # class-level tracker

    def __init__(self, app: dash.Dash, prefix="bond-schedule"):
        self.app = app
        self.prefix = prefix

        # IDs
        self.busday_id = f"{prefix}-busday-dropdown"
        self.term_busday_id = f"{prefix}-term-busday-dropdown"
        self.compounding_id = f"{prefix}-compounding-dropdown"
        self.frequency_id = f"{prefix}-frequency-dropdown"
        self.dategen_id = f"{prefix}-dategen-dropdown"
        self.calendar_id = f"{prefix}-calendar-dropdown"
        self.day_counter_id = f"{prefix}-day-counter-dropdown"
        self.end_of_month_id = f"{prefix}-end-of-month"

        self.issue_date_id = f"{prefix}-issue-date"
        self.maturity_date_id = f"{prefix}-maturity-date"

        self.output_id = f"{prefix}-output"

        if prefix not in SchedulePanel._callbacks_registered:
            self._register_callbacks()
            SchedulePanel._callbacks_registered.add(prefix)

    def layout(self):

        # ----- Dropdowns -----
        busday_dropdown = dcc.Dropdown(
            id=self.busday_id,
            options=ComponentUtils.dict_to_options(ConvertUtils.BusDayConv),
            value="ModifiedFollowing",
            clearable=False,
            searchable=False,
            className="dark-dropdown",
        )

        term_busday_dropdown = dcc.Dropdown(
            id=self.term_busday_id,
            options=ComponentUtils.dict_to_options(ConvertUtils.BusDayConv),
            value="ModifiedFollowing",
            clearable=False,
            searchable=False,
            className="dark-dropdown",
        )

        calendar_dropdown = dcc.Dropdown(
            id=self.calendar_id,
            options=ComponentUtils.dict_to_options(ConvertUtils.Calendars),
            value="TARGET",
            clearable=False,
            searchable=False,
            multi=True,
            closeOnSelect=False,
            className="dark-dropdown",
        )

        compounding_dropdown = dcc.Dropdown(
            id=self.compounding_id,
            options=ComponentUtils.dict_to_options(ConvertUtils.Compounded),
            value="QuantLib.Compounded",
            clearable=False,
            searchable=False,
            className="dark-dropdown",
        )

        frequency_dropdown = dcc.Dropdown(
            id=self.frequency_id,
            options=ComponentUtils.dict_to_options(ConvertUtils.Frequencies),
            value="QuantLib.Semiannual",
            clearable=False,
            searchable=False,
            className="dark-dropdown",
        )

        dategen_dropdown = dcc.Dropdown(
            id=self.dategen_id,
            options=ComponentUtils.dict_to_options(ConvertUtils.DateGeneration),
            value="DateGeneration.Backward",
            clearable=False,
            searchable=False,
            className="dark-dropdown",
        )

        # ----- Layout with consistent spacing -----
        return html.Div(
            children=[
                ComponentUtils.horizontal_labeled_date_picker(
                    "Issue Date", self.issue_date_id, date=datetime.date.today()
                ),
                ComponentUtils.horizontal_labeled_date_picker(
                    "Maturity Date", self.maturity_date_id, date=datetime.date.today()
                ),
                ComponentUtils.horizontal_labeled_dropdown("Calendars", calendar_dropdown),
                ComponentUtils.horizontal_labeled_dropdown("Business Day Convention", busday_dropdown),
                ComponentUtils.horizontal_labeled_dropdown("Termination Convention", term_busday_dropdown),
                ComponentUtils.horizontal_labeled_dropdown("Compounding", compounding_dropdown),
                ComponentUtils.horizontal_labeled_dropdown("Frequency", frequency_dropdown),
                ComponentUtils.horizontal_labeled_dropdown("Date Generation Rule", dategen_dropdown),
                ComponentUtils.labeled_checkbox("End Of Month", self.end_of_month_id),
            ],
            className="app-column",  # ensures vertical alignment and spacing
            style={"width": "90%"}    # occupy 90% of panel
        )

    def _register_callbacks(self):
        # ---------- OUTPUT ALL PARAMETERS ----------
        @self.app.callback(
            Output(self.output_id, "data"),
            Input(self.calendar_id, "value"),
            Input(self.busday_id, "value"),
            Input(self.term_busday_id, "value"),
            Input(self.compounding_id, "value"),
            Input(self.frequency_id, "value"),
            Input(self.dategen_id, "value"),
            Input(self.issue_date_id, "date"),
            Input(self.maturity_date_id, "date"),
            Input(self.end_of_month_id, "value"),
        )
        def gather_params(
            calendars, busday_conv, term_busday_conv, compounding,
            frequency, dategen, issue_date, maturity_date, end_of_month
        ):

            if any(v is None for v in [
                calendars, busday_conv, term_busday_conv, compounding,
                frequency, dategen, issue_date, maturity_date, end_of_month
            ]):
                return dash.no_update

            return {
                "Calendars": calendars,
                "BusDayConv": busday_conv,
                "TermBusDayConv": term_busday_conv,
                "Compounding": compounding,
                "Frequency": frequency,
                "DateGeneration": dategen,
                "issue_date": issue_date,
                "maturity_date": maturity_date,
                "endOfMonth": bool(end_of_month)
            }
