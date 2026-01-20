from concurrent.futures import ThreadPoolExecutor

import QuantLib as ql
from Common.Utils import ConvertUtils
from Common.Utils.Constants import PricingConstants, RoundingConstants
from datetime import date

from Common.Utils import BondUtils
from enum import Enum


def create_rate_helpers( market_data: list):
    deposit_quotes = {}
    future_quotes = {}
    swap_quotes = {}
    bond_quotes = {}

    for instrument_quote in market_data:
        instrument_type = instrument_quote['instrument_type']
        quote = instrument_quote['quote']
        tenor = instrument_quote['tenor']

        if instrument_type == 'Deposit':
            deposit_quotes[ql.Period(tenor[0], tenor[1])] = {'pricer_quote':ql.SimpleQuote(quote / PricingConstants.RATE_FACTOR), 'quote_details':instrument_quote['curve_component']}
        elif instrument_type == 'Future':
            py_date = date.fromisoformat(tenor)
            ql_date = ql.Date(py_date.day, py_date.month, py_date.year)
            future_quotes[ql_date] = {'pricer_quote':ql.SimpleQuote(quote), 'quote_details':instrument_quote['curve_component']}
        elif instrument_type == 'Swap':
            swap_quotes[ql.Period(tenor[0], tenor[1])] = {'pricer_quote': ql.SimpleQuote(quote / PricingConstants.RATE_FACTOR), 'quote_details':instrument_quote['curve_component']}
        elif instrument_type == 'Bond':
            bond_quotes[ql.Period(tenor[0], tenor[1])] = {'pricer_quote': ql.SimpleQuote(quote),
                                                          'quote_details': instrument_quote['curve_component']}


    return { "Deposits" : deposit_quotes, "Futures" : future_quotes, "Swaps" : swap_quotes, "Bonds": bond_quotes }


def transform_curve_components(curve):

    curve_components = curve['CurveComponents']
    calendar = ConvertUtils.calendars_from_strings(curve["Calendars"])

    target_list = []
    latest_maturity_date = ql.Date.todaysDate()
    for curve_component in curve_components:
        instrument_type = curve_component['Type']
        tenor = curve_component['Tenor']
        quote = curve_component['Quote']
        if instrument_type == 'Deposit' or instrument_type == 'Swap' or instrument_type == 'Bond':
            period = ql.Period(tenor)
            latest_maturity_date = calendar.advance(ql.Date.todaysDate(), period)
            days_to_maturity = latest_maturity_date - ql.Date.todaysDate()
            target_list.append(
                {'instrument_type': instrument_type, 'days_to_maturity': days_to_maturity, 'ticker': tenor,
                 'issue_date': ql.Date.todaysDate().to_date().isoformat(), 'maturity_date': latest_maturity_date.to_date().isoformat(),
                 'tenor': (period.length(), period.units()),
                 'quote': quote, "curve_component": curve_component})
        elif instrument_type == 'Future':
            imm_date = ql.IMM.nextDate(latest_maturity_date)
            for expiration in range(8):
                key = str(expiration)
                if key == tenor:
                    target_list.append({
                        'instrument_type': instrument_type,
                        'days_to_maturity': imm_date - ql.Date.todaysDate(),
                        'ticker': ql.IMM.code(imm_date),
                        'tenor': imm_date.to_date().isoformat(),
                        'quote': quote, "curve_component": curve_component

                    })
                imm_date = ql.IMM.nextDate(imm_date)

    return target_list

def bootstrap(quotes):

    today = ql.Settings.instance().evaluationDate

    rate_helpers = []

    # -----------------------------
    # 1) Deposits
    # -----------------------------
    for tenor, quote in quotes.get("Deposits", {}).items():
        qd = quote["quote_details"]

        rate_helpers.append(
            ql.DepositRateHelper(
                ql.QuoteHandle(quote["pricer_quote"]),
                tenor,
                qd["SettlementDays"],
                ConvertUtils.calendars_from_strings(qd["Calendars"]),
                ConvertUtils.enum_from_string(ConvertUtils.BusDayConv[qd["BusDayConv"]]),
                qd["endOfMonth"],
                ConvertUtils.day_counter_from_string(qd["DayCounter"]),
            )
        )

    # -----------------------------
    # 2) Futures
    # -----------------------------
    for tenor, quote in quotes.get("Futures", {}).items():
        qd = quote["quote_details"]

        rate_helpers.append(
            ql.FuturesRateHelper(
                ql.QuoteHandle(quote["pricer_quote"]),
                tenor,
                qd["Months"],
                ConvertUtils.calendars_from_strings(qd["Calendars"]),
                ConvertUtils.enum_from_string(ConvertUtils.BusDayConv[qd["BusDayConv"]]),
                qd["endOfMonth"],
                ConvertUtils.day_counter_from_string(qd["DayCounter"]),
                ql.makeQuoteHandle(0.0),
            )
        )

    # -----------------------------
    # 3) Bonds
    # -----------------------------
    for tenor, quote in quotes.get("Bonds", {}).items():

        qd = quote["quote_details"]
        sched = qd["Schedule"]
        bond_info = qd["FixedRateBond"]

        # Calendar, maturity, issue
        calendar = ConvertUtils.calendars_from_strings(sched["Calendars"])
        maturity = calendar.advance(today, tenor)
        issue_date = today

        # Build schedule
        ql_schedule = ql.Schedule(
            issue_date,
            maturity,
            ql.Period(ConvertUtils.enum_from_string(sched["Frequency"])),
            calendar,
            ConvertUtils.enum_from_string(ConvertUtils.BusDayConv[sched["BusDayConv"]]),
            ConvertUtils.enum_from_string(ConvertUtils.BusDayConv[sched["TermBusDayConv"]]),
            ConvertUtils.enum_from_string(ConvertUtils.DateGeneration[sched["DateGeneration"]]),
            sched["endOfMonth"]
        )

        # Build bond object
        bond = ql.FixedRateBond(
            bond_info["SettlementDays"],
            PricingConstants.PAR,
            ql_schedule,
            [bond_info["Coupon"]/PricingConstants.RATE_FACTOR],
            ConvertUtils.day_counter_from_string(bond_info["DayCounter"])
        )

        # Bond helper
        rate_helpers.append(
            ql.BondHelper(
                ql.QuoteHandle(quote["pricer_quote"]),
                bond
            )
        )

    # -----------------------------
    # 4) OIS / Swap Helpers
    # -----------------------------
    swap_quotes = quotes.get("Swaps")
    if swap_quotes:
        index_name = quotes.get("Index", "Sofr")
        index_class = getattr(ql, index_name)
        swap_index = index_class()

        for tenor, quote in swap_quotes.items():
            qd = quote["quote_details"]
            rate_helpers.append(
                ql.OISRateHelper(
                    qd["SettlementDays"],
                    tenor,
                    ql.QuoteHandle(quote["pricer_quote"]),
                    swap_index
                )
            )

    # -----------------------------
    # 5) Build Curve
    # -----------------------------
    curve = ql.PiecewiseLogLinearDiscount(
        today,
        rate_helpers,
        ql.Actual360()
    )
    curve.enableExtrapolation()

    return curve, ql.YieldTermStructureHandle(curve)

