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
    forex = 'FX'
    items_raw = 'Items'
    items_cad = 'Items (CAD)'
    items_usd = 'Items (USD)'
    aggregate_cad = 'Aggregations (CAD)'
    aggregate_usd = 'Aggregations (USD)'


WORKSHEET_COLUMN_FORMATS = {
    WorksheetType.forex: [
        {'type': 'DATE', 'pattern': 'yyyy"-"mm"-"dd'},          # Date
        {'type': 'NUMBER', 'pattern': '0.0000'}                 # CAD/USD Rate
    ],
    WorksheetType.items_raw: [
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
    WorksheetType.items_cad: [
        {'type': 'DATE', 'pattern': 'yyyy"-"mm"-"dd'},  # Date
        {'type': None, 'pattern': ''},  # Asset
        {'type': 'NUMBER', 'pattern': '#,##0.00;(#,##0.00)'},  # Amount (CAD)
        {'type': None, 'pattern': ''},  # Transaction Party
        {'type': 'NUMBER', 'pattern': '#,##0.00;(#,##0.00)'},  # HST Amount (CAD)
        {'type': None, 'pattern': ''},  # Tax Category
    ],
    WorksheetType.items_usd: [
        {'type': 'DATE', 'pattern': 'yyyy"-"mm"-"dd'},  # Date
        {'type': None, 'pattern': ''},  # Asset
        {'type': 'NUMBER', 'pattern': '#,##0.00;(#,##0.00)'},  # Amount (USD)
        {'type': None, 'pattern': ''},  # Transaction Party
        {'type': None, 'pattern': ''},  # Tax Category
    ],
}

# templatized formulas
WORKSHEET_ITEM_COLUMN_FORMULAS = {
    WorksheetType.items_cad: [
        '={items}!$A2',  # Date
        '={items}!$B2',  # Asset
        # Amount (CAD)
        '={items}!$D2*IF({items}!C2="CAD",1,VLOOKUP({items}!$A2,{fx}!$A$2:$B${total_rows},2,TRUE))',
        '={items}!$E2',  # Transaction Party
        '={items}!$F2',  # HST
        '={items}!$G2',  # Tax Category
    ],
    WorksheetType.items_usd: [
        '={items}!$A2',  # Date
        '={items}!$B2',  # Asset
        # Amount (USD)
        '={items}!$D2*IF({items}!C2="USD",1,1/VLOOKUP({items}!$A2,{fx}!$A$2:$B${total_rows},2,TRUE))',
        '={items}!$E2',  # Transaction Party
        '={items}!$G2',  # Tax Category
    ],
}


ITEM_AMOUNT_COLUMNS = {
    WorksheetType.aggregate_cad: 'F',
    WorksheetType.aggregate_usd: 'E',
}

AGGREGATE_FORMULA = '=SUMIFS(\'{items_src}\'!$C$2:$C${total_items},' \
    ' \'{items_src}\'!${col_amount}$2:${col_amount}${total_items},' \
    '"="&$A2,\'{items_src}\'!$B$2:$B${total_items},"="&{col_asset}$1)'


AGGREGATE_FORMAT = {'type': 'NUMBER', 'pattern': '#,##0.00;(#,##0.00)'}

# TODO avoid hardcoding these
NUM_AGGREGATE_ASSETS = 4
NUM_AGGREGATE_TAX_CATEGORIES = 14

GoogleSheetConfig = typing.NamedTuple('GoogleSheetConfig', [
    ('id', str),
    ('credentials_file', str)
])


WORKSHEET_SOURCE_MODELS = {
    WorksheetType.items_raw: models.Receipt,
    WorksheetType.forex: models.ForexRate,
}


def upload_to_gsheet(
    config: GoogleSheetConfig,
    start_timestamp: datetime.date,
    end_timestamp: datetime.date,
):
    # connect to spreadsheet
    gdrive_credentials = _load_credentials(config.credentials_file)
    gsheet_client = pygsheets.authorize(credentials=gdrive_credentials)
    spreadsheet = gsheet_client.open_by_key(config.id)

    # upload to data worksheets
    _upload_to_worksheet(gsheet_client, spreadsheet, WorksheetType.forex,
                         start_timestamp, end_timestamp)
    _upload_to_worksheet(gsheet_client, spreadsheet, WorksheetType.items_raw,
                         start_timestamp, end_timestamp)

    # refresh formula worksheets
    total_items = _get_first_empty_row(spreadsheet, WorksheetType.items_raw)
    _refresh_items_worksheet(gsheet_client, spreadsheet, WorksheetType.items_cad, total_items)
    _refresh_items_worksheet(gsheet_client, spreadsheet, WorksheetType.items_usd, total_items)
    _refresh_aggregate_worksheet(gsheet_client, spreadsheet,
                                 WorksheetType.aggregate_cad, WorksheetType.items_cad, total_items)
    _refresh_aggregate_worksheet(gsheet_client, spreadsheet,
                                 WorksheetType.aggregate_usd, WorksheetType.items_usd, total_items)


def _upload_to_worksheet(
    gsheet_client,
    spreadsheet,
    worksheet_type: WorksheetType,
    start_timestamp: datetime.date,
    end_timestamp: datetime.date,

):
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

    LOGGER.info(f'Finished uploading {num_rows} rows to {worksheet_type.value} worksheet')


def _refresh_items_worksheet(
    gsheet_client,
    spreadsheet,
    worksheet_type: WorksheetType,
    total_items: int,
):
    worksheet = spreadsheet.worksheet_by_title(worksheet_type.value)
    num_columns = len(WORKSHEET_ITEM_COLUMN_FORMULAS[worksheet_type])
    column_instructions = zip(
        range(num_columns),
        WORKSHEET_ITEM_COLUMN_FORMULAS[worksheet_type],
        WORKSHEET_COLUMN_FORMATS[worksheet_type],
    )
    batch_requests = []

    # collect formula and format requests
    for col, col_formula, col_format in column_instructions:
        grid_range = _make_grid_range(worksheet, col, 1, total_items - 1)
        rendered_formula = col_formula.format(
            items=WorksheetType.items_raw.value,
            fx=WorksheetType.forex.value,
            total_rows=total_items
        )
        batch_requests += [
            _make_batch_formula_request(grid_range, rendered_formula),
            _make_batch_format_request(grid_range, col_format),
        ]

    gsheet_client.sh_batch_update(spreadsheet.id, batch_requests)
    LOGGER.info(f'Finished refreshing {worksheet_type.value} worksheet')


def _refresh_aggregate_worksheet(
    gsheet_client,
    spreadsheet,
    aggregate_type: WorksheetType,
    items_src_type: WorksheetType,
    total_items,
):
    worksheet = spreadsheet.worksheet_by_title(aggregate_type.value)
    batch_requests = []

    for col in range(NUM_AGGREGATE_ASSETS):
        grid_range = _make_grid_range(worksheet, col + 1, 1, NUM_AGGREGATE_TAX_CATEGORIES + 1)
        rendered_formula = AGGREGATE_FORMULA.format(
            items_src=items_src_type.value,
            total_items=total_items,
            col_amount=ITEM_AMOUNT_COLUMNS[aggregate_type],
            col_asset=chr(ord('B') + col),
        )
        batch_requests += [
            _make_batch_formula_request(grid_range, rendered_formula),
            _make_batch_format_request(grid_range, AGGREGATE_FORMAT),
        ]

    gsheet_client.sh_batch_update(spreadsheet.id, batch_requests)
    LOGGER.info(f'Finished refreshing {aggregate_type.value} worksheet')


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
