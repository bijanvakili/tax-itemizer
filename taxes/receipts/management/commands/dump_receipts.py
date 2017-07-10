import argparse

from django.core.management.base import BaseCommand

from taxes.receipts.data_reporters import dump_receipts as run_dump_receipts
from taxes.receipts.util.datetime import parse_iso_datestring


class ParseDateAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        try:
            date_str = parse_iso_datestring(values)
        except ValueError:
            raise ValueError(
                '{} needs to be an ISO 8061 date string (YYYY-MM-DD)'.format(self.dest)
            )

        setattr(namespace, self.dest, date_str)


class Command(BaseCommand):
    help = 'Export itemized receipts as CSV'

    def add_arguments(self, parser):
        parser.add_argument('--with-header', action='store_true', help='Include column headers in CSV output')
        parser.add_argument('receipts_filename', help='Output filename')
        parser.add_argument('start_date', action=ParseDateAction, help='Purchased at start date (inclusive)')
        parser.add_argument('end_date', action=ParseDateAction, help='Purchased at start date (inclusive)')

    def handle(self, *args, **options):
        with_header = options['with_header']
        receipts_filename = options['receipts_filename']
        start_date = options['start_date']
        end_date = options['end_date']

        with open(receipts_filename, 'w') as f:
            run_dump_receipts(f, start_date, end_date, output_header=with_header)
