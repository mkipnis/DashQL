# Copyright (c) Mike Kipnis - DashQL

from enum import Enum
from typing import Any


class PricingConstants(float, Enum):
    PAR = 100
    PRICE_TICK_SIZE = 1/32
    COUPON_TICK_SIZE = 1/8
    RATE_FACTOR = 100.0
    BPS_FACTOR = RATE_FACTOR * 100.0

class RoundingConstants(int, Enum):
    ROUND_RATE = 3
    ROUND_SPREAD = 1
    ROUND_PRICE = 6
    ROUND_MONEY = 2
    ROUND_YEARS = 2


