import csv
from enum import Enum, unique
import logging
import typing

from django.conf import settings
from django.core.management.base import BaseCommand
from oauth2client.service_account import ServiceAccountCredentials
import pygsheets
from pygsheets.client import SCOPES as PYGSHEETS_SCOPES


LOGGER = logging.getLogger(__name__)


@unique
class WorksheetType(Enum):
    """
    Worksheet type

    Value is the tab name in Google Sheets
    """
    items = 'Items'
    forex = 'FX'


WORKSHEET_COLUMN_FORMATS = {
    WorksheetType.items: [
        {'type': 'DATE', 'pattern': 'yyyy"-"mm"-"dd'},
        {'type': None, 'pattern': ''},
        {'type': 'NUMBER', 'pattern': '#,##0.00;(#,##0.00)'},
        {'type': None, 'pattern': ''},
        {'type': None, 'pattern': ''},
        {'type': 'NUMBER', 'pattern': '0.0000'},
        {'type': 'NUMBER', 'pattern': '#,##0.00;(#,##0.00)'},
        {'type': 'NUMBER', 'pattern': '#,##0.00;(#,##0.00)'},
        {'type': 'NUMBER', 'pattern': '0.0000'},
        {'type': 'NUMBER', 'pattern': '0.0000'},
    ],
    WorksheetType.forex: [
        {'type': 'DATE', 'pattern': 'yyyy"-"mm"-"dd'},
        {'type': 'NUMBER', 'pattern': '0.0000'}
    ]
}

GoogleSheetConfig = typing.NamedTuple('GoogleSheetConfig', [
    ('id', str),
    ('credentials_file', str)
])


class Command(BaseCommand):
    help = 'Upload data to Google Sheets'

    def add_arguments(self, parser):
        worksheet_choices = [e.name for e in WorksheetType]
        parser.add_argument('worksheet', choices=worksheet_choices, help='Worksheet tab')
        parser.add_argument('csv_filename', help='CSV dump file to upload')

    def handle(self, *args, **options):
        if not settings.SPREADSHEET:
            raise Exception('SPREADSHEET is not configured in JSON')

        with open(options['csv_filename'], newline='') as csv_file:
            self._upload_to_gsheet(
                GoogleSheetConfig(**settings.SPREADSHEET),
                WorksheetType[options['worksheet']],
                csv_file
            )

    def _upload_to_gsheet(self, config: GoogleSheetConfig, worksheet_type: WorksheetType, csv_file: typing.io):
        # connect to spreadsheet
        gdrive_credentials = self._load_credentials(config.credentials_file)
        gsheet_client = pygsheets.authorize(credentials=gdrive_credentials)
        spreadsheet = gsheet_client.open_by_key(config.id)
        worksheet = spreadsheet.worksheet_by_title(worksheet_type.value)

        reader = csv.reader(csv_file)
        all_data = [r for r in reader]
        num_rows = len(all_data)

        # look for the first row containing any empty rows in the spreadsheet
        first_empty_row = len(worksheet.get_col(1, include_empty=False)) + 1
        if first_empty_row + num_rows > worksheet.rows:
            worksheet.add_rows(num_rows)

        # upload the data into the target cell range
        worksheet.update_cells(
            crange=(first_empty_row, 1),
            values=all_data
        )

        # format the columns
        format_requests = []
        for col, col_format in enumerate(WORKSHEET_COLUMN_FORMATS[worksheet_type]):
            # grid range is half-open [start, end) where 'end' is exclusive
            # indices are zero-based
            col_range = {
                "sheetId": worksheet.id,
                "startRowIndex": first_empty_row - 1,
                "endRowIndex": first_empty_row + num_rows,
                "startColumnIndex": col,
                "endColumnIndex": col + 1,
            }
            format_requests.append({
                "repeatCell": {
                    "range": col_range,
                    "cell": {
                        "userEnteredFormat": {
                            "numberFormat": col_format
                        }
                    },
                    "fields": "userEnteredFormat.numberFormat"
                }
            })
        gsheet_client.sh_batch_update(spreadsheet.id, format_requests)

        # TODO add missing formulas

    @staticmethod
    def _load_credentials(credentials_filename):
        return ServiceAccountCredentials.from_json_keyfile_name(
            credentials_filename,
            PYGSHEETS_SCOPES
        )
