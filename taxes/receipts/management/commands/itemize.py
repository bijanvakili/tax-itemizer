import logging
import sys

from django.core.management.base import BaseCommand
from django.db import transaction

from taxes.receipts.management.shared import DBTransactionMixin
from taxes.receipts.parsers import get_parser_class

LOGGER = logging.getLogger(__name__)

SELECTABLE_LOGGING_LEVELS = {
    logging.getLevelName(level): level for level in [
        logging.WARN,
        logging.INFO,
        logging.ERROR
    ]
}


class Command(DBTransactionMixin, BaseCommand):
    help = 'Parses and itemizes transactions'

    def add_arguments(self, parser):
        parser.add_argument('--log-level', help='Logging level')
        super().add_arguments(parser)
        parser.add_argument('transaction_filenames', nargs='+')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        log_level = options['log_level']
        transaction_filenames = options['transaction_filenames']

        if log_level:
            try:
                level = SELECTABLE_LOGGING_LEVELS[log_level.upper()]
            except KeyError:
                LOGGER.error('Invalid log level name: %s', log_level)
            else:
                root_logger = logging.getLogger('taxes.receipts')
                root_logger.setLevel(level)

        with self.ensure_atomic(dry_run, logger=LOGGER):
            total_failures = self._import_files(transaction_filenames)
            if total_failures > 0:
                LOGGER.info('Rolling back...')
                transaction.rollback()
                sys.exit(1)

    @staticmethod
    def _import_files(transaction_filenames):
        total_failures = 0
        for tx_filename in transaction_filenames:
            LOGGER.info('Starting to process: %s...', tx_filename)

            parser_class = get_parser_class(tx_filename)
            parser = parser_class()
            parser.parse(tx_filename)

            total_failures += parser.failures
            error_summary = f'({parser.failures} errors)' if parser.failures else ''
            LOGGER.info(f'Finished processing: {tx_filename} {error_summary}')
        return total_failures
