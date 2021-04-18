"""
Itemization logic
"""
import logging
import typing

from dataclasses import dataclass
from django.conf import settings
from django.db.models.query import Q
import django.core.exceptions as django_exc

from taxes.receipts.filters import load_filters_from_modules
from taxes.receipts import models
from taxes.receipts.types import (
    AliasMatchOperation,
    Currency,
    TransactionType,
    RawTransaction,
    RawTransactionIterable,
)
from taxes.receipts.tax import add_tax_adjustment
from taxes.receipts.util.currency import cents_to_dollars


LOGGER = logging.getLogger(__name__)


@dataclass
class VendorMatch:
    vendor: models.Vendor
    asset: models.FinancialAsset
    expense_type: TransactionType


class Itemizer:
    def __init__(self, filename: str):
        # TODO rename to "_pattern_mismatches"
        self._failures = 0
        self.filename = filename
        self.exclusion_filters = load_filters_from_modules(
            settings.EXCLUSION_FILTER_MODULES
        )

    def _is_excluded(self, transaction: RawTransaction) -> bool:
        return any(f.is_exclusion(transaction) for f in self.exclusion_filters)

    @staticmethod
    def _is_periodic_payment(transaction: RawTransaction):
        misc = transaction.misc
        # TODO extend to inspect payment method
        return (
            misc.get("transaction_code") in ["CD", "IB"]
            and transaction.description == ""
            and transaction.currency == Currency.CAD
        )

    # TODO: Remove once astroid is upgraded past v2.4.2 (and pylint is upgraded too)
    # pylint:disable=unsubscriptable-object
    def _find_vendor(self, transaction: RawTransaction) -> typing.Optional[VendorMatch]:
        amount = transaction.amount
        if self._is_periodic_payment(transaction):
            # TODO determine how to handle regular payments with the same amount and
            # currency
            try:
                periodic_payment = models.PeriodicPayment.objects.get(
                    currency=transaction.currency, amount=amount
                )
            except django_exc.ObjectDoesNotExist:
                self._failures += 1
                LOGGER.warning(
                    "Pattern not found for amount: %.2f", cents_to_dollars(amount)
                )
                return None
            vendor = periodic_payment.vendor
            return VendorMatch(
                vendor=periodic_payment.vendor,
                asset=vendor.default_asset if vendor else None,
                expense_type=periodic_payment.vendor.default_expense_type,
            )

        # locate the vendor by alias
        pattern = transaction.description
        q_pattern = pattern.upper()
        q_ops = AliasMatchOperation
        try:
            vendor_alias = models.VendorAliasPattern.objects.get(
                Q(match_operation=q_ops.EQUAL, pattern=q_pattern)
                | Q(match_operation=q_ops.LIKE, pattern__is_alias_match=q_pattern)
            )
        except django_exc.ObjectDoesNotExist:
            self._failures += 1
            LOGGER.warning("Pattern not found in %s: %s", self.filename, pattern)
            return None

        # prioritize vendor alias's expense type over the vendor's expense type
        vendor = vendor_alias.vendor
        return VendorMatch(
            vendor=vendor,
            asset=vendor_alias.default_asset or vendor.default_asset,
            expense_type=vendor_alias.default_expense_type
            or vendor.default_expense_type,
        )

    # pylint:enable=unsubscriptable-object

    def process_transactions(self, raw_transactions: RawTransactionIterable):
        """
        Itemizes an iterable of transactions
        """
        for raw_transaction in raw_transactions:
            if self._is_excluded(raw_transaction):
                LOGGER.info(
                    "Skipping transaction: %s %d",
                    raw_transaction.description,
                    raw_transaction.amount,
                )
                continue

            # attempt to match the vendor
            total_amount = raw_transaction.amount
            vendor_match = self._find_vendor(raw_transaction)
            if vendor_match:
                vendor = vendor_match.vendor
                asset = vendor_match.asset
                if vendor.fixed_amount:
                    total_amount = vendor.fixed_amount
                    LOGGER.info(
                        "Using fixed amount %d for vendor %s",
                        vendor.fixed_amount,
                        vendor.name,
                    )
            else:
                vendor = None
                asset = None

            transaction = models.Transaction.objects.create(
                vendor=vendor,
                asset=asset,
                transaction_date=raw_transaction.transaction_date,
                transaction_type=vendor_match.expense_type if vendor_match else None,
                payment_method=raw_transaction.payment_method,
                total_amount=total_amount,
                currency=raw_transaction.currency,
                description=vendor.name if vendor else raw_transaction.description,
            )

            # add a tax adjustment if required
            if vendor_match and vendor_match.vendor.tax_adjustment_type:
                add_tax_adjustment(transaction)

    @property
    def failures(self) -> int:
        return self._failures
