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


# TODO refactor into separate M2M model
# currently set to tax aggregation type
@unique
class VendorType(enumfields.Enum):
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


@unique
class AliasMatchOperation(Enum):
    EQUAL = 'equal'
    LIKE = 'like'


@unique
class FinancialAssetType(enumfields.Enum):
    RENTAL = 'rental'
    EMPLOYMENT = 'employment'
    PROPRIETORSHIP = 'proprietorship'

    class Labels:
        RENTAL = 'Rental'
        EMPLOYMENT = 'Employment'
        PROPRIETORSHIP = 'Proprietorship'
