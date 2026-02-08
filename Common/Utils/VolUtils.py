# Copyright (c) Mike Kipnis - DashQL

import QuantLib as ql

def price_european_option(
    spot,
    strike,
    maturity_date,
    option_type,       # ql.Option.Call or ql.Option.Put
    risk_free_rate,
    dividend_yield,
    volatility,
    valuation_date=None
):
    # -----------------------
    # Market data
    # -----------------------
    spot_handle = ql.QuoteHandle(ql.SimpleQuote(spot))

    r_ts = ql.YieldTermStructureHandle(
        ql.FlatForward(valuation_date, risk_free_rate, ql.Actual365Fixed())
    )

    q_ts = ql.YieldTermStructureHandle(
        ql.FlatForward(valuation_date, dividend_yield, ql.Actual365Fixed())
    )

    vol_ts = ql.BlackVolTermStructureHandle(
        ql.BlackConstantVol(
            valuation_date,
            ql.NullCalendar(),
            volatility,
            ql.Actual365Fixed()
        )
    )

    # -----------------------
    # Process
    # -----------------------
    process = ql.BlackScholesMertonProcess(
        spot_handle,
        q_ts,
        r_ts,
        vol_ts
    )

    # -----------------------
    # Option
    # -----------------------
    payoff = ql.PlainVanillaPayoff(option_type, strike)
    exercise = ql.EuropeanExercise(maturity_date)

    option = ql.VanillaOption(payoff, exercise)

    engine = ql.AnalyticEuropeanEngine(process)
    option.setPricingEngine(engine)

    return {
        "npv": round(option.NPV(),2),
        "delta": round(option.delta(),4),
        "gamma": round(option.gamma(),4),
        "vega": round(option.vega(),4),
        "theta": round(option.theta(),4),
        "rho": round(option.rho(),4)
    }
