import csv
import logging

from django.core.management.base import BaseCommand
from django.db.models import Min

from taxes.receipts.management.shared import DBTransactionMixin
from taxes.receipts.util.datetime import parse_iso_datestring
from taxes.receipts.util.currency import parse_amount
from taxes.receipts import models, types

LOGGER = logging.getLogger(__name__)


# TODO Consider refactoring this to a general backfill for items and forex, etc.
class Command(DBTransactionMixin, BaseCommand):
    help = "Backfill HST"

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument("csv_file", help="CSV file in 2017 Items tab format")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        csv_filename = options["csv_file"]

        with self.ensure_atomic(dry_run, logger=LOGGER):
            self._backfill_hst(csv_filename)

    @staticmethod
    def parse_accounting_str_amount(amount_str):
        amount_str = amount_str.replace(",", "")
        if amount_str[0] == "(":
            return -1 * parse_amount(amount_str[1:-1])

        return parse_amount(amount_str)

    def _backfill_hst(self, csv_filename):
        min_receipt_date = models.Transaction.objects.aggregate(
            Min("transaction_date")
        )["transaction_date_at__min"]

        with open(csv_filename, "r") as csv_file:
            reader = csv.DictReader(csv_file)

            adjustments = []
            for row in reader:
                receipt_date = parse_iso_datestring(row["Date"])
                hst_amount = row["HST Amount (CAD)"]

                if hst_amount and receipt_date >= min_receipt_date:
                    LOGGER.info(
                        "Adding tax adjustment for %s, %s ...",
                        row["Date"],
                        row["Transaction Party"],
                    )

                    hst_amount = self.parse_accounting_str_amount(hst_amount)
                    total_amount = self.parse_accounting_str_amount(row["Amount (CAD)"])

                    receipt = models.Transaction.objects.get(
                        transaction_date=receipt_date,
                        currency=types.Currency.CAD,
                        vendor__name=row["Transaction Party"],
                        total_amount=total_amount,
                    )
                    adjustments.append(
                        models.TaxAdjustment(
                            receipt=receipt,
                            tax_type=types.TaxType.HST,
                            amount=hst_amount,
                        )
                    )

            models.TaxAdjustment.objects.bulk_create(adjustments)
