import argparse
import contextlib
import sys
import typing

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


class DateRangeOutputMixin():
    def add_arguments(self, parser):
        parser.add_argument('--with-header', action='store_true', help='Include column headers in CSV output')
        parser.add_argument('start_date', action=ParseDateAction, help='Purchased at start date (inclusive)')
        parser.add_argument('end_date', action=ParseDateAction, help='Purchased at start date (inclusive)')
        parser.add_argument('output_filename', nargs='?', default=None, help='Output filename')

    @contextlib.contextmanager
    def open_output(self, output_filename: str) -> typing.ContextManager[typing.io]:
        if not output_filename:
            yield sys.stdout
        else:
            with open(output_filename, 'w') as f:
                yield f
