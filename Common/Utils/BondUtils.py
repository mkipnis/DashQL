import QuantLib as ql
import Common.Utils.ConvertUtils as ConvertUtils
import Common.Utils.CurveUtils as CurveUtils

PAR = 100
PRICE_TICK_SIZE = 1/32
COUPON_TICK_SIZE = 1/8
ROUND_PRICE = 6
ROUND_MONEY = 2

ROUND_YEARS = 2

def get_fixed_rate_bond(schedule, bond_info):

    calendar = ConvertUtils.calendars_from_strings(schedule["Calendars"])
    # Build schedule
    ql_schedule = ql.Schedule(
        ql.DateParser.parseISO(schedule['issue_date']),
        ql.DateParser.parseISO(schedule['maturity_date']),
        ql.Period(ConvertUtils.enum_from_string(schedule["Frequency"])),
        calendar,
        ConvertUtils.enum_from_string(ConvertUtils.BusDayConv[schedule["BusDayConv"]]),
        ConvertUtils.enum_from_string(ConvertUtils.BusDayConv[schedule["TermBusDayConv"]]),
        ConvertUtils.enum_from_string(schedule["DateGeneration"]),
        schedule["endOfMonth"]
    )

    # Build bond object
    bond = ql.FixedRateBond(
        bond_info["SettlementDays"],
        bond_info["FaceAmount"],
        ql_schedule,
        bond_info["Coupon"],
        ConvertUtils.day_counter_from_string(bond_info["DayCounter"])
    )

    return bond


def get_floating_rate_bond(market_data, index_fixings, schedule, overnight_leg, bond_info):

    calendar = ConvertUtils.calendars_from_strings(schedule["Calendars"])
    # Build schedule
    ql_schedule = ql.Schedule(
        ql.DateParser.parseISO(schedule['issue_date']),
        ql.DateParser.parseISO(schedule['maturity_date']),
        ql.Period(ConvertUtils.enum_from_string(schedule["Frequency"])),
        calendar,
        ConvertUtils.enum_from_string(ConvertUtils.BusDayConv[schedule["BusDayConv"]]),
        ConvertUtils.enum_from_string(ConvertUtils.BusDayConv[schedule["TermBusDayConv"]]),
        ConvertUtils.enum_from_string(schedule["DateGeneration"]),
        schedule["endOfMonth"]
    )

    curve_market_data = market_data["MarketData"]
    rate_helpers = CurveUtils.create_rate_helpers(curve_market_data)
    curve, forecast_curve = CurveUtils.bootstrap(rate_helpers)

    index_name = market_data['Curve']['Index']
    index_class = getattr(ql, index_name)
    ql_index = index_class(forecast_curve)

    for index_fixing in index_fixings[index_name]:
        fixing_date = ql.DateParser.parseISO(index_fixing['fixing_date'])
        if ql_index.isValidFixingDate(fixing_date):
            ql_index.addFixing(fixing_date, index_fixing['rate'], True)

    coupons = ql.OvernightLeg(
        schedule=ql_schedule,
        index=ql_index,
        nominals=overnight_leg['nominals'],
        spreads=overnight_leg['spreads'],
        paymentLag=overnight_leg['paymentLag'],
    )

    # Build bond object
    bond = ql.Bond(
        bond_info["SettlementDays"],
        calendar,
        ql_schedule[0],
        coupons
    )

    return bond

