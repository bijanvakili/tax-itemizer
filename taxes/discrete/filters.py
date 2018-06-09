from datetime import date
import re

from django.db.models import Q

from taxes.receipts import models
from taxes.receipts.filters import BaseVendorExclusionFilter, OPTIONAL_PAYMENT_METHOD
from taxes.receipts.util.datetime import parse_iso_datestring


class January2018Filter(BaseVendorExclusionFilter):
    def __init__(self):
        self.work_trip_dates = [parse_iso_datestring(d) for d in ['2018-01-28', '2018-01-31']]
        self.filter_payment_method_id = models.PaymentMethod.objects.get(
            name='Chase Freedom Visa'
        ).id

    def is_exclusion(self, transaction_description: str, for_date: date, amount: int,
                     payment_method: OPTIONAL_PAYMENT_METHOD):
        if not payment_method or (payment_method.id != self.filter_payment_method_id):
            return False

        # exclude work trip expenses
        return (for_date >= self.work_trip_dates[0]) and (for_date <= self.work_trip_dates[1])


class February2018Filter(BaseVendorExclusionFilter):
    def __init__(self):
        self.filter_payment_method_ids = models.PaymentMethod.objects\
            .filter(Q(name='Chase Freedom Visa') | Q(name='Wells Fargo Checking'))\
            .values_list('id', flat=True)
        self.filter_transaction_pattern = re.compile(
            r'(?:^THE WESTIN BEACH RESORT.*)|(?:.*TAX.*VAKILI, BIJAN$)'
        )

    def is_exclusion(self, transaction_description: str, for_date: date, amount: int,
                     payment_method: OPTIONAL_PAYMENT_METHOD):
        return payment_method and payment_method.id in self.filter_payment_method_ids and \
            self.filter_transaction_pattern.fullmatch(transaction_description) is not None


class April2018Filter(BaseVendorExclusionFilter):
    def is_exclusion(self, transaction_description: str, for_date: date, amount: int,
                     payment_method: OPTIONAL_PAYMENT_METHOD):
        """ Mis-entered rent check """
        if amount == 111000 and for_date == date(2018, 4, 9):
            return True
        return False


class May2018Filter(BaseVendorExclusionFilter):
    def __init__(self):
        self.chase_visa = models.PaymentMethod.objects.get(name='Chase Freedom Visa')
        self.vacation_dates = [parse_iso_datestring(d) for d in ['2018-05-01', '2018-05-07']]

    def is_exclusion(self, transaction_description: str, for_date: date, amount: int,
                     payment_method: OPTIONAL_PAYMENT_METHOD):
        return payment_method == self.chase_visa and \
            (for_date >= self.vacation_dates[0]) and (for_date <= self.vacation_dates[1])
