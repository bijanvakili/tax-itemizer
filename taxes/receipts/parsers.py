import abc
import csv
import logging
import os
import re
from enum import Enum
from functools import lru_cache

from django.conf import settings
from django.db.models.query import Q
import django.core.exceptions as django_exc

from taxes.receipts import models, constants
from taxes.receipts.util.datetime import parse_date
from taxes.receipts.util.currency import parse_amount, cents_to_dollars
from taxes.receipts.filters import load_filters_from_modules

LOGGER = logging.getLogger(__name__)


class ParseException(Exception):
    def __init__(self, *args, line_number=None, **kwargs):
        self.line_number = line_number
        super().__init__(*args, **kwargs)

    def __repr__(self):
        prefix = '{} '.format(self.line_number) if self.line_number else ''
        return prefix + super().__repr__()


class TextFileFilter(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def is_accepted(self, line):
        pass


class NonEmptyLinesFilter(TextFileFilter):
    def is_accepted(self, line):
        return line.strip() != ''


class FileIterator(object):
    def __init__(self, file, filters):
        self.file = file
        self.filters = filters or []

    def __iter__(self):
        for line in self.file.readlines():
            if all((f.is_accepted(line) for f in self.filters)):
                yield line


class SkipPatternsFilter(TextFileFilter):
    def __init__(self, patterns):
        self.patterns = [re.compile(pattern) for pattern in patterns]

    def is_accepted(self, line):
        for pattern in self.patterns:
            if pattern.match(line):
                return False
        return True


# TODO remap dict keys in base class
class BaseParser(metaclass=abc.ABCMeta):
    CSV_FIELDS = None
    CSV_QUOTECHAR = '"'
    FIXED_PAYMENT_METHOD_NAME = None
    SKIP_HEADER = True

    def __init__(self):
        self.failures = 0
        self.fixed_payment_method = None
        self.exclusion_filters = load_filters_from_modules(settings.EXCLUSION_FILTER_MODULES)

    def parse(self, filename):
        # set the fixed card number if the class specifies it
        if self.FIXED_PAYMENT_METHOD_NAME:
            self.fixed_payment_method = models.PaymentMethod.objects.get(name=self.FIXED_PAYMENT_METHOD_NAME)

        self.failures = 0
        with open(filename, 'r') as f:
            file_iterator = FileIterator(f, self.filters)
            reader = csv.DictReader(
                file_iterator,
                fieldnames=self.CSV_FIELDS,
                quotechar=self.CSV_QUOTECHAR
            )
            for line_number, row in enumerate(reader):
                # skip header
                if self.SKIP_HEADER and line_number == 0:
                    continue
                LOGGER.debug('CSV Line - {}'.format(line_number))
                try:
                    self.parse_row(row, line_number)
                except:
                    LOGGER.error('FAILURE on line {} of file {}'.format(line_number + 1, filename))
                    raise

    @property
    def filters(self):
        return []

    @abc.abstractmethod
    def parse_row(self, row: dict, line_number: int):
        """
        :param row: current row parsed from CSV
        :param line_number: zero-based integer line number
        """
        pass

    @lru_cache(maxsize=8)
    def _get_payment_method(self, card_number):
        # TODO determine how to handle different cards with the same last 4 digits
        last_4_digits = card_number[-4:]
        return models.PaymentMethod.objects.get(safe_numeric_id=last_4_digits)

    def _add_new_receipt(self, vendor, purchased_at, payment_method, total_amount, currency):
        if vendor.fixed_amount:
            total_amount = vendor.fixed_amount
            LOGGER.info(
                'Using fixed amount {} for vendor {}'.format(vendor.fixed_amount, vendor.name)
            )

        models.Receipt.objects.create(
            vendor=vendor,
            purchased_at=purchased_at,
            payment_method=payment_method,
            total_amount=total_amount,
            currency=currency
        )

    def _is_exclusion(self, pattern, for_date, amount):
        return any(f.is_exclusion(pattern, for_date, amount) for f in self.exclusion_filters)

    def _find_vendor(self, pattern, for_date, amount):
        # check exclusion conditions
        if self._is_exclusion(pattern, for_date, amount):
            LOGGER.warning('Skipped vendor {}'.format(pattern))
            return None

        # locate the vendor by alias
        q_pattern = pattern.upper()
        q_ops = constants.AliasMatchOperation
        try:
            vendor_alias = models.VendorAliasPattern.objects.get(
                Q(match_operation=q_ops.EQUAL, pattern=q_pattern) |
                Q(match_operation=q_ops.LIKE, pattern__is_alias_match=q_pattern)
            )
        except django_exc.ObjectDoesNotExist:
            self.failures += 1
            LOGGER.error('Pattern not found: {}'.format(pattern))
            return None
        return vendor_alias.vendor


class BaseBMOCSVParser(BaseParser):
    DATE_FORMAT = '%Y%m%d'
    CSV_QUOTECHAR = "'"

    @property
    def filters(self):
        return [
            NonEmptyLinesFilter(),
            SkipPatternsFilter(['^Following data is valid as of.*'])
        ]


class BMOTransactionCode(Enum):
    """
    https://www.bmo.com/olb/help-centre/en/my-accounts/
    """
    SERVICE_CHARGEABLE = 'DS'
    CHECK_DEPOSIT = 'CD'
    ONLINE_BANKING = 'CW'
    STANDARD_ORDER = 'SO'
    SERVICE_CHARGE = 'SC'
    NOT_SERVICE_CHARGEABLE = 'DN'
    INSTABANK = 'IB'
    INTEREST = 'IN'
    ONLINE_DEBIT_PURCHASE = 'OL'
    MULTI_BRANCH_BANKING = 'MB'
    RETURNED_ITEM = 'RT'
    TRANSFER_OF_FUNDS = 'TF'
    FOREIGN_EXCHANGE = 'FX'
    WITHDRAWAL = 'WD'
    CREDIT_MEMO = 'CM'
    DEBIT_MEMO = 'DM'


class BMOBankAccountParser(BaseBMOCSVParser):
    CSV_FIELDS = ['card_number', 'type', 'date', 'amount', 'party']
    VALID_CHARGE_CODES = {
        BMOTransactionCode.SERVICE_CHARGEABLE,
        BMOTransactionCode.NOT_SERVICE_CHARGEABLE,
        BMOTransactionCode.ONLINE_DEBIT_PURCHASE,
        BMOTransactionCode.MULTI_BRANCH_BANKING,
        BMOTransactionCode.FOREIGN_EXCHANGE,
    }

    def __init__(self):
        super().__init__()
        self.party_parser = re.compile('^\[([A-Z]{2})\](.*)$')

    def _find_vendor_from_amount(self, for_date, amount):
        if self._is_exclusion('', for_date, amount):
            LOGGER.warn('Skipping amount: {}'.format(amount))
            return None

        # TODO determine how to handle regular payments with the same amount and currency
        try:
            periodic_payment = models.PeriodicPayment.objects.get(
                currency=constants.Currency.CAD,
                amount=amount
            )
        except django_exc.ObjectDoesNotExist:
            self.failures += 1
            LOGGER.error('Pattern not for amount: {}'.format(cents_to_dollars(amount)))
            return None

        return periodic_payment.vendor

    def parse_row(self, row, line_number):
        # determine the vendor
        payment_method = self._get_payment_method(row['card_number'])

        # parse the description to determine the vendor
        match = self.party_parser.search(row['party'])
        if not match:
            raise ParseException('Unable to parse line', line_number=line_number)
        tx_code_string, merchant_description = match.groups()
        tx_code = BMOTransactionCode(tx_code_string)
        merchant_description = merchant_description.strip()

        amount = parse_amount(row['amount'])
        receipt_date = parse_date(row['date'], self.DATE_FORMAT)

        if tx_code == BMOTransactionCode.CHECK_DEPOSIT:
            vendor = self._find_vendor_from_amount(receipt_date, amount)
            if not vendor:
                return
        elif tx_code in self.VALID_CHARGE_CODES:
            vendor = self._find_vendor(merchant_description, receipt_date, amount)
            if not vendor:
                return
        else:
            LOGGER.info(
                'Skipping {} transaction for {}...'.format(
                    tx_code,
                    merchant_description
                )
            )
            return

        self._add_new_receipt(vendor, receipt_date, payment_method, amount, constants.Currency.CAD)


class BMOCreditParser(BaseBMOCSVParser):
    CSV_FIELDS = ['item_number', 'card_number', 'transaction_date',
                  'posting_date', 'amount', 'party']

    def parse_row(self, row, line_number):
        payment_method = self._get_payment_method(row['card_number'])
        vendor_description = row['party']

        # all postive values are debited as expenses
        amount = -1 * parse_amount(row['amount'])

        if 'PAYMENT RECEIVED - THANK YOU' in vendor_description and amount >= 0:
            return

        receipt_date = parse_date(row['transaction_date'], self.DATE_FORMAT)
        vendor = self._find_vendor(vendor_description, receipt_date, amount)
        if not vendor:
            return

        self._add_new_receipt(vendor, receipt_date, payment_method, amount, constants.Currency.CAD)


class USDateFormatMixin(object):
    DATE_FORMAT = '%m/%d/%Y'


class CapitalOneParser(BaseParser):
    DATE_FORMAT = '%m/%d/%Y'
    CSV_FIELDS = ['stage', 'transaction_date', 'posted_date', 'card_number', 'description',
                  'category', 'debit', 'credit']
    PAYMENT_DESCRIPTIONS = {'Payment', 'Payment/Credit'}

    def parse_row(self, row, line_number):
        if row['category'] in self.PAYMENT_DESCRIPTIONS:
            LOGGER.info(
                'Skipping payment {transaction_date} {card_number} {description}'.format(**row)
            )
            return

        payment_method = self._get_payment_method(row['card_number'])
        vendor_description = row['description']
        receipt_date = parse_date(row['transaction_date'], self.DATE_FORMAT)
        debit_amount = parse_amount(row['debit'] or '0.0')
        credit_amount = parse_amount(row['credit'] or '0.0')
        amount = credit_amount - debit_amount
        vendor = self._find_vendor(vendor_description, receipt_date, amount)
        if not vendor:
            return

        self._add_new_receipt(vendor, receipt_date, payment_method,
                              amount, constants.Currency.USD)


class MBNAMastercardParser(BaseParser, USDateFormatMixin):
    CSV_FIELDS = ['posted_date', 'payee', 'address', 'amount']
    FIXED_PAYMENT_METHOD_NAME = 'MBNA Mastercard'

    def parse_row(self, row, line_number):
        if row['payee'].upper() == 'PAYMENT':
            LOGGER.info('Skipping payment {posted_date}...'.format(**row))
            return

        vendor_description = row['payee']
        receipt_date = parse_date(row['posted_date'], self.DATE_FORMAT)
        amount = parse_amount(row['amount'])
        vendor = self._find_vendor(vendor_description, receipt_date, amount)
        if not vendor:
            return

        self._add_new_receipt(vendor, receipt_date, self.fixed_payment_method,
                              amount, constants.Currency.CAD)


class BaseWellsFargoParser(BaseParser, USDateFormatMixin):
    CSV_FIELDS = ['transaction_date', 'amount', 'unknown_0', 'check_number', 'party']
    SKIP_HEADER = False
    PREFIXES_TO_SKIP = [
        'ATM WITHDRAWAL AUTHORIZED',
        'BILL PAY',
        'CASH EWITHDRAWAL',
        'DEPOSITED OR CASHED CHECK',
        'ONLINE TRANSFER',
        'ONLINE PAYMENT'
    ]

    def __init__(self):
        super().__init__()
        self.authorized_purchase_pattern = re.compile('^PURCHASE AUTHORIZED ON \d{2}/\d{2} (?P<party>.+)$')

    def parse_row(self, row, line_number):
        # skip checks
        if row['check_number']:
            LOGGER.info('Skipping check #{check_number}...'.format(**row))
            return

        party = row['party'].upper()

        # extract real payee if preauthorized payment
        preauthorized_match = self.authorized_purchase_pattern.match(party)
        if preauthorized_match:
            party = preauthorized_match.group('party')

        # skip common transactions
        for prefix in WellFargoCheckingParser.PREFIXES_TO_SKIP:
            if party.startswith(prefix):
                LOGGER.info('Skipping transaction: {party}...'.format(**row))
                return

        receipt_date = parse_date(row['transaction_date'], self.DATE_FORMAT)
        amount = parse_amount(row['amount'])
        vendor = self._find_vendor(party, receipt_date, amount)
        if not vendor:
            return

        self._add_new_receipt(vendor, receipt_date, self.fixed_payment_method,
                              amount, constants.Currency.USD)


class WellFargoCheckingParser(BaseWellsFargoParser):
    FIXED_PAYMENT_METHOD_NAME = 'Wells Fargo Checking'


class WellsFargoVisaParser(BaseWellsFargoParser):
    FIXED_PAYMENT_METHOD_NAME = 'Wells Fargo Visa Card'


class ChaseVisaParser(BaseParser, USDateFormatMixin):
    FIXED_PAYMENT_METHOD_NAME = 'Chase Freedom Visa'
    CSV_FIELDS = ['type', 'transaction_date', 'posted_date', 'party', 'amount', 'category', 'memo']

    # NOTE: The Chase Online 'Download transactions' feature has a known bug where it fails to quote
    # the 'category' and 'memo' columns.  These fields can contain commas.

    def parse_row(self, row, line_number):
        # skip non-sale transactions
        if row['type'].upper() != 'SALE':
            LOGGER.info('Skipping {type}: {party}...'.format(**row))
            return

        party = row['party'].upper()
        receipt_date = parse_date(row['transaction_date'], self.DATE_FORMAT)
        amount = parse_amount(row['amount'])
        vendor = self._find_vendor(party, receipt_date, amount)
        if not vendor:
            return

        self._add_new_receipt(vendor, receipt_date, self.fixed_payment_method,
                              amount, constants.Currency.USD)


PARSER_MAP = [
    # (filename_prefix, parser_class)
    ('bmo_savings', BMOBankAccountParser),
    ('bmo_premium', BMOBankAccountParser),
    ('bmo_mastercard', BMOCreditParser),
    ('bmo_readiline', BMOCreditParser),
    ('capitalone', CapitalOneParser),
    ('mbna_mastercard', MBNAMastercardParser),
    ('wellsfargo_checking', WellFargoCheckingParser),
    ('wellsfargo_savings', WellFargoCheckingParser),
    ('wellsfargo_visa', WellsFargoVisaParser),
    ('chase_visa', ChaseVisaParser),
]


def get_parser_class(pathname):
    filename = os.path.basename(pathname)
    matched_parser = next((p[1] for p in PARSER_MAP if filename.startswith(p[0])), None)
    if not matched_parser:
        raise ParseException('No class found for file: ' + filename)
    return matched_parser
