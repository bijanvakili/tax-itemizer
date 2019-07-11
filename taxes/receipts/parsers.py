import abc
import csv
import enum
import logging
import re

from taxes.receipts.models import PaymentMethod
from taxes.receipts.types import RawTransaction, RAW_TRANSACTION_GENERATOR
from taxes.receipts.util.datetime import parse_date
from taxes.receipts.util.currency import parse_amount


LOGGER = logging.getLogger(__name__)


class CommonColumn(enum.Enum):
    transaction_date = 'transaction_date'
    amount = 'amount'
    description = 'description'


class ParseException(Exception):
    def __init__(self, *args, line_number=None, **kwargs):
        self.line_number = line_number
        super().__init__(*args, **kwargs)

    def __repr__(self):
        prefix = f'{self.line_number} ' if self.line_number else ''
        return prefix + super().__repr__()


class TextFileLineFilter(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def is_accepted(self, line):
        pass


class NonEmptyLinesFilter(TextFileLineFilter):
    def is_accepted(self, line):
        return line.strip() != ''


class SkipPatternsFilter(TextFileLineFilter):
    def __init__(self, patterns):
        self.patterns = [re.compile(pattern) for pattern in patterns]

    def is_accepted(self, line):
        for pattern in self.patterns:
            if pattern.match(line):
                return False
        return True


class TextFileIterator(object):
    def __init__(self, file):
        self.file = file
        self._line_num = 0

    def __iter__(self):
        self._line_num = 0
        for line in self.file.readlines():
            self._line_num += 1
            yield line

    @property
    def line_num(self):
        return self._line_num


class BaseTransactionParser(metaclass=abc.ABCMeta):
    QUOTE_CHAR = '"'
    LINE_FILTERS = []
    CSV_FIELDS = None  # must be specified by derived class
    TRANSACTION_DATE_FORMAT = '%m/%d/%Y'

    """
    Base class for parsing transaction files from financial institutions
    """
    def __init__(self, payment_method: PaymentMethod):
        self.payment_method = payment_method
        self._failures = 0
        if not self.CSV_FIELDS:
            raise RuntimeError('CSV_FIELDS not specified in derived class')

    def parse(self, filename: str) -> RAW_TRANSACTION_GENERATOR:
        self._failures = 0
        with open(filename, 'r') as csv_file:
            raw_iter_lines = TextFileIterator(csv_file)
            iter_filtered_lines = filter(
                lambda line: all((f.is_accepted(line) for f in self.LINE_FILTERS)),
                raw_iter_lines
            )
            iter_rows = csv.DictReader(
                iter_filtered_lines,
                fieldnames=self.CSV_FIELDS,
                quotechar=self.QUOTE_CHAR
            )
            for row in iter_rows:
                try:
                    yield self.parse_row(row, raw_iter_lines.line_num)
                except Exception:
                    LOGGER.error('FAILURE on line %d of file %s',
                                 raw_iter_lines.line_num, filename)
                    self._failures += 1
                    raise

    @abc.abstractmethod
    def parse_row(self, row: dict, line_number: int) -> RawTransaction:
        pass

    @property
    def failures(self) -> int:
        return self._failures

    def _make_transaction(self, row: dict, line_number: int, misc: dict,
                          amount: int = None) -> RawTransaction:
        return RawTransaction(
            line_number=line_number,
            transaction_date=parse_date(
                row[CommonColumn.transaction_date.value],
                self.TRANSACTION_DATE_FORMAT
            ),
            amount=amount if amount else parse_amount(row[CommonColumn.amount.value]),
            currency=self.payment_method.currency,
            description=row[CommonColumn.description.value].strip(),
            misc=misc,
            payment_method=self.payment_method,
        )


class BMOCSVBankAccountParser(BaseTransactionParser):
    QUOTE_CHAR = "'"
    LINE_FILTERS = [
        NonEmptyLinesFilter(),
        SkipPatternsFilter([
            r'^Following data is valid as of.*',
            r'^First Bank Card.*'
        ]),
    ]
    CSV_FIELDS = [
        'card_number',
        'transaction_type',
        CommonColumn.transaction_date.value,
        CommonColumn.amount.value,
        'consolidated_description'
    ]
    TRANSACTION_DATE_FORMAT = '%Y%m%d'
    DESCRIPTION_PARSER = re.compile(r'^\[([A-Z]{2})\](.*)$')

    def parse_row(self, row: dict, line_number: int) -> RawTransaction:
        match = self.DESCRIPTION_PARSER.search(row['consolidated_description'])
        if not match:
            raise ParseException('Unable to parse line', line_number=line_number)
        transaction_code, description = match.groups()

        row[CommonColumn.description.value] = description
        return self._make_transaction(row, line_number, {
            'last_4_digits': row['card_number'][-4:],
            'transaction_code': transaction_code,
        })


class BMOCSVCreditParser(BaseTransactionParser):
    QUOTE_CHAR = "'"
    LINE_FILTERS = [
        NonEmptyLinesFilter(),
        SkipPatternsFilter([
            r'^Following data is valid as of.*',
            r'^Item #.*'
        ]),
    ]
    CSV_FIELDS = [
        'item_number',
        'card_number',
        CommonColumn.transaction_date.value,
        'posting_date',
        CommonColumn.amount.value,
        CommonColumn.description.value,
    ]
    TRANSACTION_DATE_FORMAT = '%Y%m%d'

    def parse_row(self, row: dict, line_number: int) -> RawTransaction:
        # all postive values are debited as expenses
        amount = -1 * parse_amount(row[CommonColumn.amount.value])

        return self._make_transaction(row, line_number, {
            'last_4_digits': row['card_number'][-4:],
        }, amount=amount)


class MBNAMastercardParser(BaseTransactionParser):
    LINE_FILTERS = [
        SkipPatternsFilter([r'^Posted Date,Payee.*'])
    ]
    CSV_FIELDS = [
        CommonColumn.transaction_date.value,
        CommonColumn.description.value,
        'address',
        CommonColumn.amount.value,
    ]
    TRANSACTION_DATE_FORMAT = '%m/%d/%Y'

    def parse_row(self, row: dict, line_number: int) -> RawTransaction:
        return self._make_transaction(row, line_number, {})


class CapitalOneMastercardParser(BaseTransactionParser):
    LINE_FILTERS = [
        SkipPatternsFilter([r'^Transaction Date.*'])
    ]
    CSV_FIELDS = [
        CommonColumn.transaction_date.value,
        'posted_date',
        'card_number',
        CommonColumn.description.value,
        'category',
        'debit',
        'credit'
    ]
    TRANSACTION_DATE_FORMAT = '%Y-%m-%d'

    def parse_row(self, row: dict, line_number: int) -> RawTransaction:
        debit_amount = parse_amount(row['debit'] or '0.0')
        credit_amount = parse_amount(row['credit'] or '0.0')
        return self._make_transaction(row, line_number, {
            'last_4_digits': row['card_number'],
            'category': row['category']
        }, amount=credit_amount - debit_amount)


class ChaseVisaParser(BaseTransactionParser):
    LINE_FILTERS = [
        SkipPatternsFilter([r'^Transaction Date,Post Date.*'])
    ]
    CSV_FIELDS = [
        CommonColumn.transaction_date.value,
        'posted_date',
        CommonColumn.description.value,
        'category',
        'type',
        CommonColumn.amount.value,
    ]

    def parse_row(self, row: dict, line_number: int) -> RawTransaction:
        return self._make_transaction(row, line_number, {
            'category': row['category'],
            'type': row['type'],
        })


class WellsFargoParser(BaseTransactionParser):
    LINE_FILTERS = [
        NonEmptyLinesFilter(),
    ]
    CSV_FIELDS = [
        CommonColumn.transaction_date.value,
        CommonColumn.amount.value,
        'unknown_0',
        'check_number',
        CommonColumn.description.value,
    ]

    def __init__(self, *args):
        super().__init__(*args)
        self.authorized_purchase_pattern = re.compile(
            r'^PURCHASE AUTHORIZED ON (?P<authorized_date>\d{2}/\d{2}) (?P<party>.+)$'
        )

    def parse_row(self, row: dict, line_number: int) -> RawTransaction:
        # extract real payee if preauthorized payment
        misc = {}
        preauthorized_match = self.authorized_purchase_pattern.match(
            row[CommonColumn.description.value]
        )
        if preauthorized_match:
            row[CommonColumn.description.value] = preauthorized_match.group('party')
            misc['authorized_purchase_on'] = preauthorized_match.group('authorized_date')

        return self._make_transaction(row, line_number, misc)
