from datetime import date

from taxes.receipts import models
from taxes.receipts.filters import BaseVendorExclusionFilter, OPTIONAL_PAYMENT_METHOD
from taxes.receipts.util.datetime import parse_iso_datestring


# class September2017Filter(BaseVendorExclusionFilter):
#
#     def __init__(self):
#         super().__init__()
#         self.bad_bmo_dates = {parse_iso_datestring(d) for d in ['2017-09-22', '2017-09-25']}
#         self.bad_bmo_amounts = {1237000, 16000000, 62816}
#
#     def is_exclusion(self, transaction_description: str, for_date: date, amount: int):
#         return for_date in self.bad_bmo_dates and abs(amount) in self.bad_bmo_amounts


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
