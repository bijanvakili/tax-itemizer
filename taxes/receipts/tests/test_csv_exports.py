from decimal import Decimal
from io import StringIO
import os

import pytest

from taxes.receipts.csv_exporters import dump_receipts, dump_forex
from taxes.receipts import models
from taxes.receipts.parsers import get_parser_class
from taxes.receipts.util.datetime import parse_iso_datestring as isodstr


@pytest.fixture(autouse=True)
def data_reporters_setup(transactional_db):
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
        parsed_row = row.strip().split(',')
        assert parsed_row == expected_rows[row_id]


@pytest.mark.usefixtures('payment_methods', 'vendors_and_exclusions')
def test_receipt_dump(t_file, transaction_fixture_dir):
    filename = os.path.join(transaction_fixture_dir, 'bmo_savings_2016-08.csv')
    parser_class = get_parser_class(filename)
    parser = parser_class()
    parser.parse(filename)

    dump_receipts(t_file, isodstr('2016-08-01'), isodstr('2016-09-01'), output_header=True)

    expected_rows = [
        ['Date', 'Asset', 'Currency', 'Amount', 'Transaction Party',
            'HST Amount (CAD)', 'Tax Category', 'Payment Method', 'Notes'],
        ['2016-08-02', '1001-25 Wellesley St', 'CAD', '-11.33', 'MTCC 452',
            '', 'Management and Administrative', 'BMO Savings', ''],
        ['2016-08-02', '1001-25 Wellesley St', 'CAD', '1600.00', 'Warren Smooth',
            '', 'Gross Rent', 'BMO Savings', ''],
        ['2016-08-02', '5-699 Amber St', 'CAD', '-2008.39', 'YRCC 994',
            '-231.05', 'Management and Administrative', 'BMO Savings', ''],
        ['2016-08-03', '5-699 Amber St', 'CAD', '308.90', 'FootBlind Finance Analytic',
            '35.54', 'Gross Rent', 'BMO Savings', ''],
        ['2016-08-15', '1001-25 Wellesley St', 'CAD', '-733.00', 'City of Toronto',
            '', 'Property Tax', 'BMO Savings', ''],
    ]
    t_file.seek(0)

    _verify_csv_output(t_file, expected_rows)


def test_dump_forex_rates(t_file):
    models.ForexRate.objects.bulk_create([
        models.ForexRate(effective_at=isodstr('2017-11-01'), pair='CAD/USD', rate=Decimal('1.2345')),
        models.ForexRate(effective_at=isodstr('2017-11-02'), pair='CAD/USD', rate=Decimal('1.4343')),
        models.ForexRate(effective_at=isodstr('2017-11-03'), pair='CAD/USD', rate=Decimal('1.5555')),
    ])

    dump_forex(t_file, isodstr('2017-11-01'), isodstr('2017-11-03'), output_header=True)

    expected_rows = [
        ['Date', 'Rate'],
        ['2017-11-01', '1.2345'],
        ['2017-11-02', '1.4343'],
        ['2017-11-03', '1.5555'],
    ]
    _verify_csv_output(t_file, expected_rows)
