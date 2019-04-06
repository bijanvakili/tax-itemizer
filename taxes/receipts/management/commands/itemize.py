import csv
import logging
from io import StringIO
import sys
import typing

from django.core.management.base import BaseCommand
from django.db import transaction

from taxes.receipts.management.shared import DBTransactionMixin
from taxes.receipts.parsers_factory import ParserFactory
from taxes.receipts.itemize import Itemizer

LOGGER = logging.getLogger(__name__)

SELECTABLE_LOGGING_LEVELS = {
    logging.getLevelName(level): level for level in [
        logging.WARN,
        logging.INFO,
        logging.ERROR,
        logging.CRITICAL,
    ]
}


class Command(DBTransactionMixin, BaseCommand):
    help = 'Parses and itemizes transactions'

    def add_arguments(self, parser):
        parser.add_argument('--log-level', help='Logging level')
        parser.add_argument('--csv-output', action='store_true', help='CSV only output (include errors)')
        super().add_arguments(parser)
        parser.add_argument('transaction_filenames', nargs='+')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        log_level = options['log_level']
        use_csv_output = options['csv_output']
        transaction_filenames = options['transaction_filenames']

        if use_csv_output:
            # disable normal logging
            LOGGER.setLevel(logging.CRITICAL)
            log_level = 'CRITICAL'

        if log_level:
            try:
                level = SELECTABLE_LOGGING_LEVELS[log_level.upper()]
            except KeyError:
                LOGGER.error('Invalid log level name: %s', log_level)
            else:
                root_logger = logging.getLogger('taxes.receipts')
                root_logger.setLevel(level)

        with self.ensure_atomic(dry_run, logger=LOGGER):
            total_failures = self._import_files(transaction_filenames, use_csv_output)
            if total_failures > 0:
                LOGGER.info('Rolling back...')
                transaction.rollback()
                sys.exit(1)

    @staticmethod
    def _import_files(transaction_filenames: typing.List[str], use_csv_output: bool):
        total_failures = 0
        parser_factory = ParserFactory()
        csv_outputfile = StringIO() if use_csv_output else None

        for tx_filename in transaction_filenames:
            LOGGER.info('Starting to process: %s...', tx_filename)

            parser = parser_factory.get_parser(tx_filename)
            itemizer = Itemizer(tx_filename)
            itemizer.process_transactions(parser.parse(tx_filename), csv_outputfile=csv_outputfile)

            total_failures += parser.failures
            error_summary = \
                f'({parser.failures} parser errors, {itemizer.failures} itemization errors)' \
                if parser.failures + itemizer.failures else ''
            LOGGER.info(f'Finished processing: {tx_filename} {error_summary}')

        # output sorted csv file
        # TODO move Transaction to models and repalce receipt so this hack is no longer here
        if csv_outputfile:
            csv_outputfile.seek(0)
            reader = csv.reader(csv_outputfile)
            sorted_rows = sorted(
                [r for r in reader],
                key=lambda r: (r[0], r[4], r[3])
            )
            writer = csv.writer(sys.stdout)
            writer.writerows(sorted_rows)

        return total_failures