def transform_index_fixings(fixings):

    transformed_index_fixings = {}

    for index in fixings:
        calendar = ConvertUtils.calendars_from_strings(index["Calendars"])
        index_fixings = index['Fixings']

        transformed_index_fixings[index['Index']] = []
        for fixing in index_fixings:
            fixing_date = calendar.advance(ql.Date.todaysDate(), ql.Period(fixing['date_index'], ql.Days))
            transformed_index_fixings[index['Index']].append({'fixing_date': fixing_date.to_date().isoformat(),
                                                              'rate':fixing['rate']/PricingConstants.RATE_FACTOR})

    return transformed_index_fixings


def price_ois_curve(index: str, discount_curve, curve_tenors):
    index_class = getattr(ql, index)
    index_obj = index_class(discount_curve)

    ois_swaps = {}
    for curve_tenor in curve_tenors:
        ois = ql.MakeOIS(ql.Period(curve_tenor), index_obj)
        ois.setPricingEngine(ql.DiscountingSwapEngine(discount_curve))
        ois_swaps[curve_tenor] = ois

    # Run computations in parallel
    with ThreadPoolExecutor() as executor:
        results = executor.map(lambda item: (item[0], item[1].fairRate() * PricingConstants.RATE_FACTOR), ois_swaps.items())

    tenors = []
    rates = []
    for tenor, rate in results:
        tenors.append(tenor)
        rates.append(rate)

    return index_obj, tenors, rates


def price_yield_curve(default_bond_setup, discount_curve, curve_tenors):

    sched = default_bond_setup["Schedule"]
    bond_info = default_bond_setup["FixedRateBond"]

    calendar = ConvertUtils.calendars_from_strings(sched["Calendars"])

    today = ql.Settings.instance().evaluationDate

    ql_frequency = ConvertUtils.enum_from_string(sched["Frequency"])
    ql_compounding = ConvertUtils.enum_from_string(sched["Compounding"])
    ql_day_counter = ConvertUtils.day_counter_from_string(bond_info["DayCounter"])

    # Run computations in parallel
    with ThreadPoolExecutor() as executor:
        results = executor.map(
            lambda item: (
                item,
                discount_curve
                .zeroRate(
                    calendar.advance(today, ql.Period(item)),
                    ql_day_counter,
                    ql_compounding,
                    ql_frequency,
                )
                .rate() * PricingConstants.RATE_FACTOR
            ),
            curve_tenors,
        )

    tenors = []
    rates = []
    for tenor, rate in results:
        tenors.append(tenor)
        rates.append(rate)

    return tenors, rates


def price_mid_curve(index, forecast_curve, swap_tenors, forward_start_tenors):

    ois_midcurves = {}
    ois_midcurves_results = []
    ois_midcurve_surface_results = []

    index_class = getattr(ql, index)
    index_obj = index_class(forecast_curve)

    for curve_tenor in swap_tenors:
        ois_midcurves[curve_tenor] = {}
        for forward_start in forward_start_tenors:
            ois = ql.MakeOIS(ql.Period(curve_tenor), index_obj,
                             fwdStart=ql.Period(forward_start),
                             telescopicValueDates=True)
            ois.setPricingEngine(ql.DiscountingSwapEngine(forecast_curve))
            ois_midcurves[curve_tenor][forward_start] = ois

        with ThreadPoolExecutor() as executor:
            midcurve_results = dict(
                executor.map(
                    lambda item: (item[0], round(item[1].fairRate() * PricingConstants.RATE_FACTOR, RoundingConstants.ROUND_RATE)),
                    ois_midcurves[curve_tenor].items()
                )
            )

        ois_midcurve_surface_results.append(list(midcurve_results.values()))

        midcurve_results['Tenor'] = curve_tenor
        ois_midcurves_results.append(midcurve_results)

    return ois_midcurves, ois_midcurves_results, ois_midcurve_surface_results