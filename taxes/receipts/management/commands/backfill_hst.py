import csv
import logging
import sys

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Min

from taxes.receipts.util.datetime import parse_iso_datestring
from taxes.receipts.util.currency import parse_amount
from taxes.receipts import models, constants

LOGGER = logging.getLogger(__name__)


# TODO Consider refactoring this to a general backfill for items and forex, etc.
# TODO Consider moving --dry-run transaction rollback functionality to a mixin class
class Command(BaseCommand):
    help = 'Backfill HST'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Do not store results in database')
        parser.add_argument('csv_file', help='CSV file in 2017 Items tab format')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        csv_filename = options['csv_file']

        transaction.set_autocommit(False)
        try:
            self._backfill_hst(csv_filename)
        except Exception:
            transaction.rollback()
            LOGGER.exception('Unhandled exception')
            sys.exit(1)

        if dry_run:
            LOGGER.info('Rolling back...')
            transaction.rollback()
        else:
            transaction.commit()

    @staticmethod
    def parse_accounting_str_amount(amount_str):
        amount_str = amount_str.replace(',', '')
        if amount_str[0] == '(':
            return -1 * parse_amount(amount_str[1:-1])
        else:
            return parse_amount(amount_str)

    def _backfill_hst(self, csv_filename):
        min_receipt_date = models.Receipt.objects.aggregate(Min('purchased_at'))['purchased_at__min']

        with open(csv_filename, 'r') as csv_file:
            reader = csv.DictReader(csv_file)

            adjustments = []
            for row in reader:
                receipt_date = parse_iso_datestring(row['Date'])
                hst_amount = row['HST Amount (CAD)']

                if hst_amount and receipt_date >= min_receipt_date:
                    LOGGER.info(
                        'Adding tax adjustment for %s, %s ...' %
                        (row['Date'], row['Transaction Party'])
                    )

                    hst_amount = self.parse_accounting_str_amount(hst_amount)
                    total_amount = self.parse_accounting_str_amount(row['Amount (CAD)'])

                    receipt = models.Receipt.objects.get(
                        purchased_at=receipt_date,
                        currency=constants.Currency.CAD,
                        vendor__name=row['Transaction Party'],
                        total_amount=total_amount,
                    )
                    adjustments.append(
                        models.TaxAdjustment(
                            receipt=receipt,
                            tax_type=constants.TaxType.HST,
                            amount=hst_amount
                        )
                    )

            models.TaxAdjustment.objects.bulk_create(adjustments)
