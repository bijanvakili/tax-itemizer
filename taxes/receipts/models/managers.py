import abc
import datetime
import typing

from django.db import models

from taxes.receipts.forex import CURRENCY_PAIR


TUPLE_GENERATOR = typing.Generator[typing.NamedTuple, None, None]


class ItemizedReceiptFields(typing.NamedTuple):
    date: str
    asset: str
    currency: str
    amount: str
    transaction_party: str
    hst_amount: str
    tax_category: str
    payment_method: str
    notes: str


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
            financial_asset = receipt.vendor.assigned_asset
            amount_in_cents = f'{receipt.total_amount * 0.01:0.2f}'

            if receipt.hst_amount:
                hst_amount = f'{receipt.hst_amount * 0.01:0.2f}'
            else:
                hst_amount = ''

            yield ItemizedReceiptFields(
                receipt.transaction_date.isoformat(),
                financial_asset.name if financial_asset else '',
                receipt.currency.value,
                amount_in_cents,
                receipt.vendor.name,
                hst_amount,
                receipt.expense_type.label,
                receipt.payment_method.name,
                '',
            )


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
