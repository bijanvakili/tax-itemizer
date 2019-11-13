import logging

from django.core.management.base import BaseCommand

from taxes.receipts.data_loaders import load_fixture, DataLoadType
from taxes.receipts.management.shared import DBTransactionMixin

LOGGER = logging.getLogger(__name__)


class Command(DBTransactionMixin, BaseCommand):
    help = "Imports fixture data"

    def add_arguments(self, parser):
        worksheet_choices = [e.value for e in DataLoadType]
        super().add_arguments(parser)
        parser.add_argument(
            "load_type", choices=worksheet_choices, help="Type of data to load"
        )
        parser.add_argument("fixtures", nargs="+")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        load_type = DataLoadType(options["load_type"])
        fixtures = options["fixtures"]

        with self.ensure_atomic(dry_run, logger=LOGGER):
            self._load_fixtures(load_type, fixtures)

    @staticmethod
    def _load_fixtures(load_type, fixtures):
        for fixture_name in fixtures:
            LOGGER.info("Loading fixture: %s...", fixture_name)
            load_fixture(load_type, fixture_name)
            LOGGER.info("Finished load for: %s", fixture_name)
