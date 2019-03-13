import functools
import logging
import os
import re

import pytest

from taxes.receipts import constants, models, parsers
from .logging import log_contains_message, MockLogger

pytestmark = pytest.mark.usefixtures(  # pylint: disable=invalid-name
    'transactional_db',
    'payment_methods',
    'vendors_and_exclusions'
)


@pytest.fixture()
def mock_logger(monkeypatch):
    mock = MockLogger()
    monkeypatch.setattr(parsers, 'LOGGER', mock)
    return mock


def _run_parser(filename, transaction_dir=None, logger=None):
    assert transaction_dir
    assert logger

    pathname = os.path.join(transaction_dir, filename)
    parser_class = parsers.get_parser_class(pathname)
    parser = parser_class()
    parser.parse(pathname)

    assert not log_contains_message(logger, 'Pattern not found', level=logging.ERROR)
    assert parser.failures == 0


def _skipped_vendors_from_log(logger):
    actual_skip_warnings = filter(
        lambda m: m.level == logging.WARN and
        re.match(r'^Skipped vendor', m.msg),
        logger.messages
    )
    return set(
        map(
            lambda m: re.match(r'^Skipped vendor (?P<vendor>.+)$', m.msg).group(1),
            actual_skip_warnings
        )
    )


def _all_sorted_receipts():
    return list(
        models.Receipt.objects
        .select_related('vendor', 'payment_method')
        .order_by('transaction_date', 'vendor__name', 'expense_type', 'total_amount')
    )


def _verify_receipts(actual_receipts, expected_receipt_values):
    """
    :param actual_receipts: array of models.Receipt
    :param expected_receipt_values: array of tuples
        (transaction_date, vendor.name, total_amount, expense_type)
    """
    assert len(actual_receipts) == len(expected_receipt_values)
    for i, receipt in enumerate(actual_receipts):
        assert receipt.transaction_date.isoformat() == expected_receipt_values[i][0]
        assert receipt.vendor.name == expected_receipt_values[i][1]
        assert receipt.total_amount == expected_receipt_values[i][2]
        assert receipt.expense_type == expected_receipt_values[i][3]


# pylint: disable=redefined-outer-name
@pytest.fixture()
def run_parser(transaction_fixture_dir, mock_logger):
    # clear the cache to to avoid using primary keys from test fixtures
    # pylint: disable=protected-access
    parsers.BaseParser._get_payment_method.cache_clear()
    # pylint: enable=protected-access

    return functools.partial(_run_parser,
                             transaction_dir=transaction_fixture_dir, logger=mock_logger)


def test_parse_bmo_savings(run_parser):
    run_parser('bmo_savings_2016-08.csv')

    actual_receipts = _all_sorted_receipts()

    expected_receipt_values = [
        ('2016-08-02', 'MTCC 452', -1133, constants.ExpenseType.ADMINISTRATIVE),
        ('2016-08-02', 'Warren Smooth', 160000, constants.ExpenseType.RENT),
        ('2016-08-02', 'YRCC 994', -200839, constants.ExpenseType.ADMINISTRATIVE),
        ('2016-08-03', 'FootBlind Finance Analytic', 30890, constants.ExpenseType.RENT),
        ('2016-08-15', 'City of Toronto', -73300, constants.ExpenseType.PROPERTY_TAX),
    ]
    _verify_receipts(actual_receipts, expected_receipt_values)

    assert {r.payment_method.name for r in actual_receipts} == {'BMO Savings'}
    assert {r.currency for r in actual_receipts} == {constants.Currency.CAD}

    # verify HST adjustment
    adjustments = models.TaxAdjustment.objects.order_by('receipt__vendor__name').all()
    assert len(adjustments) == 2

    assert adjustments[0].tax_type == constants.TaxType.HST
    assert adjustments[0].receipt.vendor.name == 'FootBlind Finance Analytic'
    assert adjustments[0].amount == 3554  # 13 % of original base amount

    assert adjustments[1].tax_type == constants.TaxType.HST
    assert adjustments[1].receipt.vendor.name == 'YRCC 994'
    assert adjustments[1].amount == -23105  # 13 % of original base amount


def test_parse_bmo_amount_exclusion(run_parser, mock_logger):
    run_parser('bmo_savings_2016-09_amount_exclusion.csv')

    actual_receipts = _all_sorted_receipts()

    expected_receipt_values = [
        ('2016-09-01', 'MTCC 452', -1133, constants.ExpenseType.ADMINISTRATIVE),
        ('2016-09-01', 'Warren Smooth', 160000, constants.ExpenseType.RENT),
        ('2016-09-01', 'YRCC 994', -200839, constants.ExpenseType.ADMINISTRATIVE),
        ('2016-09-06', 'FootBlind Finance Analytic', 30890, constants.ExpenseType.RENT),
    ]
    _verify_receipts(actual_receipts, expected_receipt_values)

    assert log_contains_message(mock_logger, 'Skipping amount', level=logging.WARNING)


