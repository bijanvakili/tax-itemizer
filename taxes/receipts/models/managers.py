import abc
import datetime
import typing

from django.db import models

from taxes.receipts.forex import CURRENCY_PAIR
from taxes.receipts.util.csv import receipt_to_itemized_row


TUPLE_GENERATOR = typing.Generator[typing.NamedTuple, None, None]


class ForexRateFields(typing.NamedTuple):
    date: str
    rate: str


class ReportMixinBase(metaclass=abc.ABCMeta):
    @property
    @abc.abstractmethod
    def headers(self):
        pass

    @abc.abstractmethod
    def sorted_report(self, start_date: datetime.date, end_date: datetime.date) -> TUPLE_GENERATOR:
        pass


class ReceiptManager(ReportMixinBase, models.Manager):
    @property
    def headers(self):
        return [
            'Date', 'Asset', 'Currency', 'Amount', 'Transaction Party',
            'HST Amount (CAD)', 'Tax Category', 'Payment Method', 'Notes',
        ]

    def sorted_report(self, start_date: datetime.date, end_date: datetime.date) -> TUPLE_GENERATOR:
        receipts = self.get_queryset() \
            .select_related('vendor', 'vendor__assigned_asset', 'payment_method') \
            .filter(transaction_date__range=(start_date, end_date)) \
            .extra(select={
                'hst_amount': """
                    SELECT SUM(amount)
                    FROM tax_adjustment ta
                    WHERE ta.tax_type = 'hst' AND ta.receipt_id = receipt.id
                """
            }) \
            .order_by('transaction_date', 'vendor__name', 'total_amount')

        for receipt in receipts:
            yield receipt_to_itemized_row(receipt, receipt.hst_amount)


class ForexRateManager(models.Manager):
    @property
    def headers(self):
        return ['Date', 'Rate']

    def sorted_report(self, start_date: datetime.date, end_date: datetime.date) -> TUPLE_GENERATOR:
        rates = self.get_queryset() \
            .filter(pair=CURRENCY_PAIR, effective_at__range=(start_date, end_date)) \
            .order_by('effective_at')
        return (
            ForexRateFields(r.effective_at.isoformat(), str(r.rate)) for r in rates
        )
