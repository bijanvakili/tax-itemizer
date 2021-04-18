import abc
import datetime
import typing

from django.db import models

from taxes.receipts.constants import UNKNOWN_VALUE
from taxes.receipts.forex import CURRENCY_PAIR
from taxes.receipts.types import ProcessedTransactionRow, TransactionType
from taxes.receipts.util.currency import cents_to_dollars


TupleGenerator = typing.Generator[typing.NamedTuple, None, None]


# TODO: Remove once astroid is upgraded past v2.4.2
# pylint:disable=inherit-non-class
class ForexRateFields(typing.NamedTuple):
    date: str
    rate: str


# pylint:enable=inherit-non-class


class ReportMixinBase(metaclass=abc.ABCMeta):
    @property
    @abc.abstractmethod
    def headers(self):
        pass

    @abc.abstractmethod
    def sorted_report(
        self, start_date: datetime.date, end_date: datetime.date
    ) -> TupleGenerator:
        pass


class TransactionManager(ReportMixinBase, models.Manager):
    @property
    def headers(self):
        return [
            "Date",
            "Asset",
            "Currency",
            "Amount",
            "Transaction Party",
            "HST Amount (CAD)",
            "Tax Category",
            "Payment Method",
            "Notes",
        ]

    def sorted_report(
        self, start_date: datetime.date, end_date: datetime.date
    ) -> TupleGenerator:
        transactions = (
            self.get_queryset()
            .select_related("payment_method")
            .filter(transaction_date__range=(start_date, end_date))
            .extra(
                select={
                    "hst_amount": """
                    SELECT SUM(amount)
                    FROM tax_adjustment ta
                    WHERE ta.tax_type = 'hst' AND ta.receipt_id = receipt.id
                """
                }
            )
            .order_by("transaction_date", "description", "total_amount")
        )

        for transaction in transactions:
            asset = transaction.asset

            yield ProcessedTransactionRow(
                transaction.transaction_date.isoformat(),
                asset.name if asset else UNKNOWN_VALUE,
                transaction.currency,
                cents_to_dollars(transaction.total_amount),
                transaction.description,
                cents_to_dollars(transaction.hst_amount)
                if transaction.hst_amount
                else "",
                TransactionType(transaction.transaction_type).label
                if transaction.transaction_type
                else UNKNOWN_VALUE,
                transaction.payment_method.name,
                "",
            )


class ForexRateManager(models.Manager):
    @property
    def headers(self):
        return ["Date", "Rate"]

    def sorted_report(
        self, start_date: datetime.date, end_date: datetime.date
    ) -> TupleGenerator:
        rates = (
            self.get_queryset()
            .filter(pair=CURRENCY_PAIR, effective_at__range=(start_date, end_date))
            .order_by("effective_at")
        )
        return (ForexRateFields(r.effective_at.isoformat(), str(r.rate)) for r in rates)
