"""
Regression tests for business logic that classifies transactions into receipts
"""
import functools
import logging
from io import StringIO

import pytest

from taxes.receipts import models
from taxes.receipts.tests.logging import MockLogger, log_contains_message
import taxes.receipts.itemize as itemize_module
from taxes.receipts.util.datetime import parse_iso_datestring
from taxes.receipts.tests.factories import VendorFactory

from taxes.receipts.types import (
    RawTransaction,
    Currency,
    PaymentMethod,
    ExpenseType,
    TaxType,
    RAW_TRANSACTION_ITERABLE,
    AliasMatchOperation
)


@pytest.fixture()
def itemize_test_setup(request, monkeypatch):
    mock = MockLogger()
    monkeypatch.setattr(itemize_module, 'LOGGER', mock)
    request.cls.mock_logger = mock
    request.cls.itemizer = itemize_module.Itemizer('test_filename.csv')


@pytest.fixture()
def bmo_savings_test_setup(request):
    request.cls.payment_method = models.PaymentMethod.objects.get(name='BMO Savings')


@pytest.fixture()
def bmo_credit_test_setup(request):
    request.cls.payment_method = models.PaymentMethod.objects.get(name='BMO Savings')


@pytest.fixture()
def wellsfargo_checking_test_setup(request, settings):
    request.cls.payment_method = models.PaymentMethod.objects.get(name='Wells Fargo Checking')


@pytest.fixture
def t_file():
    return StringIO()


# pylint:disable=too-many-arguments
def _make_expected_transaction(line_number: int, transaction_datestr: str, amount: int,
                               description: str, misc: dict,
                               currency: Currency = None,
                               payment_method: PaymentMethod = None) -> RawTransaction:
    return RawTransaction(
        line_number=line_number,
        payment_method=payment_method,
        transaction_date=parse_iso_datestring(transaction_datestr),
        amount=amount,
        currency=currency,
        description=description,
        misc=misc
    )
# pylint:enable=too-many-arguments


def _get_all_sorted_receipts():
    q_receipts = models.Transaction.objects \
        .extra(
            select={'transaction_date_isoformat': "to_char(transaction_date, 'YYYY-MM-DD')"}
        ) \
        .select_related('vendor', 'payment_method') \
        .order_by('transaction_date', 'vendor__name', 'expense_type', 'total_amount') \
        .values_list(
            'transaction_date_isoformat',
            'vendor__name',
            'total_amount',
            'expense_type'
        )
    return list(q_receipts)


class BaseTestItemize:
    # to be injected by 'itemize_test_setup' fixture
    mock_logger: MockLogger = None
    itemizer: itemize_module.Itemizer = None
    payment_method: models.PaymentMethod = None

    def _run_itemizer(self, transactions: RAW_TRANSACTION_ITERABLE):
        self.itemizer.process_transactions(transactions)
        assert not log_contains_message(self.mock_logger, 'Pattern not found', level=logging.ERROR)


@pytest.mark.usefixtures(
    'itemize_test_setup',
    'transactional_db',
    'payment_methods',
    'vendors_and_exclusions',
    'bmo_savings_test_setup',
)
class TestBmoBankAccountItemize(BaseTestItemize):

    def _make_transaction(self):
        return functools.partial(_make_expected_transaction,  # pylint:disable=invalid-name
                                 currency=Currency.CAD, payment_method=self.payment_method)

    def _make_misc(self):
        return lambda transaction_code: {
            'last_4_digits': self.payment_method.safe_numeric_id,
            'transaction_code': transaction_code
        }

    def test_vendor_alias_match(self):
        # pylint:disable=invalid-name
        _T = self._make_transaction()
        _m = self._make_misc()
        # pylint:enable=invalid-name

        transactions = [
            _T(7, '2016-08-02', -1133, 'MTCC 452        FEE/FRA', _m('DS')),
            _T(8, '2016-08-02', 160000, '', _m('CD')),
            _T(15, '2016-08-15', -73300, 'TORONTO TAX     TAX/TAX', _m('DS')),
        ]
        self._run_itemizer(transactions)

        results = _get_all_sorted_receipts()
        assert results == [
            ('2016-08-02', 'MTCC 452', -1133, ExpenseType.ADMINISTRATIVE),
            ('2016-08-02', 'Warren Smooth', 160000, ExpenseType.RENT),
            ('2016-08-15', 'City of Toronto', -73300, ExpenseType.PROPERTY_TAX),
        ]

    def test_hst_adjustments(self):
        # pylint:disable=invalid-name
        _T = self._make_transaction()
        _m = self._make_misc()
        # pylint:enable=invalid-name

        transactions = [
            _T(1, '2016-08-02', -200839, 'YRCC994         FEE/FRA', _m('DS')),
            _T(2, '2016-08-03', 30890, '', _m('CD')),
        ]

        self._run_itemizer(transactions)

        receipts = _get_all_sorted_receipts()
        assert receipts == [
            ('2016-08-02', 'YRCC 994', -200839, ExpenseType.ADMINISTRATIVE),
            ('2016-08-03', 'FootBlind Finance Analytic', 30890, ExpenseType.RENT),
        ]

        # verify HST adjustment
        adjustments = models.TaxAdjustment.objects.order_by('receipt__vendor__name').all()
        assert len(adjustments) == 2

        assert adjustments[0].tax_type == TaxType.HST
        assert adjustments[0].receipt.vendor.name == 'FootBlind Finance Analytic'
        assert adjustments[0].amount == 3554  # 13 % of original base amount

        assert adjustments[1].tax_type == TaxType.HST
        assert adjustments[1].receipt.vendor.name == 'YRCC 994'
        assert adjustments[1].amount == -23105  # 13 % of original base amount

    def test_transaction_code_exclusions(self):
        # pylint:disable=invalid-name
        _T = self._make_transaction()
        _m = self._make_misc()
        # pylint:enable=invalid-name

        transactions = [
            _T(1, '2016-08-15', -50000, 'AP    000000002288889ZZZZ', _m('SO')),
            _T(2, '2016-08-23', -3500, 'BMO MASTERCARD', _m('CW')),
            _T(3, '2016-08-31', -2600, 'PREMIUM PLAN', _m('SC')),
            _T(3, '2016-08-31', 2600, 'FULL PLAN FEE REBATE', _m('SC')),
        ]

        self._run_itemizer(transactions)

        receipts = _get_all_sorted_receipts()
        assert receipts == []

        assert log_contains_message(self.mock_logger, 'Skipping transaction:.*',
                                    level=logging.WARNING)


