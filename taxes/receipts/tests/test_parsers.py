import functools
import logging
import os
import re

import pytest

from taxes.receipts import constants, models, parsers
from .logging import log_contains_message, MockLogger

pytestmark = pytest.mark.usefixtures(
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
    # TODO remove category 'Payment'
    parser.parse(pathname)

    assert not log_contains_message(logger, 'Pattern not found', level=logging.ERROR)
    assert parser.failures == 0


@pytest.fixture()
def run_parser(transaction_fixture_dir, mock_logger):
    return functools.partial(_run_parser, transaction_dir=transaction_fixture_dir, logger=mock_logger)


def _skipped_vendors_from_log(logger):
    actual_skip_warnings = filter(
        lambda m: m.level == logging.WARN and re.match(r'^Skipped vendor', m.msg),
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
        .order_by('purchased_at', 'vendor__name', 'total_amount')
    )


def _verify_receipts(actual_receipts, expected_receipt_values):
    """
    :param actual_receipts: array of models.Receipt
    :param expected_receipt_values: array of tuples (purchased_at, vendor.name, total_amount)
    """
    assert len(actual_receipts) == len(expected_receipt_values)
    for i, r in enumerate(actual_receipts):
        assert r.purchased_at.isoformat() == expected_receipt_values[i][0]
        assert r.vendor.name == expected_receipt_values[i][1]
        assert r.total_amount == expected_receipt_values[i][2]


def test_parse_bmo_savings(run_parser):
    run_parser('bmo_savings_2016-08.csv')

    actual_receipts = _all_sorted_receipts()

    expected_receipt_values = [
        ('2016-08-02', 'MTCC 452', -1133),
        ('2016-08-02', 'Warren Smooth', 160000),
        ('2016-08-02', 'YRCC 994', -200839),
        ('2016-08-03', 'FootBlind Finance Analytic', 30890),
        ('2016-08-15', 'City of Toronto', -73300),
    ]
    _verify_receipts(actual_receipts, expected_receipt_values)

    assert {r.payment_method.name for r in actual_receipts} == {'BMO Savings'}
    assert {r.currency for r in actual_receipts} == {constants.Currency.CAD}


def test_parse_bmo_amount_exclusion(run_parser, mock_logger):
    run_parser('bmo_savings_2016-09_amount_exclusion.csv')

    actual_receipts = _all_sorted_receipts()

    expected_receipt_values = [
        ('2016-09-01', 'MTCC 452', -1133),
        ('2016-09-01', 'Warren Smooth', 160000),
        ('2016-09-01', 'YRCC 994', -200839),
        ('2016-09-06', 'FootBlind Finance Analytic', 30890),
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
        ('2016-02-18', 'Intuit', -4999),
        ('2016-04-22', 'Air Canada', -85276),
        ('2016-05-07', 'Aroma', -961),
        ('2016-05-07', "Joe's Hamburgers", -4028),
        ('2016-05-07', 'Pizza Libretto', -13300),
        ('2016-05-08', "Real Mo-Mo's", -6734),
        ('2016-05-08', "Tim Horton's", -369),
        ('2016-05-09', 'Wine Rack', -3295),
        ('2016-05-10', 'Panera Bread', -2108),
        ('2016-05-10', "Tim Horton's", -150),
        ('2016-05-11', 'Boccone Trattoria', -2066),
    ]
    _verify_receipts(actual_receipts, expected_receipt_values)

    assert {r.payment_method.name for r in actual_receipts} == {'BMO Paypass Mastercard'}
    assert {r.currency for r in actual_receipts} == {constants.Currency.CAD}


def test_parse_readiline(run_parser, mock_logger):
    run_parser('bmo_readiline_2016-09.csv')

    actual_skipped_vendors = _skipped_vendors_from_log(mock_logger)
    assert len(actual_skipped_vendors) == 0

    actual_receipts = _all_sorted_receipts()
    expected_receipt_values = [
        ('2016-09-09', 'BMO', -45377),
    ]
    _verify_receipts(actual_receipts, expected_receipt_values)

    assert {r.payment_method.name for r in actual_receipts} == {'BMO Readiline'}
    assert {r.currency for r in actual_receipts} == {constants.Currency.CAD}


def test_parse_capitalone(run_parser, mock_logger):
    run_parser('capitalone-09-10-2016.csv')

    # collect skip warnings
    actual_skipped_vendors = _skipped_vendors_from_log(mock_logger)
    expected_skipped_vendors = {
        'Amazon.com',
        'CHESTNUT ST COFFEE ROA',
        'NORDSTROM #0427',
        'FELLOW BARBER - VALENC',
        'MARINA THEATRE',
        'MARINA DELI & LIQUORS',
        'SQ *ALLSTAR CAFE',
        'AMAZON MKTPLACE PMTS',
        'SMITTEN ICE CREAM - 00',
        "PEET'S #21302",
        'MUIR WOODS',
    }
    assert expected_skipped_vendors == actual_skipped_vendors

    actual_receipts = _all_sorted_receipts()
    expected_receipt_values = [
        # (purchased_at, vendor.name, total_amount)
        ('2016-08-09', 'We Be Sushi', -2642),
        ('2016-08-10', "Barney's Burgers", -3082),
        ('2016-08-11', 'Marina Supermarket', -428),
        ('2016-08-12', 'Bonita Taqueria', -2001),
        ('2016-08-13', 'FedEx', -525),
        ('2016-08-15', 'Golden Kim Tar', -2334),
        ('2016-08-18', 'Saiwalks', -2382),
        ('2016-08-19', 'Marina Supermarket', -3445),
        ('2016-08-24', 'Senior Sisig', -1496),
        ('2016-08-24', 'Yum Yum Hunan', -3483)
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
        # (purchased_at, vendor.name, total_amount)
        ('2016-09-16', 'Relay', -281),
    ]
    _verify_receipts(actual_receipts, expected_receipt_values)

    assert {r.payment_method.name for r in actual_receipts} == {'MBNA Mastercard'}
    assert {r.currency for r in actual_receipts} == {constants.Currency.CAD}


def test_parse_checking_account_basic(run_parser, mock_logger):
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
        # (purchased_at, vendor.name, total_amount)
        ('2016-08-15', 'Liars', 8035),
        ('2016-08-30', '21st Century Insurance', -7666),
        ('2016-08-31', 'Liars', 16636),
    ]
    _verify_receipts(actual_receipts, expected_receipt_values)

    assert {r.payment_method.name for r in actual_receipts} == {'Wells Fargo Checking'}
    assert {r.currency for r in actual_receipts} == {constants.Currency.USD}


