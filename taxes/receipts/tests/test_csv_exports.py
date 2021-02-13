from decimal import Decimal
from io import StringIO
import logging
import os

import pytest

from taxes.receipts.csv_exporters import dump_transactions, dump_forex
from taxes.receipts import models
from taxes.receipts.parsers_factory import ParserFactory
from taxes.receipts.itemize import Itemizer, LOGGER as ITEMIZER_LOGGER
from taxes.receipts.util.datetime import parse_iso_datestring as isodstr


@pytest.fixture(autouse=True)
def data_reporters_setup(transactional_db):  # pylint: disable=unused-argument
    return


@pytest.fixture
def t_file():
    return StringIO()


def _verify_csv_output(fileobj, expected_rows):
    # sanity check
    assert expected_rows

    max_rows = len(expected_rows)
    for row_id, row in enumerate(fileobj):
        assert row_id < max_rows
        parsed_row = row.strip().split(",")
        assert parsed_row == expected_rows[row_id]


# pylint: disable=redefined-outer-name
@pytest.mark.usefixtures("payment_methods", "vendors_and_exclusions")
def test_receipt_dump_matched(t_file, transaction_fixture_dir):
    filename = os.path.join(transaction_fixture_dir, "bmo_savings_2016-08.csv")
    parser_factory = ParserFactory()
    parser = parser_factory.get_parser(filename)
    itemizer = Itemizer(filename)
    itemizer.process_transactions(parser.parse(filename))

    dump_transactions(
        t_file, isodstr("2016-08-01"), isodstr("2016-09-01"), output_header=True
    )

    expected_rows = [
        [
            "Date",
            "Asset",
            "Currency",
            "Amount",
            "Transaction Party",
            "HST Amount (CAD)",
            "Tax Category",
            "Payment Method",
            "Notes",
        ],
        [
            "2016-08-02",
            "1001-25 Wellesley St",
            "CAD",
            "-11.33",
            "MTCC 452",
            "",
            "HOA Fees",
            "BMO Savings",
            "",
        ],
        [
            "2016-08-02",
            "1001-25 Wellesley St",
            "CAD",
            "1600.00",
            "Warren Smooth",
            "",
            "Gross Rent",
            "BMO Savings",
            "",
        ],
        [
            "2016-08-02",
            "5-699 Amber St",
            "CAD",
            "-2008.39",
            "YRCC 994",
            "-231.05",
            "HOA Fees",
            "BMO Savings",
            "",
        ],
        [
            "2016-08-03",
            "5-699 Amber St",
            "CAD",
            "308.90",
            "FootBlind Finance Analytic",
            "35.54",
            "Gross Rent",
            "BMO Savings",
            "",
        ],
        [
            "2016-08-15",
            "1001-25 Wellesley St",
            "CAD",
            "-733.00",
            "City of Toronto",
            "",
            "Property Tax",
            "BMO Savings",
            "",
        ],
    ]
    t_file.seek(0)
    _verify_csv_output(t_file, expected_rows)


@pytest.mark.usefixtures("payment_methods", "vendors_and_exclusions")
def test_receipt_dump_unmatched(t_file, transaction_fixture_dir):
    filename = os.path.join(transaction_fixture_dir, "capitalone_2019-06.csv")
    parser_factory = ParserFactory()
    parser = parser_factory.get_parser(filename)
    itemizer = Itemizer(filename)
    itemizer.process_transactions(parser.parse(filename))

    ITEMIZER_LOGGER.setLevel(logging.CRITICAL)
    dump_transactions(
        t_file, isodstr("2019-04-30"), isodstr("2019-05-31"), output_header=True
    )

    expected_rows = [
        [
            "Date",
            "Asset",
            "Currency",
            "Amount",
            "Transaction Party",
            "HST Amount (CAD)",
            "Tax Category",
            "Payment Method",
            "Notes",
        ],
        [
            "2019-05-30",
            "Sole Proprietorship",
            "USD",
            "-20.61",
            "Mainland Market",
            "",
            "Meals",
            "CapitalOne Platinum Mastercard",
            "",
        ],
        [
            "2019-06-12",
            "1001-25 Wellesley St",
            "USD",
            "-7.07",
            "Uber",
            "",
            "Business Travel",
            "CapitalOne Platinum Mastercard",
            "",
        ],
        [
            "2019-06-15",
            "1001-25 Wellesley St",
            "USD",
            "-7.91",
            "Uber",
            "",
            "Business Travel",
            "CapitalOne Platinum Mastercard",
            "",
        ],
        [
            "2019-06-15",
            "Sole Proprietorship",
            "USD",
            "-2.98",
            "Safeway",
            "",
            "Meals",
            "CapitalOne Platinum Mastercard",
            "",
        ],
        [
            "2019-06-17",
            "*UNKNOWN*",
            "USD",
            "-20.05",
            "LYFT   *RIDE SUN 11PM",
            "",
            "*UNKNOWN*",
            "CapitalOne Platinum Mastercard",
            "",
        ],
    ]
    t_file.seek(0)
    _verify_csv_output(t_file, expected_rows)


def test_dump_forex_rates(t_file):
    models.ForexRate.objects.bulk_create(
        [
            models.ForexRate(
                effective_at=isodstr("2017-11-01"),
                pair="CAD/USD",
                rate=Decimal("1.2345"),
            ),
            models.ForexRate(
                effective_at=isodstr("2017-11-02"),
                pair="CAD/USD",
                rate=Decimal("1.4343"),
            ),
            models.ForexRate(
                effective_at=isodstr("2017-11-03"),
                pair="CAD/USD",
                rate=Decimal("1.5555"),
            ),
        ]
    )

    dump_forex(t_file, isodstr("2017-11-01"), isodstr("2017-11-03"), output_header=True)

    expected_rows = [
        ["Date", "Rate"],
        ["2017-11-01", "1.2345"],
        ["2017-11-02", "1.4343"],
        ["2017-11-03", "1.5555"],
    ]
    _verify_csv_output(t_file, expected_rows)


# pylint: enable=redefined-outer-name
