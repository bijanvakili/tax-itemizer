from enum import Enum, unique
import enumfields


@unique
class PaymentMethod(enumfields.Enum):
    CASH = 'cash'
    CREDIT_CARD = 'credit_card'

    class Labels:
        CASH = 'Cash'
        CREDIT_CARD = 'Credit Card'


@unique
class Currency(Enum):
    USD = 'USD'
    CAD = 'CAD'


CASH_UNIQUE_IDENTIFIER = 'CASH'


# taxable expense aggregation type
@unique
class ExpenseType(enumfields.Enum):
    IGNORE = 'ignore'
    PROPERTY_TAX = 'property_tax'
    INTEREST = 'interest'
    INSURANCE = 'insurance'
    UTILITY = 'utility'
    ADMINISTRATIVE = 'administrative'
    MAINTENANCE = 'maintenance'
    TRAVEL = 'travel'
    MEALS_AND_ENTERTAINMENT = 'meals'
    SUPPLIES = 'supplies'
    RENT = 'rent'
    FOREIGN_INCOME = 'foreign_income'
    CAPITAL_GAINS = 'capital_gains'
    ADVERTISING = 'advertising'
    DONATION = 'donation'

    class Labels:
        IGNORE = '*IGNORE*'
        PROPERTY_TAX = 'Property Tax'
        INTEREST = 'Interest'
        INSURANCE = 'Insurance'
        UTILITY = 'Telephone and Utilities'
        ADMINISTRATIVE = 'Management and Administrative'
        MAINTENANCE = 'Repair and Maintenance'
        TRAVEL = 'Business Travel'
        MEALS_AND_ENTERTAINMENT = 'Meals and Entertainment'
        SUPPLIES = 'Office Supplies'
        RENT = 'Gross Rent'
        FOREIGN_INCOME = 'Foreign Income'
        CAPITAL_GAINS = 'Capital Gains'
        ADVERTISING = 'Advertising'
        DONATION = 'Donations'


@unique
class AliasMatchOperation(Enum):
    EQUAL = 'equal'
    LIKE = 'like'


@unique
class FinancialAssetType(enumfields.Enum):
    RENTAL = 'rental'
    EMPLOYMENT = 'employment'
    PROPRIETORSHIP = 'proprietorship'
    PRIMARY_RESIDENCE = 'primary_residence'

    class Labels:
        RENTAL = 'Rental'
        EMPLOYMENT = 'Employment'
        PROPRIETORSHIP = 'Proprietorship'
        PRIMARY_RESIDENCE = 'Primary Residence'


@unique
class TaxType(enumfields.Enum):
    HST = 'hst'
