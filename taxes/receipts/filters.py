import abc
from datetime import date

from django.db.models import Q

from taxes.receipts import models


class BaseVendorExclusionFilter(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def is_exclusion(self, transaction_description: str, for_date: date, amount: int) -> bool:
        """
        Determine if a transaction should be excluded

        :param transaction_description: string load from the transaction source
        :param for_date: date of transaction
        :param amount: transaction amount in cents
        :return: true to exclude, false otherwise
        """
        pass


class ExclusionConditionFilter(BaseVendorExclusionFilter):
    """
    Filters based on loaded exclusions in the database
    """
    def is_exclusion(self, transaction_description: str, for_date: date, amount: int) -> bool:
        q_pattern = transaction_description.upper()
        return models.ExclusionCondition.objects \
            .filter(
                Q(
                    Q(prefix__isnull=False, prefix__is_prefix_match=q_pattern) &
                    Q(Q(on_date__isnull=True) | Q(on_date=for_date))
                ) |
                Q(prefix__isnull=True, on_date=for_date, amount=amount)
            ).exists()
