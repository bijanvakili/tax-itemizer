import logging
import sys

from django.core.management.base import BaseCommand
from django.db import transaction

from taxes.receipts.data_loaders import load_fixture

LOGGER = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Imports fixture data'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Do not store results in database')
        parser.add_argument('fixtures', nargs='+')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        fixtures = options['fixtures']

        transaction.set_autocommit(False)
        try:
            self._load_fixtures(fixtures)
        except Exception:
            transaction.rollback()
            LOGGER.exception('Unhandled exception')
            sys.exit(1)

        if dry_run:
            LOGGER.info('Rolling back...')
            transaction.rollback()
        else:
            transaction.commit()

    def _load_fixtures(self, fixtures):
        for fixture_name in fixtures:
            LOGGER.info(f'Loading fixture: {fixture_name}...')
            load_fixture(fixture_name)
            LOGGER.info(f'Finished load for: {fixture_name}')
