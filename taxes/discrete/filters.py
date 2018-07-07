"""
Custom override filters
"""
from datetime import date

from taxes.receipts import models
from taxes.receipts.filters import BaseVendorExclusionFilter, OPTIONAL_PAYMENT_METHOD
from taxes.receipts.util.datetime import parse_iso_datestring


class April2018Filter(BaseVendorExclusionFilter):
    """
    April 2018 exclusions
    """
    def is_exclusion(self, transaction_description: str, for_date: date, amount: int,
                     payment_method: OPTIONAL_PAYMENT_METHOD):
        """ Mis-entered rent check """
        if amount == 111000 and for_date == date(2018, 4, 9):
            return True
        return False


class May2018Filter(BaseVendorExclusionFilter):
    """
    May 2018 exclusions
    """
    def __init__(self):
        self.chase_visa = models.PaymentMethod.objects.get(name='Chase Freedom Visa')
        self.vacation_dates = [parse_iso_datestring(d) for d in ['2018-05-01', '2018-05-07']]

    def is_exclusion(self, transaction_description: str, for_date: date, amount: int,
                     payment_method: OPTIONAL_PAYMENT_METHOD):
        return payment_method == self.chase_visa and \
            (for_date >= self.vacation_dates[0]) and (for_date <= self.vacation_dates[1])
