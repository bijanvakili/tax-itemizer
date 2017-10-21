from datetime import date
import re

from taxes.receipts.filters import BaseVendorExclusionFilter
from taxes.receipts.util.datetime import parse_iso_datestring


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


class September2017Filter(BaseVendorExclusionFilter):

    def __init__(self):
        super().__init__()
        self.bad_bmo_dates = {parse_iso_datestring(d) for d in ['2017-09-22', '2017-09-25']}
        self.bad_bmo_amounts = {1237000, 16000000, 62816}

    def is_exclusion(self, transaction_description: str, for_date: date, amount: int):
        return for_date in self.bad_bmo_dates and abs(amount) in self.bad_bmo_amounts
