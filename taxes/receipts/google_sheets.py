import datetime
from enum import Enum, unique
import logging
import typing

from oauth2client.service_account import ServiceAccountCredentials
import pygsheets
from pygsheets.client import SCOPES as PYGSHEETS_SCOPES
import yaml

from taxes.receipts import models


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
        {'type': 'DATE', 'pattern': 'yyyy"-"mm"-"dd'},          # Date
        {'type': None, 'pattern': ''},                          # Asset
        {'type': None, 'pattern': ''},                          # Currency
        {'type': 'NUMBER', 'pattern': '#,##0.00;(#,##0.00)'},   # Amount
        {'type': None, 'pattern': ''},                          # Transaction Party
        {'type': 'NUMBER', 'pattern': '#,##0.00;(#,##0.00)'},   # HST Amount (CAD)
        {'type': None, 'pattern': ''},                          # Tax Category
        {'type': None, 'pattern': ''},                          # Payment Method
        {'type': None, 'pattern': ''},                          # Notes
    ],
    WorksheetType.forex: [
        {'type': 'DATE', 'pattern': 'yyyy"-"mm"-"dd'},          # Date
        {'type': 'NUMBER', 'pattern': '0.0000'}                 # CAD/USD Rate
    ]
}

GoogleSheetConfig = typing.NamedTuple('GoogleSheetConfig', [
    ('id', str),
    ('credentials_file', str)
])


WORKSHEET_SOURCE_MODELS = {
    WorksheetType.items: models.Receipt,
    WorksheetType.forex: models.ForexRate,
}


def upload_to_gsheet(
    config: GoogleSheetConfig,
    worksheet_type: WorksheetType,
    start_timestamp: datetime.date,
    end_timestamp: datetime.date,
):
    # connect to spreadsheet
    gdrive_credentials = _load_credentials(config.credentials_file)
    gsheet_client = pygsheets.authorize(credentials=gdrive_credentials)
    spreadsheet = gsheet_client.open_by_key(config.id)
    worksheet = spreadsheet.worksheet_by_title(worksheet_type.value)

    source_model = WORKSHEET_SOURCE_MODELS[worksheet_type]
    source_data = list(source_model.objects.sorted_report(start_timestamp, end_timestamp))
    flattened_data = []
    for row in source_data:
        flattened_data.append(list(row))
    num_rows = len(flattened_data)
    if not num_rows:
        LOGGER.warning('Range does not contain any data')
        return

    # look for the first row containing any empty rows in the spreadsheet
    first_empty_row = _get_first_empty_row(spreadsheet, worksheet)
    if first_empty_row + num_rows > worksheet.rows:
        worksheet.add_rows(num_rows)

    # upload the data into the target cell range
    worksheet.update_cells(
        crange=(first_empty_row, 1),
        values=flattened_data
    )

    # format the columns
    format_requests = []
    for col, col_format in enumerate(WORKSHEET_COLUMN_FORMATS[worksheet_type]):
        # grid range is half-open [start, end) where 'end' is exclusive
        # indices are zero-based
        col_range = _make_grid_range(worksheet, col, first_empty_row - 1, first_empty_row + num_rows)
        format_requests.append(_make_batch_format_request(col_range, col_format))
    gsheet_client.sh_batch_update(spreadsheet.id, format_requests)

    LOGGER.info(f'Finished uploading {num_rows} rows to Google Sheet')


def _load_credentials(credentials_filename):
    with open(credentials_filename) as credentials_file:
        credentials_data = yaml.safe_load(credentials_file)
        return ServiceAccountCredentials.from_json_keyfile_dict(
            credentials_data,
            PYGSHEETS_SCOPES
        )


def _get_first_empty_row(spreadsheet, worksheet):
    if type(worksheet) == WorksheetType:
        worksheet = spreadsheet.worksheet_by_title(worksheet.value)
    return len(worksheet.get_col(1, include_empty=False)) + 1


def _make_grid_range(
    worksheet,
    col: int,
    start_row: int,
    end_row: int,  # exclusive
):
    return {
        'sheetId': worksheet.id,
        'startRowIndex': start_row,
        'endRowIndex': end_row,
        'startColumnIndex': col,
        'endColumnIndex': col + 1,
    }


def _make_batch_format_request(grid_range: dict, format_spec: dict):
    return {
        'repeatCell': {
            'range': grid_range,
            'cell': {
                'userEnteredFormat': {
                    'numberFormat': format_spec,
                }
            },
            'fields': 'userEnteredFormat.numberFormat',
        }
    }


def _make_batch_formula_request(grid_range: dict, formula: str):
    return {
        'repeatCell': {
            'range': grid_range,
            'cell': {
                'userEnteredValue': {
                    'formulaValue': formula
                }
            },
            'fields': 'userEnteredValue.formulaValue'
        }
    }
