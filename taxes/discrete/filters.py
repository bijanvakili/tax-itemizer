from datetime import date
import re

from taxes.receipts.filters import BaseVendorExclusionFilter
from taxes.receipts.util.datetime import parse_iso_datestring


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


class August2017Filter(BaseVendorExclusionFilter):

    OUTSIDE_LAND_PATTERNS = [
        r'OUTSIDE LANDS',
        r"SAN FRANCISCO'{0,1}S OUTSI"
    ]

    def __init__(self):
        super().__init__()
        self.exclusion_regexes = [re.compile(p) for p in self.OUTSIDE_LAND_PATTERNS]

    def is_exclusion(self, transaction_description: str, for_date: date, amount: int):
        return transaction_description and any(r.search(transaction_description) for r in self.exclusion_regexes)
