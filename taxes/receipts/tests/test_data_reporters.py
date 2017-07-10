from io import StringIO
import os

import pytest

from taxes.receipts.data_reporters import dump_receipts
from taxes.receipts.parsers import get_parser_class
from taxes.receipts.util.datetime import parse_iso_datestring


@pytest.fixture
def t_file():
    return StringIO()


@pytest.fixture(autouse=True)
def data_loaders_setup(transactional_db):
    return


@pytest.mark.usefixtures('payment_methods', 'vendors_and_exclusions')
def test_receipt_dump(t_file, transaction_fixture_dir):
    filename = os.path.join(transaction_fixture_dir, 'bmo_savings_2016-08.csv')
    parser_class = get_parser_class(filename)
    parser = parser_class()
    parser.parse(filename)

    output_file = t_file
    dump_receipts(output_file,
                  parse_iso_datestring('2016-08-01'),
                  parse_iso_datestring('2016-09-01'),
                  output_header=True)

    # TODO update to include associated asset
    expected_rows = [
        ['Date', 'Source', 'Amount (CAD)', 'Transaction Party', 'Notes', 'CAD/USD rate', 'Amount (USD)',
            'HST Amount (CAD)', 'Tax Category', 'Payment Method'],
        ['2016-08-02', '', '-11.33', 'MTCC 452', '', '', '', '',
            'Management and Administrative', 'BMO Savings'],
        ['2016-08-02', '', '1600.00', 'Warren Smooth', '', '', '', '',
            'Gross Rent', 'BMO Savings'],
        ['2016-08-02', '', '-2008.39', 'YRCC 994', '', '', '', '',
            'Management and Administrative', 'BMO Savings'],
        ['2016-08-03', '', '308.90', 'FootBlind Finance Analytic', '', '', '', '',
            'Gross Rent', 'BMO Savings'],
        ['2016-08-15', '', '-733.00', 'City of Toronto', '', '', '', '',
            'Property Tax', 'BMO Savings'],
    ]
    output_file.seek(0)

    max_rows = len(expected_rows)
    for row_id, row in enumerate(output_file):
        assert row_id < max_rows
        parsed_row = row.strip().split(',')
        assert parsed_row == expected_rows[row_id]
