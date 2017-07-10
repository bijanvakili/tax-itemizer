import logging
import sys

from django.core.management.base import BaseCommand
from django.db import transaction

from taxes.receipts.parsers import get_parser_class

LOGGER = logging.getLogger(__name__)

SELECTABLE_LOGGING_LEVELS = {
    logging.getLevelName(level): level for level in [
        logging.WARN,
        logging.INFO,
        logging.ERROR
    ]
}


class Command(BaseCommand):
    help = 'Parses and itemizes transactions'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Do not store results in database')
        parser.add_argument('--log-level', help='Logging level')
        parser.add_argument('transaction_filenames', nargs='+')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        log_level = options['log_level']
        transaction_filenames = options['transaction_filenames']

        transaction.set_autocommit(False)
        if log_level:
            try:
                level = SELECTABLE_LOGGING_LEVELS[log_level.upper()]
            except KeyError:
                LOGGER.error('Invalid log level name: ' + log_level)
            else:
                root_logger = logging.getLogger('taxes.receipts')
                root_logger.setLevel(level)

        try:
            total_failures = self._import_files(transaction_filenames)
        except:
            transaction.rollback()
            LOGGER.exception('Unhandled exception')
            sys.exit(1)

        if dry_run or total_failures > 0:
            LOGGER.info('Rolling back...')
            transaction.rollback()
        else:
            transaction.commit()

        if total_failures:
            sys.exit(1)

    def _import_files(self, transaction_filenames):
        total_failures = 0
        for tx_filename in transaction_filenames:
            LOGGER.info(
                'Starting to process: {filename}...'.format(filename=tx_filename)
            )

            parser_class = get_parser_class(tx_filename)
            parser = parser_class()
            parser.parse(tx_filename)

            total_failures += parser.failures
            LOGGER.info(
                'Finished processing: {filename} {error_summary}'.format(
                    filename=tx_filename,
                    error_summary='({} errors)'.format(parser.failures) if parser.failures else ''
                )
            )
        return total_failures
