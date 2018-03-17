from django.conf import settings
from django.core.management.base import BaseCommand

from taxes.receipts import google_sheets
from .shared import DateRangeMixin


class Command(DateRangeMixin, BaseCommand):
    help = 'Upload data to Google Sheets'

    def handle(self, *args, **options):
        if not settings.SPREADSHEET:
            raise Exception('SPREADSHEET is not configured in JSON')

        google_sheets.upload_to_gsheet(
            google_sheets.GoogleSheetConfig(**settings.SPREADSHEET),
            options['start_date'],
            options['end_date'],
        )
