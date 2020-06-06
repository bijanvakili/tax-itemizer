from datetime import date
from enum import Enum, unique
import typing

from dataclasses import dataclass
from django.db.models import TextChoices
import enumfields


@unique
class PaymentMethodEnum(enumfields.Enum):
    CASH = "cash"
    CREDIT_CARD = "credit_card"

    class Labels:
        CASH = "Cash"
        CREDIT_CARD = "Credit Card"


class PaymentMethod(TextChoices):
    CASH = "cash", "Cash"
    CREDIT_CARD = "credit_card", "Credit Card"


@unique
class CurrencyEnum(Enum):
    USD = "USD"
    CAD = "CAD"


class Currency(TextChoices):
    USD = "USD", "USD"
    CAD = "CAD", "CAD"


# taxable expense aggregation type
@unique
class ExpenseTypeEnum(enumfields.Enum):
    IGNORE = "ignore"
    PROPERTY_TAX = "property_tax"
    INTEREST = "interest"
    INSURANCE = "insurance"
    UTILITY = "utility"
    ADMINISTRATIVE = "administrative"
    MAINTENANCE = "maintenance"
    TRAVEL = "travel"
    MEALS_AND_ENTERTAINMENT = "meals"
    SUPPLIES = "supplies"
    RENT = "rent"
    FOREIGN_INCOME = "foreign_income"
    CAPITAL_GAINS = "capital_gains"
    ADVERTISING = "advertising"
    DONATION = "donation"

    class Labels:
        IGNORE = "*IGNORE*"
        PROPERTY_TAX = "Property Tax"
        INTEREST = "Interest"
        INSURANCE = "Insurance"
        UTILITY = "Telephone and Utilities"
        ADMINISTRATIVE = "Management and Administrative"
        MAINTENANCE = "Repair and Maintenance"
        TRAVEL = "Business Travel"
        MEALS_AND_ENTERTAINMENT = "Meals and Entertainment"
        SUPPLIES = "Office Supplies"
        RENT = "Gross Rent"
        FOREIGN_INCOME = "Foreign Income"
        CAPITAL_GAINS = "Capital Gains"
        ADVERTISING = "Advertising"
        DONATION = "Donations"


class ExpenseType(TextChoices):
    IGNORE = "ignore", "*IGNORE*"
    PROPERTY_TAX = "property_tax", "Property Tax"
    INTEREST = "interest", "Interest"
    INSURANCE = "insurance", "Insurance"
    UTILITY = "utility", "Telephone and Utilities"
    ADMINISTRATIVE = "administrative", "Management and Administrative"
    MAINTENANCE = "maintenance", "Repair and Maintenance"
    TRAVEL = "travel", "Business Travel"
    MEALS_AND_ENTERTAINMENT = "meals", "Meals and Entertainment"
    SUPPLIES = "supplies", "Office Supplies"
    RENT = "rent", "Gross Rent"
    FOREIGN_INCOME = "foreign_income", "Foreign Income"
    CAPITAL_GAINS = "capital_gains", "Capital Gains"
    ADVERTISING = "advertising", "Advertising"
    DONATION = "donation", "Donations"


@unique
class AliasMatchOperationEnum(Enum):
    EQUAL = "equal"
    LIKE = "like"


class AliasMatchOperation(TextChoices):
    EQUAL = "equal"
    LIKE = "like"


@unique
class FinancialAssetTypeEnum(enumfields.Enum):
    RENTAL = "rental"
    EMPLOYMENT = "employment"
    PROPRIETORSHIP = "proprietorship"
    PRIMARY_RESIDENCE = "primary_residence"

    class Labels:
        RENTAL = "Rental"
        EMPLOYMENT = "Employment"
        PROPRIETORSHIP = "Proprietorship"
        PRIMARY_RESIDENCE = "Primary Residence"


class FinancialAssetType(TextChoices):
    RENTAL = "rental", "Rental"
    EMPLOYMENT = "employment", "Employment"
    PROPRIETORSHIP = "proprietorship", "Proprietorship"
    PRIMARY_RESIDENCE = "primary_residence", "Primary Residence"


@unique
class TaxTypeEnum(enumfields.Enum):
    HST = "hst"


class TaxType(TextChoices):
    HST = "hst", "HST"


@dataclass
class RawTransaction:
    """
    Represents a parsed transaction
    """

    line_number: int
    transaction_date: date
    amount: int
    currency: CurrencyEnum
    description: str = None
    misc: dict = None
    payment_method: PaymentMethodEnum = None


class ProcessedTransactionRow(typing.NamedTuple):
    """
    Fields to output in CSV format for an processed transaction
    """

    date: str
    asset: str
    currency: str
    amount: str
    transaction_party: str
    hst_amount: str
    tax_category: str
    payment_method: str
    notes: str


RawTransactionSequence = typing.Sequence[RawTransaction]
RawTransactionIterable = typing.Iterable[RawTransaction]
RawTransactinGenerator = typing.Generator[RawTransaction, None, None]
TextLineGenerator = typing.Generator[str, None, None]