def get_zeros(schedule, bond_info):

    calendar = ConvertUtils.calendars_from_strings(schedule["Calendars"])
    # Build schedule
    ql_schedule = ql.Schedule(
        ql.DateParser.parseISO(schedule['issue_date']),
        ql.DateParser.parseISO(schedule['maturity_date']),
        ql.Period(ConvertUtils.enum_from_string(schedule["Frequency"])),
        calendar,
        ConvertUtils.enum_from_string(ConvertUtils.BusDayConv[schedule["BusDayConv"]]),
        ConvertUtils.enum_from_string(ConvertUtils.BusDayConv[schedule["TermBusDayConv"]]),
        ConvertUtils.enum_from_string(schedule["DateGeneration"]),
        schedule["endOfMonth"]
    )

    zero_coupon_bonds = []
    for cash_flow_date in ql_schedule:
        zero_coupon_bonds.append(
            ql.ZeroCouponBond(
                settlementDays=bond_info["SettlementDays"],
                calendar=calendar,
                faceAmount=bond_info["FaceAmount"],
                maturityDate=cash_flow_date,
            )
        )
        #print(d.to_date().isoformat())
    # Build bond object
    #bond = ql.FixedRateBond(
    #    bond_info["SettlementDays"],
    #    bond_info["FaceAmount"],
    #    ql_schedule,
    #    bond_info["Coupon"],
    #    ConvertUtils.day_counter_from_string(bond_info["DayCounter"])
    #)

    return zero_coupon_bonds

def get_cashflows(bond):
    data = []
    for cf in bond.cashflows():
        c = ql.as_coupon(cf)
        if c is not None:
            data.append({'business_date':c.date().ISO(), 'nominal':c.nominal(), 'rate':round(c.rate()*CurveUtils.RATE_FACTOR, CurveUtils.ROUND_RATE), 'amount': round(c.amount(), ROUND_MONEY)})
        else:
            data.append({'business_date':cf.date().ISO(), 'nominal':None, 'rate':None, 'amount':cf.amount()})

    return data

def get_pricing_results(
                        forecast_curve,
                        discount_curve,
                        bond,
                        clean_price,
                        day_counter,
                        compounding,
                        frequency
    ):
    results = {}

    ql_clean_price = ql.BondPrice(clean_price, ql.BondPrice.Clean)

    engine = ql.DiscountingBondEngine(discount_curve)
    bond.setPricingEngine(engine)

    zspread = ql.BondFunctions.zSpread(
        bond,
        ql_clean_price,
        forecast_curve,
        ConvertUtils.day_counter_from_string(day_counter),
        ConvertUtils.enum_from_string(compounding), ConvertUtils.enum_from_string(frequency)
    )

    yield_value = bond.bondYield(ql_clean_price,
                                 ConvertUtils.day_counter_from_string(day_counter),
                                 ConvertUtils.enum_from_string(compounding),ConvertUtils.enum_from_string(frequency))

    yield_rate = ql.InterestRate(
        yield_value,
        ConvertUtils.day_counter_from_string(day_counter),
        ConvertUtils.enum_from_string(compounding),
        ConvertUtils.enum_from_string(frequency)
    )

    results['Maturity Date'] = bond.maturityDate().ISO()
    results['Yield'] = round(yield_rate.rate()*CurveUtils.RATE_FACTOR, CurveUtils.ROUND_RATE)
    results['Price(Curve)'] = round(bond.cleanPrice(), ROUND_PRICE)
    results['Full-Price(Curve)'] = round(bond.dirtyPrice(), ROUND_PRICE)
    results['Z-Spread(BPS)'] = round(zspread * CurveUtils.BPS_FACTOR, CurveUtils.ROUND_SPREAD)
    results['DV01'] = round(ql.BondFunctions.basisPointValue(bond, yield_rate), ROUND_MONEY)
    results['NPV'] = round(bond.NPV(), ROUND_MONEY)
    results['Modified Duration'] = round(ql.BondFunctions.duration(bond,yield_rate), ROUND_YEARS)
    results['Macaulay Duration'] = round(ql.BondFunctions.duration(bond, yield_rate, ql.Duration.Macaulay), ROUND_YEARS)
    results['Convexity'] = round(ql.BondFunctions.convexity(bond, yield_rate), ROUND_MONEY)
    results['Accrued Interest'] = round(bond.accruedAmount(), ROUND_PRICE)
    results['Settlement Date'] = bond.settlementDate().ISO()
    results['Notional'] = round(bond.notional())
    results['Accrued Days'] = ql.BondFunctions.accruedDays(bond)

    return results
