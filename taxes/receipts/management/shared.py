import argparse
import contextlib
import logging
import sys
import typing

from django.db import transaction

from taxes.receipts.util.datetime import parse_iso_datestring


LOGGER = logging.getLogger(__name__)


class ParseDateAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        try:
            date_str = parse_iso_datestring(values)
        except ValueError:
            raise ValueError(f'{self.dest} needs to be an ISO 8061 date string (YYYY-MM-DD)')

        setattr(namespace, self.dest, date_str)


class DateRangeMixin:
    def add_arguments(self, parser):  # pylint: disable=no-self-use
        parser.add_argument('start_date', action=ParseDateAction,
                            help='Purchased at start date (inclusive)')
        parser.add_argument('end_date', action=ParseDateAction,
                            help='Purchased at start date (inclusive)')


class DateRangeOutputMixin(DateRangeMixin):
    def add_arguments(self, parser):  # pylint: disable=no-self-use
        parser.add_argument('--with-header', action='store_true',
                            help='Include column headers in CSV output')
        super().add_arguments(parser)
        parser.add_argument('output_filename', nargs='?', default=None, help='Output filename')

    @staticmethod
    @contextlib.contextmanager
    def open_output(output_filename: str) -> typing.ContextManager[typing.io]:
        if not output_filename:
            yield sys.stdout
        else:
            with open(output_filename, 'w') as output_file:
                yield output_file


class DBTransactionMixin:
    def add_arguments(self, parser):  # pylint: disable=no-self-use
        parser.add_argument('--dry-run', action='store_true',
                            help='Do not store results in database')

    @staticmethod
    @contextlib.contextmanager
    def ensure_atomic(is_dry_run: bool, logger=None):
        logger = logger or LOGGER
        transaction.set_autocommit(False)
        try:
            yield transaction
        except Exception:
            transaction.rollback()
            logger.exception('Unhandled exception')
            sys.exit(1)

        if is_dry_run:
            logger.info('Rolling back...')
            transaction.rollback()
        else:
            transaction.commit()
