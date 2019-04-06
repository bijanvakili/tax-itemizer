"""
Itemization logic
"""
import csv
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
    ExpenseType,
    Transaction,
    TRANSACTION_ITERABLE,
)
from taxes.receipts.tax import add_tax_adjustment
from taxes.receipts.util.currency import cents_to_dollars
from taxes.receipts.util.csv import receipt_to_itemized_row, transaction_to_itemized_row


LOGGER = logging.getLogger(__name__)


@dataclass
class VendorMatch:
    vendor: models.Vendor
    expense_type: ExpenseType


class Itemizer:

    def __init__(self, filename: str):
        self._failures = 0
        self.filename = filename
        self.exclusion_filters = load_filters_from_modules(settings.EXCLUSION_FILTER_MODULES)

    def _is_excluded(self, transaction: Transaction) -> bool:
        return any(f.is_exclusion(transaction) for f in self.exclusion_filters)

    @staticmethod
    def _add_new_receipt(vendor_match: VendorMatch, transaction: Transaction):
        vendor = vendor_match.vendor
        if vendor.fixed_amount:
            total_amount = vendor.fixed_amount
            LOGGER.info(f'Using fixed amount {vendor.fixed_amount} for vendor {vendor.name}')
        else:
            total_amount = transaction.amount

        receipt = models.Receipt.objects.create(
            vendor=vendor,
            transaction_date=transaction.transaction_date,
            expense_type=vendor_match.expense_type,
            payment_method=transaction.payment_method,
            total_amount=total_amount,
            currency=transaction.currency
        )
        return receipt

    @staticmethod
    def _is_periodic_payment(transaction: Transaction):
        misc = transaction.misc
        # TODO extend to inspect payment method
        return \
            misc.get('transaction_code') == 'CD' and \
            transaction.description == '' and \
            transaction.currency == Currency.CAD

    def _find_vendor(self, transaction) -> typing.Optional[VendorMatch]:
        amount = transaction.amount
        # TODO check exclusion conditions
        # if self._is_exclusion(pattern, for_date, amount):
        #     LOGGER.warning(f'Skipped vendor {pattern}')
        #     return None

        if self._is_periodic_payment(transaction):
            # TODO determine how to handle regular payments with the same amount and currency
            try:
                periodic_payment = models.PeriodicPayment.objects.get(
                    currency=transaction.currency,
                    amount=amount
                )
            except django_exc.ObjectDoesNotExist:
                self._failures += 1
                LOGGER.error(f'Pattern not found for amount: {cents_to_dollars(amount)}')
                return None
            return VendorMatch(
                vendor=periodic_payment.vendor,
                expense_type=periodic_payment.vendor.default_expense_type,
            )

        # locate the vendor by alias
        pattern = transaction.description
        q_pattern = pattern.upper()
        q_ops = AliasMatchOperation
        try:
            vendor_alias = models.VendorAliasPattern.objects.get(
                Q(match_operation=q_ops.EQUAL, pattern=q_pattern) |
                Q(match_operation=q_ops.LIKE, pattern__is_alias_match=q_pattern)
            )
        except django_exc.ObjectDoesNotExist:
            self._failures += 1
            LOGGER.error(f'Pattern not found in {self.filename}: {pattern}')
            return None

        # prioritize vendor alias's expense type over the vendor's expense type
        vendor = vendor_alias.vendor
        return VendorMatch(
            vendor=vendor,
            expense_type=vendor_alias.default_expense_type or vendor.default_expense_type
        )

    def process_transactions(self, transactions: TRANSACTION_ITERABLE, csv_outputfile=None):
        """
        Itemizes an iterable of transactions
        """
        if csv_outputfile:
            csv_writer = csv.writer(csv_outputfile)
        else:
            csv_writer = None

        for transaction in transactions:
            if self._is_excluded(transaction):
                LOGGER.warning('Skipping transaction: %s %d',
                               transaction.description, transaction.amount)
                continue

            # attemp to match the vendor
            vendor_match = self._find_vendor(transaction)
            hst_amount = None
            receipt = None
            if vendor_match:
                receipt = self._add_new_receipt(vendor_match, transaction)
                # add a tax adjustment if required
                if vendor_match.vendor.tax_adjustment_type:
                    adjustment = add_tax_adjustment(receipt)
                    hst_amount = adjustment.amount

            if csv_writer:
                if receipt:
                    csv_writer.writerow(receipt_to_itemized_row(receipt, hst_amount))
                else:
                    csv_writer.writerow(transaction_to_itemized_row(transaction))

    @property
    def failures(self) -> int:
        return self._failures
