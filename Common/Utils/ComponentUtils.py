import datetime
from dash import html, dcc
import QuantLib as ql

# -----------------------
# Helpers
# -----------------------

def dict_to_options(d):
    """Convert dict to Dash dropdown options"""
    return [{"label": k, "value": v} for k, v in d.items()]


def round_to_rational_fraction(step: float, x: float) -> float:
    return round(x / step) * step


# -----------------------
# Common classes
# -----------------------

COMMON_INPUT_CLASS = "common-input input-narrow"


# -----------------------
# Horizontal form elements
# -----------------------

def horizontal_labeled_dropdown(label, dropdown):
    """Wrap dropdown with a horizontal label"""
    dropdown.className = "dropdown-narrow"

    return html.Div(
        [
            html.Label(label),
            dropdown,
        ],
        className="form-row",
    )


def horizontal_labeled_date_picker(label, picker_id, date=None):
    """Wrap date picker with a horizontal label (tight spacing)"""
    return html.Div(
        [
            html.Label(label),
            dcc.DatePickerSingle(
                id=picker_id,
                date=date,
                className="datepicker-narrow",
            ),
        ],
        className="form-row datepicker-row",
    )


# -----------------------
# Inputs
# -----------------------

def labeled_text_input(
    label,
    input_id,
    placeholder="",
    value="",
    font_color=None,
    label_color=None,
):
    input_style = {}
    if font_color:
        input_style["color"] = font_color

    label_style = {}
    if label_color:
        label_style["color"] = label_color

    return html.Div(
        [
            html.Label(label, style=label_style),
            dcc.Input(
                id=input_id,
                type="text",
                placeholder=placeholder,
                value=value,
                debounce=True,
                className=f"{COMMON_INPUT_CLASS} input-uppercase",
                style=input_style,
            ),
        ],
        className="form-row",
    )


def labeled_number_input(label, input_id, placeholder="", value=None, step=0.01):
    return html.Div(
        [
            html.Label(label),
            dcc.Input(
                id=input_id,
                type="number",
                placeholder=placeholder,
                step=step,
                value=value,
                debounce=True,
                className=COMMON_INPUT_CLASS,
            ),
        ],
        className="form-row",
    )


def labeled_text(label, value_id=None, value=""):
    return html.Div(
        [
            html.Label(label),
            html.Span(
                value if value_id is None else None,
                id=value_id,
                className="common-input input-narrow static-text",
            ),
        ],
        className="form-row",
    )


def labeled_checkbox(label, checkbox_id, checked=True):
    return html.Div(
        [
            html.Label(label),
            dcc.Checklist(
                id=checkbox_id,
                options=[{"label": "", "value": True}],
                value=[True] if checked else [],
                className="checkbox-offset",
            ),
        ],
        className="form-row",
    )


# -----------------------
# Panels
# -----------------------

def panel_label(label):
    return html.Div(
        [html.Label(label)],
        className="panel-label",
    )


def panel_section(label, children, bordered=True):
    """
    Canonical panel:
    - Label on top (no border)
    - Optional left border starts below label
    """
    return html.Div(
        className="panel",
        children=[
            panel_label(label),
            html.Div(
                children=children,
                className="panel-content bordered" if bordered else "panel-content",
            ),
        ],
    )


# -----------------------
# QuantLib helpers
# -----------------------

def enum_from_string(path: str):
    """
    Resolve string like 'QuantLib.Following' to the actual QuantLib enum
    """
    obj = ql
    for part in path.split("."):
        obj = getattr(obj, part)
    return obj
