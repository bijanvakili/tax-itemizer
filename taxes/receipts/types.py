from datetime import date
import typing

from dataclasses import dataclass
from django.db.models import TextChoices


class PaymentMethod(TextChoices):
    CASH = "cash", "Cash"
    CREDIT_CARD = "credit_card", "Credit Card"


class Currency(TextChoices):
    USD = "USD", "USD"
    CAD = "CAD", "CAD"


# taxable expense aggregation type
class ExpenseType(TextChoices):
    IGNORE = "ignore", "*IGNORE*"

    ADMINISTRATIVE = "administrative", "Management and Administrative"
    ADVERTISING = "advertising", "Advertising"
    CAPITAL_GAINS = "capital_gains", "Capital Gains"
    DONATION = "donation", "Donations"
    FOREIGN_INCOME = "foreign_income", "Foreign Income"
    HOA_FEES = "hoa_fees", "HOA Fees"
    INTEREST = "interest", "Interest"
    INSURANCE = "insurance", "Insurance"
    MAINTENANCE = "maintenance", "Repair and Maintenance"
    MEALS = "meals", "Meals"
    PROPERTY_TAX = "property_tax", "Property Tax"
    RENT = "rent", "Gross Rent"
    SUPPLIES = "supplies", "Office Supplies"
    TELEPHONE = "telephone", "Telephone"
    TRAVEL = "travel", "Business Travel"
    UTILITY = "utility", "Utilities"


class AliasMatchOperation(TextChoices):
    EQUAL = "equal"
    LIKE = "like"


class FinancialAssetType(TextChoices):
    RENTAL = "rental", "Rental"
    EMPLOYMENT = "employment", "Employment"
    PROPRIETORSHIP = "proprietorship", "Proprietorship"
    PRIMARY_RESIDENCE = "primary_residence", "Primary Residence"


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
    currency: Currency
    description: str = None
    misc: dict = None
    payment_method: PaymentMethod = None


# TODO: Remove once astroid is upgraded past v2.4.2
# pylint:disable=inherit-non-class
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


# pylint:enable=inherit-non-class


RawTransactionSequence = typing.Sequence[RawTransaction]
RawTransactionIterable = typing.Iterable[RawTransaction]
RawTransactinGenerator = typing.Generator[RawTransaction, None, None]
TextLineGenerator = typing.Generator[str, None, None]