@pytest.mark.usefixtures(
    'itemize_test_setup',
    'transactional_db',
    'payment_methods',
    'vendors_and_exclusions',
    'bmo_credit_test_setup',
)
class TestBmoCreditItemize(BaseTestItemize):

    def _make_transaction(self):
        return functools.partial(_make_expected_transaction,  # pylint:disable=invalid-name
                                 currency=Currency.CAD, payment_method=self.payment_method)

    def test_payment_exclusions(self):
        # pylint:disable=invalid-name
        _T = self._make_transaction()
        # pylint:enable=invalid-name

        misc = {
            'last_4_digits': self.payment_method.safe_numeric_id,
        }
        transactions = [
            _T(1, '2016-05-12', -150, 'TIM HORTONS #6011 TORONTO ON', misc),
            _T(2, '2016-05-17', 1347723, 'PAYMENT RECEIVED - THANK YOU', misc),
            _T(3, '2016-08-15', 50000, 'AUTOMATIC PAYMENT RECEIVED - THANK YOU', misc),
            _T(4, '2016-09-09', -45377, 'INTEREST ADVANCES  @ 02.70000% TO 09SEP', misc),
        ]

        self._run_itemizer(transactions)

        receipts = _get_all_sorted_receipts()
        assert receipts == [
            ('2016-05-12', "Tim Horton's", -150, ExpenseType.MEALS_AND_ENTERTAINMENT),
            ('2016-09-09', 'BMO', -45377, ExpenseType.INTEREST),
        ]

        assert log_contains_message(self.mock_logger, 'Skipping transaction:.*',
                                    level=logging.WARNING)


@pytest.mark.usefixtures(
    'itemize_test_setup',
    'transactional_db',
    'payment_methods',
    'vendors_and_exclusions',
    'wellsfargo_checking_test_setup',
)
class TestWellsFargoItemize(BaseTestItemize):

    def _make_transaction(self):
        return functools.partial(_make_expected_transaction,  # pylint:disable=invalid-name
                                 currency=Currency.USD, payment_method=self.payment_method)

    def test_exclusion_conditions(self):
        # pylint:disable=invalid-name
        _T = self._make_transaction()
        # pylint:enable=invalid-name

        maven_vendor = VendorFactory.create(
            name='Maven',
            default_expense_type=ExpenseType.MEALS_AND_ENTERTAINMENT
        )
        models.VendorAliasPattern.objects.create(vendor=maven_vendor, pattern='MAVEN',
                                                 match_operation=AliasMatchOperation.EQUAL)

        transactions = [
            # should be excluded
            _T(1, '2016-08-18', -5480, "PGANDE WEB ONLINE AUG 16 44444444444444 JOHN DOE", {}),

            # should be included
            _T(4, '2016-08-30', -667, 'MAVEN', {}),
            _T(5, '2016-08-31', 16636, "GUSTO PAY 666666 555555 6AAAAAA06uq John Doe", {}),

            # should be excluded
            _T(6, '2016-09-15', 4219, 'SOME VENDOR', {}),
            _T(7, '2016-09-21', -667, 'MAVEN', {}),
        ]

        self._run_itemizer(transactions)

        receipts = _get_all_sorted_receipts()
        assert receipts == [
            ('2016-08-30', 'Maven', -667, ExpenseType.MEALS_AND_ENTERTAINMENT),
            ('2016-08-31', 'Liars', 16636, ExpenseType.FOREIGN_INCOME),
        ]

        assert log_contains_message(self.mock_logger, 'Skipping transaction:.*',
                                    level=logging.WARNING)

    def test_online_payment_exclusions(self):
        # pylint:disable=invalid-name
        _T = self._make_transaction()
        # pylint:enable=invalid-name

        transactions = [

            # excluded
            _T(2, '2016-09-27', 19815, 'ELECTRONIC PAYMENT', {'category': 'Payment'}),
            _T(3, '2016-09-27', 999, 'PAYMENT', {}),

            # verify expense type based on alias
            _T(6, '2016-09-01', -2500, 'ANNUAL FEE FOR 01/16 THROUGH 12/16', {}),

            # excluded
            _T(7, '2016-09-27', 19815, 'ONLINE PAYMENT', {}),
            _T(8, '2019-02-28', -533398, 'Payment Thank You - Bill', {'type': 'Payment'}),
        ]

        self._run_itemizer(transactions)

        receipts = _get_all_sorted_receipts()
        assert receipts == [
            ('2016-09-01', 'Wells Fargo', -2500, ExpenseType.ADMINISTRATIVE),
        ]

        assert log_contains_message(self.mock_logger, 'Skipping transaction:.*',
                                    level=logging.WARNING)
