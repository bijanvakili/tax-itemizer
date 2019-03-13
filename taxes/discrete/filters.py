"""
Custom override filters
"""
from datetime import date

from taxes.receipts.filters import BaseVendorExclusionFilter, OPTIONAL_PAYMENT_METHOD
from taxes.receipts.util.datetime import parse_iso_datestring


class January2019Filter(BaseVendorExclusionFilter):
    """
    January 2019 Transactions
    """
    def __init__(self):
        self.omin_dates = [parse_iso_datestring(d) for d in ['2019-01-12', '2019-01-14']]

    def is_exclusion(self, transaction_description: str, for_date: date, amount: int,
                     payment_method: OPTIONAL_PAYMENT_METHOD):
        return transaction_description.startswith('OMNI') and \
            (for_date >= self.omin_dates[0]) and (for_date <= self.omin_dates[1])


class February2019Filter(BaseVendorExclusionFilter):
    """
    February 2019 Transactions
    """
    def __init__(self):
        self.maui_dates = [parse_iso_datestring(d) for d in ['2019-02-15', '2019-02-22']]

    def is_exclusion(self, transaction_description: str, for_date: date, amount: int,
                     payment_method: OPTIONAL_PAYMENT_METHOD):
        return transaction_description.startswith('WESTIN') and \
            (for_date >= self.maui_dates[0]) and (for_date <= self.maui_dates[1])
