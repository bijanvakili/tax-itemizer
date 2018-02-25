import abc
from importlib import import_module
import inspect
from datetime import date
import typing

from django.db.models import Q

from taxes.receipts import models


OPTIONAL_PAYMENT_METHOD = typing.Optional[models.PaymentMethod]


class BaseVendorExclusionFilter(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def is_exclusion(self, transaction_description: str, for_date: date, amount: int,
                     payment_method: OPTIONAL_PAYMENT_METHOD) -> bool:
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
    def is_exclusion(self, transaction_description: str, for_date: date, amount: int,
                     payment_method: OPTIONAL_PAYMENT_METHOD) -> bool:
        # TODO future support to filter on payment_method
        q_pattern = transaction_description.upper()
        return models.ExclusionCondition.objects \
            .filter(
                Q(
                    Q(prefix__isnull=False, prefix__is_prefix_match=q_pattern) &
                    Q(Q(on_date__isnull=True) | Q(on_date=for_date))
                ) |
                Q(prefix__isnull=True, on_date=for_date, amount=amount)
            ).exists()


def load_filters_from_modules(module_paths: typing.Iterable[str]) -> typing.List[BaseVendorExclusionFilter]:
    filters = []

    for module_path in module_paths:
        filter_module = import_module(module_path)
        for name, clz in inspect.getmembers(filter_module):
            if inspect.isclass(clz) and not inspect.isabstract(clz) and issubclass(clz, BaseVendorExclusionFilter):
                filters.append(clz())

    return filters