def test_parse_bmo_mastercard(run_parser, mock_logger):
    run_parser('bmo_mastercard.csv')

    # collect skip warnings
    actual_skipped_vendors = _skipped_vendors_from_log(mock_logger)
    expected_skipped_vendors = {
        'APL* ITUNES.COM/BILL 800-676-2775 ON'
    }
    assert expected_skipped_vendors == actual_skipped_vendors

    actual_receipts = _all_sorted_receipts()
    expected_receipt_values = [
        ('2016-02-18', 'Intuit', -4999, constants.ExpenseType.ADMINISTRATIVE),
        ('2016-04-22', 'Air Canada', -85276, constants.ExpenseType.TRAVEL),
        ('2016-05-07', 'Aroma', -961, constants.ExpenseType.MEALS_AND_ENTERTAINMENT),
        ('2016-05-07', "Joe's Hamburgers", -4028, constants.ExpenseType.MEALS_AND_ENTERTAINMENT),
        ('2016-05-07', 'Pizza Libretto', -13300, constants.ExpenseType.MEALS_AND_ENTERTAINMENT),
        ('2016-05-08', "Real Mo-Mo's", -6734, constants.ExpenseType.MEALS_AND_ENTERTAINMENT),
        ('2016-05-08', "Tim Horton's", -369, constants.ExpenseType.MEALS_AND_ENTERTAINMENT),
        ('2016-05-09', 'Wine Rack', -3295, constants.ExpenseType.MEALS_AND_ENTERTAINMENT),
        ('2016-05-10', 'Panera Bread', -2108, constants.ExpenseType.MEALS_AND_ENTERTAINMENT),
        ('2016-05-10', "Tim Horton's", -150, constants.ExpenseType.MEALS_AND_ENTERTAINMENT),
        ('2016-05-11', 'Boccone Trattoria', -2066, constants.ExpenseType.MEALS_AND_ENTERTAINMENT),
    ]
    _verify_receipts(actual_receipts, expected_receipt_values)

    assert {r.payment_method.name for r in actual_receipts} == {'BMO Paypass Mastercard'}
    assert {r.currency for r in actual_receipts} == {constants.Currency.CAD}


def test_parse_readiline(run_parser, mock_logger):
    run_parser('bmo_readiline_2016-09.csv')

    actual_skipped_vendors = _skipped_vendors_from_log(mock_logger)
    assert actual_skipped_vendors == set()

    actual_receipts = _all_sorted_receipts()
    expected_receipt_values = [
        ('2016-09-09', 'BMO', -45377, constants.ExpenseType.INTEREST),
    ]
    _verify_receipts(actual_receipts, expected_receipt_values)

    assert {r.payment_method.name for r in actual_receipts} == {'BMO Readiline'}
    assert {r.currency for r in actual_receipts} == {constants.Currency.CAD}


def test_parse_capitalone(run_parser, mock_logger):
    run_parser('capitalone_2017-09.csv')

    # collect skip warnings
    actual_skipped_vendors = _skipped_vendors_from_log(mock_logger)
    expected_skipped_vendors = {
        'BOOKS INC     80700131',
        'SAFEWAY  STORE00009670'
    }
    assert expected_skipped_vendors == actual_skipped_vendors

    actual_receipts = _all_sorted_receipts()
    expected_receipt_values = [
        # (transaction_date, vendor.name, total_amount)
        ('2017-09-04', 'Embarcadero Cinemas', -2600, constants.ExpenseType.MEALS_AND_ENTERTAINMENT),
        ('2017-09-09', 'Marina Supermarket', -2520, constants.ExpenseType.MEALS_AND_ENTERTAINMENT),
        ('2017-09-17', 'Yum Yum Hunan', -3054, constants.ExpenseType.MEALS_AND_ENTERTAINMENT),
        ('2017-09-20', "Lee's Deli", -1481, constants.ExpenseType.MEALS_AND_ENTERTAINMENT),
        ('2017-09-21', 'We Be Sushi', -2474, constants.ExpenseType.MEALS_AND_ENTERTAINMENT),
        ('2017-09-25', 'Glaze Teriyaki', -1462, constants.ExpenseType.MEALS_AND_ENTERTAINMENT),
    ]
    _verify_receipts(actual_receipts, expected_receipt_values)

    assert {r.payment_method.name for r in actual_receipts} == {'CapitalOne Platinum Mastercard'}
    assert {r.currency for r in actual_receipts} == {constants.Currency.USD}


def test_parse_mbna(run_parser, mock_logger):
    run_parser('mbna_mastercard_2016-09.csv')

    # collect skip warnings
    actual_skipped_vendors = _skipped_vendors_from_log(mock_logger)
    expected_skipped_vendors = {
        'NETFLIX.COM 866-716-0414 ON',
    }
    assert expected_skipped_vendors == actual_skipped_vendors

    actual_receipts = _all_sorted_receipts()
    expected_receipt_values = [
        # (transaction_date, vendor.name, total_amount)
        ('2016-09-16', 'Relay', -281, constants.ExpenseType.MEALS_AND_ENTERTAINMENT),
    ]
    _verify_receipts(actual_receipts, expected_receipt_values)

    assert {r.payment_method.name for r in actual_receipts} == {'MBNA Mastercard'}
    assert {r.currency for r in actual_receipts} == {constants.Currency.CAD}