def test_parse_checking_account_basic_with_fixed_amount(run_parser, mock_logger):
    run_parser('wellsfargo_checking_2016-09_fixed_amount.csv')

    actual_receipts = _all_sorted_receipts()
    expected_receipt_values = [
        # (purchased_at, vendor.name, total_amount)
        ('2016-09-16', 'Xoom', -499),
        ('2016-09-28', '21st Century Insurance', -7666),
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
        # (purchased_at, vendor.name, total_amount)
        ('2016-09-01', 'Chariot', -11900),
        ('2016-09-03', 'Crepevine', -1469),
    ]

    _verify_receipts(actual_receipts, expected_receipt_values)

    assert {r.payment_method.name for r in actual_receipts} == {'Wells Fargo Visa Card'}
    assert {r.currency for r in actual_receipts} == {constants.Currency.USD}


def test_parse_chase_visa(run_parser, mock_logger):
    run_parser('chase_visa_2016-09.csv')

    actual_skipped_vendors = _skipped_vendors_from_log(mock_logger)
    expected_skipped_vendors = {
        'ATT*BILL PAYMENT',
        'AT&AMP;T*BILL PAYMENT',
        'BANANAREPUBLIC US 8035',
        'CHESTNUT ST COFFEE ROASTE',
        'DON PABLO',
        "LEE'S DELI-2ND ST",
        'MAVEN',
        'RINCON MARKET',
        'SPORTS BASEMENT',
        'SQ *ALLSTAR CAFE',
        'SQ *BLUE BOTTLE COFFEE',
        'SQ *COUNTER OFFER, LLC',
        'SQ *OVER THE MOON',
        'SAFEWAY  STORE00017111',
        'WALGREENS #1403',
    }
    assert expected_skipped_vendors == actual_skipped_vendors

    actual_receipts = _all_sorted_receipts()
    expected_receipt_values = [
        # (purchased_at, vendor.name, total_amount)
        ('2016-09-01', 'Blackwood', -7315),
        ('2016-09-01', 'The Market', -1487),
        ('2016-09-02', 'Squat and Gobble', -1477),
        ('2016-09-03', 'IHOP', -1812),
        ('2016-09-04', "Barney's Burgers", -2529),
        ('2016-09-04', 'Squat and Gobble', -1771),
        ('2016-09-06', 'The Market', -1372),
        ('2016-09-06', 'We Be Sushi', -2349),
        ('2016-09-07', 'Gyro King', -1617),
        ('2016-09-08', 'Air Canada', -126433),
        ('2016-09-08', 'Air Canada', -83409),
        ('2016-09-08', 'Uber', -598),
        ('2016-09-09', 'Expedia', -1000),
        ('2016-09-10', "Barney's Burgers", -2591),
        ('2016-09-10', 'Squat and Gobble', -1613),
        ('2016-09-10', 'Uber', -475),
        ('2016-09-10', 'Uber', -475),
        ('2016-09-10', 'Uber', -200),
        ('2016-09-11', 'Il Fornaio Caffe Del Mondo', -1468),
        ('2016-09-11', 'Uber', -1917),
        ('2016-09-13', 'Uber', -712),
        ('2016-09-13', 'Uber', -461),
        ('2016-09-15', 'Bonita Taqueria', -1170),
        ('2016-09-15', 'Uber', -1880),
        ('2016-09-15', 'Uber', -457),
        ('2016-09-16', 'The Sandwich Spot', -1474),
        ('2016-09-16', 'Uber', -1999),
        ('2016-09-18', 'Pacific Catch', -2531),
        ('2016-09-18', 'Zipcar', -762),
        ('2016-09-19', 'Glaze Teriyaki', -1578),
        ('2016-09-19', 'Saiwalks', -1952),
        ('2016-09-20', 'Uber', -332),
        ('2016-09-21', 'Taqueria El Buen Sabor', -1115),
        ('2016-09-22', 'Freshbooks', -995),
        ('2016-09-24', 'FedEx', -274),
        ('2016-09-24', 'Uber', -475),
        ('2016-09-25', 'IHOP', -1894),
        ('2016-09-25', 'Uber', -1431),
        ('2016-09-25', 'Uber', -500),
        ('2016-09-25', 'Uber', -475),
        ('2016-09-26', 'Github', -700),
        ('2016-09-30', 'FedEx', -288),
        ('2016-09-30', 'Glaze Teriyaki', -1588),
        ('2016-09-30', 'Sharetea', -575)
    ]
    _verify_receipts(actual_receipts, expected_receipt_values)
