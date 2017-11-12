from django.conf import settings
from django.core.management.base import BaseCommand

from taxes.receipts import google_sheets
from .shared import DateRangeMixin


class Command(DateRangeMixin, BaseCommand):
    help = 'Upload data to Google Sheets'

    def add_arguments(self, parser):
        worksheet_choices = [e.name for e in google_sheets.WorksheetType]
        parser.add_argument('worksheet', choices=worksheet_choices, help='Worksheet tab')
        super().add_arguments(parser)

    def handle(self, *args, **options):
        if not settings.SPREADSHEET:
            raise Exception('SPREADSHEET is not configured in JSON')

        google_sheets.upload_to_gsheet(
            google_sheets.GoogleSheetConfig(**settings.SPREADSHEET),
            google_sheets.WorksheetType[options['worksheet']],
            options['start_date'],
            options['end_date'],
        )