def test_parse_checking_account_basic(run_parser, mock_logger):  # pylint: disable=invalid-name
    run_parser('wellsfargo_checking_2016-08.csv')

    # collect skip warnings
    actual_skipped_vendors = _skipped_vendors_from_log(mock_logger)
    expected_skipped_vendors = {
        "PGANDE WEB ONLINE AUG 16 44444444444444 JOHN DOE",
        "BART-CLIPPER POWELL SAN FRANCISCO CA P00000000000000002 CARD 0069",
        "BART-CLIPPER POWELL SAN FRANCISCO CA P00000000000000008 CARD 0069",
        "VENMO-0 CASHOUT XXXXX1595 JOHN DOE",
    }
    assert expected_skipped_vendors == actual_skipped_vendors

    actual_receipts = _all_sorted_receipts()
    expected_receipt_values = [
        # (transaction_date, vendor.name, total_amount)
        ('2016-08-15', 'Liars', 8035, constants.ExpenseType.FOREIGN_INCOME),
        ('2016-08-15', 'Wells Fargo', 31, constants.ExpenseType.CAPITAL_GAINS),
        ('2016-08-30', '21st Century Insurance', -7666, constants.ExpenseType.INSURANCE),
        ('2016-08-31', 'Liars', 16636, constants.ExpenseType.FOREIGN_INCOME),
    ]
    _verify_receipts(actual_receipts, expected_receipt_values)

    assert {r.payment_method.name for r in actual_receipts} == {'Wells Fargo Checking'}
    assert {r.currency for r in actual_receipts} == {constants.Currency.USD}


def test_parse_checking_account_with_fixed_amount(run_parser):  # pylint: disable=invalid-name
    run_parser('wellsfargo_checking_2016-09_fixed_amount.csv')

    actual_receipts = _all_sorted_receipts()
    expected_receipt_values = [
        # (transaction_date, vendor.name, total_amount)
        ('2016-09-16', 'Xoom', -499, constants.ExpenseType.ADMINISTRATIVE),
        ('2016-09-28', '21st Century Insurance', -7666, constants.ExpenseType.INSURANCE),
    ]
    _verify_receipts(actual_receipts, expected_receipt_values)
    assert {r.currency for r in actual_receipts} == {constants.Currency.USD}


def test_parse_wellsfargo_visa(run_parser, mock_logger):
    run_parser('wellsfargo_visa_2016-09.csv')

    # collect skip warnings
    actual_skipped_vendors = _skipped_vendors_from_log(mock_logger)
    expected_skipped_vendors = {
        "WALGREENS #1403 SAN FRANCISCOCA",
        "CHESTNUT ST COFFEE ROASTESAN FRANCISCOCA",
        "REDBOX *DVD RENTAL OAKBROOK TER IL",
        "SQ *HAPPY DUMPLINGS HAYWARD CA",
    }
    assert expected_skipped_vendors == actual_skipped_vendors

    actual_receipts = _all_sorted_receipts()
    expected_receipt_values = [
        # (transaction_date, vendor.name, total_amount)
        ('2016-09-01', 'Chariot', -11900, constants.ExpenseType.TRAVEL),
        ('2016-09-01', 'Wells Fargo', -2500, constants.ExpenseType.ADMINISTRATIVE),
        ('2016-09-03', 'Crepevine', -1469, constants.ExpenseType.MEALS_AND_ENTERTAINMENT),
    ]

    _verify_receipts(actual_receipts, expected_receipt_values)

    assert {r.payment_method.name for r in actual_receipts} == {'Wells Fargo Visa Card'}
    assert {r.currency for r in actual_receipts} == {constants.Currency.USD}


def test_parse_chase_visa(run_parser, mock_logger):
    run_parser('chase_visa_2019-02.csv')

    actual_skipped_vendors = _skipped_vendors_from_log(mock_logger)
    expected_skipped_vendors = {
        'BANANAREPUBLIC US 8035',
    }
    assert expected_skipped_vendors == actual_skipped_vendors

    actual_receipts = _all_sorted_receipts()
    expected_receipt_values = [
        # (transaction_date, vendor.name, total_amount)
        ('2019-02-24', 'Ho Da La', -4283, constants.ExpenseType.MEALS_AND_ENTERTAINMENT),
        ('2019-02-24', 'Mainland Market', -5770, constants.ExpenseType.MEALS_AND_ENTERTAINMENT),
        ('2019-02-26', "Github", -700, constants.ExpenseType.ADMINISTRATIVE),
        ('2019-02-27', 'Intuit', -2398, constants.ExpenseType.ADMINISTRATIVE),
    ]
    _verify_receipts(actual_receipts, expected_receipt_values)
# pylint: enable=redefined-outer-name
