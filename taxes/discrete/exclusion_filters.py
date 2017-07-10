from datetime import date

from taxes.receipts.filters import BaseVendorExclusionFilter
from taxes.receipts.util.datetime import parse_iso_datestring


# TODO refactor to register all filters via a base class and only have the module added to the config file
class June2017Filter(BaseVendorExclusionFilter):
    EXCLUDE_DATE_RANGE = ('2017-06-07', '2017-06-12')

    def __init__(self):
        super().__init__()
        self.exclude_min, self.exclude_max = (
            parse_iso_datestring(d) for d in self.EXCLUDE_DATE_RANGE
        )

    def is_exclusion(self, transaction_description: str, for_date: date, amount: int):
        if for_date >= self.exclude_min and for_date <= self.exclude_max:
            if 'INTERACTIVE BROK ACH TRANSF' in transaction_description:
                return True

        return False
