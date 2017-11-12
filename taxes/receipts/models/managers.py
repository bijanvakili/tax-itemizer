import datetime
import typing

from django.db import models

from taxes.receipts import constants
from taxes.receipts.forex import CURRENCY_PAIR


DICT_GENERATOR = typing.Generator[dict, None, None]


# TODO convert to generators of named tuples rather than just arbitrary key stringed dictionaries

class ReceiptManager(models.Manager):
    def sorted_report(self, start_date: datetime.date, end_date: datetime.date) -> DICT_GENERATOR:
        receipts = self.get_queryset() \
            .select_related('vendor', 'payment_method') \
            .filter(purchased_at__range=(start_date, end_date)) \
            .order_by('purchased_at', 'vendor__name', 'total_amount')

        for receipt in receipts:
            row = {}
            row['Date'] = receipt.purchased_at.isoformat()

            financial_asset = receipt.vendor.assigned_asset
            row['Source'] = financial_asset.name if financial_asset else ''

            amount_in_cents = f'{receipt.total_amount * 0.01:0.2f}'
            if receipt.currency == constants.Currency.CAD:
                row['Amount (CAD)'] = amount_in_cents
                row['Amount (USD)'] = ''
            else:
                row['Amount (CAD)'] = ''
                row['Amount (USD)'] = amount_in_cents

            row['Transaction Party'] = receipt.vendor.name
            row['Notes'] = ''
            row['CAD/USD rate'] = ''
            row['HST Amount (CAD)'] = ''
            row['Tax Category'] = receipt.vendor.type.label
            row['Payment Method'] = receipt.payment_method.name
            yield row


class ForexRateManager(models.Manager):
    def sorted_report(self, start_date: datetime.date, end_date: datetime.date) -> DICT_GENERATOR:
        rates = self.get_queryset() \
            .filter(pair=CURRENCY_PAIR, effective_at__range=(start_date, end_date)) \
            .order_by('effective_at')
        return (
            {'Date': r.effective_at.isoformat(), 'Rate': str(r.rate)} for r in rates
        )
