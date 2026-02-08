# Copyright (c) Mike Kipnis - DashQL

from datetime import datetime

import QuantLib as ql

# -----------------------
# Enum definitions
# -----------------------
BusDayConv = {
    "Following": "Following",
    "ModifiedFollowing": "ModifiedFollowing",
    "Preceding": "Preceding",
    "ModifiedPreceding": "ModifiedPreceding",
    "Unadjusted": "Unadjusted"
}

Compounded = {
    "Simple":"QuantLib.Simple",
    "Compounded":"QuantLib.Compounded",
    "Continuous":"QuantLib.Continuous",
    "SimpleThenCompounded":"QuantLib.SimpleThenCompounded",
    "CompoundedThenSimple":"QuantLib.CompoundedThenSimple"
}

Frequencies = {
    "NoFrequency":"QuantLib.NoFrequency",
    "Once":"QuantLib.Once",
    "Annual":"QuantLib.Annual",
    "Semiannual":"QuantLib.Semiannual",
    "EveryFourthMonth":"QuantLib.EveryFourthMonth",
    "Quarterly":"QuantLib.Quarterly",
    "Bimonthly":"QuantLib.Bimonthly",
    "Monthly":"QuantLib.Monthly",
    "EveryFourthWeek":"QuantLib.EveryFourthWeek",
    "Biweekly":"QuantLib.Biweekly",
    "Weekly":"QuantLib.Weekly",
    "Daily":"QuantLib.Daily"
}

DateGeneration = {
    "Backward":"DateGeneration.Backward",
    "Forward":"DateGeneration.Forward",
    "Zero":"DateGeneration.Zero",
    "ThirdWednesday":"DateGeneration.ThirdWednesday",
    "ThirdWednesdayInclusive":"DateGeneration.ThirdWednesdayInclusive",
    "Twentieth":"DateGeneration.Twentieth",
    "TwentiethIMM":"DateGeneration.TwentiethIMM",
    "OldCDS":"DateGeneration.OldCDS",
    "CDS":"DateGeneration.CDS",
    "CDS2015":"DateGeneration.CDS2015"
}

Calendars = {
    "TARGET":"TARGET",
    "UnitedStates_Settlement": "UnitedStates_Settlement",
    "UnitedKingdom_Settlement":"UnitedKingdom_Settlement",
    "UnitedStates_GovernmentBond":"UnitedStates_GovernmentBond"
}

# For dropdowns: readable text → internal key
DayCounterNames = {
    "Actual360": "Actual360",
    "Actual365Fixed": "Actual365Fixed",
    "Actual366": "Actual366",
    "ActualActual": "ActualActual",
    "ActualActual_ISDA": "ActualActual_ISDA",
    "ActualActual_ISMA": "ActualActual_ISMA",
    "ActualActual_AFB": "ActualActual_AFB",
    "ActualActual_Bond": "ActualActual_Bond",
    "Simple": "Simple",
    "OneDay": "OneDay",
    "30_360": "30_360",
    "30_360_BondBasis": "30_360_BondBasis",
    "30_360_EurobondBasis": "30_360_EurobondBasis",
    "30_360_USA": "30_360_USA",
    "30_360_ISDA": "30_360_ISDA",
    "30_360_ISMA": "30_360_ISMA",
    "30_360_PSA": "30_360_PSA",
    "30_360_SIA": "30_360_SIA",
    "30_360_German": "30_360_German",
    "Business252": "Business252",
}

DayCounterConstructors = {
    "Actual360": lambda: ql.Actual360(),
    "Actual365Fixed": lambda: ql.Actual365Fixed(),
    "Actual366": lambda: ql.Actual366(),
    "ActualActual": lambda: ql.ActualActual(ql.ActualActual.Bond),

    "ActualActual_ISDA": lambda: ql.ActualActual(ql.ActualActual.ISDA),
    "ActualActual_ISMA": lambda: ql.ActualActual(ql.ActualActual.ISMA),
    "ActualActual_AFB":  lambda: ql.ActualActual(ql.ActualActual.AFB),
    "ActualActual_Bond": lambda: ql.ActualActual(ql.ActualActual.Bond),

    "Simple": lambda: ql.SimpleDayCounter(),
    "OneDay": lambda: ql.OneDayCounter(),

    "30_360": lambda: ql.Thirty360(),
    "30_360_BondBasis":      lambda: ql.Thirty360(ql.Thirty360.BondBasis),
    "30_360_EurobondBasis":  lambda: ql.Thirty360(ql.Thirty360.EurobondBasis),
    "30_360_USA":            lambda: ql.Thirty360(ql.Thirty360.USA),
    "30_360_ISDA":           lambda: ql.Thirty360(ql.Thirty360.ISDA),
    "30_360_ISMA":           lambda: ql.Thirty360(ql.Thirty360.ISMA),
    "30_360_PSA":            lambda: ql.Thirty360(ql.Thirty360.PSA),
    "30_360_SIA":            lambda: ql.Thirty360(ql.Thirty360.SIA),
    "30_360_German":         lambda: ql.Thirty360(ql.Thirty360.German),

    "Business252": lambda cal: ql.Business252(cal),
}


def make_calendar(spec: str):
    """
    Convert strings like:
        'QuantLib.TARGET'
        'QuantLib.UnitedStates_Settlement'
        'QuantLib.UnitedKingdom_Settlement'
    into actual QuantLib calendar objects.
    """
    # Remove prefix if present
    if spec.startswith("QuantLib."):
        body = spec[9:]
    else:
        body = spec

    # Simple calendar without market enum
    if "_" not in body:
        cls = getattr(ql, body)   # get class
        obj = cls()               # MUST instantiate
        if not isinstance(obj, ql.Calendar):
            raise TypeError(f"{spec} did not return a Calendar object")
        return obj

    # Calendar with market enum
    class_name, enum_name = body.split("_", 1)
    cls = getattr(ql, class_name)           # class
    enum_value = getattr(cls, enum_name)    # enum
    obj = cls(enum_value)                   # instantiate
    if not isinstance(obj, ql.Calendar):
        raise TypeError(f"{spec} did not return a Calendar object")
    return obj

def merge_calendars_from_strings(spec_list):
    """
    Merge a list of QuantLib calendar spec strings into a single calendar.
    """
    # Make sure every item is a real calendar object
    calendars = [make_calendar(s) for s in spec_list]

    return ql.JointCalendar(calendars)


def calendars_from_strings(calendars):
    if isinstance(calendars, str):
        calendars = [calendars]

    ql_calendar_strs = []
    for s in calendars:
        #print(s)  # debug: see each calendar string
        ql_calendar_strs.append(Calendars[s])

    ql_calendars = merge_calendars_from_strings(ql_calendar_strs)

    return ql_calendars

def day_counter_from_string(daycounter_value, calendar = "TARGET"):
    if daycounter_value == "Business252":
        dc = DayCounterConstructors["Business252"](calendar)
    else:
        dc = DayCounterConstructors[daycounter_value]()

    return  dc

def enum_from_string(path: str):
    """Resolve string like 'QuantLib.Following' to the actual QuantLib enum"""
    obj = ql
    for part in path.split("."):
        obj = getattr(obj, part)
    return obj

def to_ql_date(date_str: str) -> ql.Date:
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return ql.Date(dt.day, dt.month, dt.year)