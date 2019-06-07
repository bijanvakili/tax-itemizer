"""
Filters to exclude transactions
"""
import abc
import inspect
import re
import typing
from importlib import import_module

from django.db.models import Q

from taxes.receipts import models
from taxes.receipts.types import RawTransaction


class BaseVendorExclusionFilter(metaclass=abc.ABCMeta):
    def is_exclusion(self, transaction: RawTransaction) -> bool:
        """
        Determine if a transaction should be excluded

        :param transaction_description: string load from the transaction source
        :param for_date: date of transaction
        :param amount: transaction amount in cents
        :param payment_method: (optional) payment method instance (if known)
        :return: true to exclude, false otherwise
        """
        pass


class ExclusionConditionFilter(BaseVendorExclusionFilter):
    """
    Filters based on loaded exclusions in the database
    """
    def is_exclusion(self, transaction: RawTransaction) -> bool:
        # TODO future support to filter on payment_method
        q_pattern = transaction.description.upper()
        for_date = transaction.transaction_date
        return models.ExclusionCondition.objects \
            .filter(
                Q(
                    Q(prefix__isnull=False, prefix__is_prefix_match=q_pattern) &
                    Q(Q(on_date__isnull=True) | Q(on_date=for_date))
                ) |
                Q(prefix__isnull=True, on_date=for_date, amount=transaction.amount)
            ).exists()


class BMOTransactionCodeFilter(BaseVendorExclusionFilter):
    """
    Filters out specific BMO transactions
    """
    EXCLUDED_TRANSACTION_CODES = {'SO', 'SC', 'CW'}

    def is_exclusion(self, transaction: RawTransaction) -> bool:
        transaction_code = transaction.misc.get('transaction_code')
        return transaction_code and transaction_code in self.EXCLUDED_TRANSACTION_CODES


class CreditPaymentFilter(BaseVendorExclusionFilter):
    """
    Filters out credit payments depending on payment method
    """
    PAYMENT_DESCRIPTIONS = {
        'PAYMENT RECEIVED - THANK YOU',
        'AUTOMATIC PAYMENT RECEIVED - THANK YOU',
        'ONLINE PAYMENT',
        'PAYMENT'
    }

    def is_exclusion(self, transaction: RawTransaction) -> bool:
        return transaction.misc.get('category') == 'Payment' or \
            transaction.misc.get('type') == 'Payment' or \
            transaction.description.upper() in self.PAYMENT_DESCRIPTIONS


class CRAPaymentFilter(BaseVendorExclusionFilter):
    """
    Filtesr out CRA withholding tax payments
    """
    def is_exclusion(self, transaction: RawTransaction) -> bool:
        return transaction.payment_method.name == 'BMO Savings' and \
            re.search(
                r'^ONLINE PURCHASE\s.*PAY\s+TO\s+CRA',
                transaction.description.upper()
            ) is not None


class WellsFargoOnlinePaymentFilter(BaseVendorExclusionFilter):
    def is_exclusion(self, transaction: RawTransaction) -> bool:
        return transaction.payment_method.name == 'Wells Fargo Checking' and \
            re.search(
                r'^(ONLINE TRANSFER REF|BILL PAY)\s.+ON\s.+$',
                transaction.description.upper()
            ) is not None


def load_filters_from_modules(module_paths: typing.Iterable[str]) -> \
        typing.List[BaseVendorExclusionFilter]:
    filters = []

    for module_path in module_paths:
        filter_module = import_module(module_path)
        for _, clz in inspect.getmembers(filter_module):
            if inspect.isclass(clz) and not inspect.isabstract(clz) and\
                    issubclass(clz, BaseVendorExclusionFilter):
                filters.append(clz())

    return filters
