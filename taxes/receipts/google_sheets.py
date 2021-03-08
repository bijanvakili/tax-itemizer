import datetime
from enum import Enum, unique
import logging
import typing

import pygsheets

from taxes.receipts import models


LOGGER = logging.getLogger(__name__)


@unique
class WorksheetType(Enum):
    """
    Worksheet type

    Value is the tab name in Google Sheets
    """

    forex = "FX"
    items = "Items"
    aggregate_cad = "Aggregations (CAD)"
    aggregate_usd = "Aggregations (USD)"


@unique
class LineItemType(Enum):
    """
    Line item type
    """

    revenue = "revenue"
    cost = "cost"


WORKSHEET_COLUMN_FORMATS = {
    WorksheetType.forex: [
        {"type": "DATE", "pattern": 'yyyy"-"mm"-"dd'},  # Date
        {"type": "NUMBER", "pattern": "0.0000"},  # CAD/USD Rate
    ],
    WorksheetType.items: [
        {"type": "DATE", "pattern": 'yyyy"-"mm"-"dd'},  # Date
        {"type": None, "pattern": ""},  # Asset
        {"type": None, "pattern": ""},  # Currency
        {"type": "NUMBER", "pattern": "#,##0.00;(#,##0.00)"},  # Amount
        {"type": None, "pattern": ""},  # Transaction Party
        {"type": "NUMBER", "pattern": "#,##0.00;(#,##0.00)"},  # HST Amount (CAD)
        {"type": None, "pattern": ""},  # Tax Category
        {"type": None, "pattern": ""},  # Payment Method
        {"type": None, "pattern": ""},  # Notes
    ],
}

# templatized formulas
# pylint:disable=line-too-long
CONVERTER_SUBFORMULA = {
    WorksheetType.aggregate_cad: 'IF({items}!$C$2:$C${total_items}="CAD", 1, '
    "ARRAYFORMULA(VLOOKUP({items}!$A$2:$A${total_items},{fx}!$A$2:$B${total_rates},2,TRUE)))",
    WorksheetType.aggregate_usd: 'IF({items}!$C$2:$C${total_items}="USD", 1, '
    "ARRAYFORMULA(1/VLOOKUP({items}!$A$2:$A${total_items},{fx}!$A$2:$B${total_rates},2,TRUE)))",
}
# pylint:enable=line-too-long
AGGREGATE_FORMAT = {"type": "NUMBER", "pattern": "#,##0.00;(#,##0.00)"}

# flake8: noqa: E241
HST_FORMULA = {
    LineItemType.revenue: '=SUMIF(Items!$F$2:$F${total_items},">0")',
    LineItemType.cost: '=SUMIF(Items!$F$2:$F${total_items},"<0")',
}

HST_START_CELL = (25, 1)

EVEN_ROW_BACKGROUND = {"red": 0.8509804, "green": 0.91764706, "blue": 0.827451}

# TODO avoid hardcoding these
NUM_AGGREGATE_ASSETS = {
    WorksheetType.aggregate_cad: 2,
    WorksheetType.aggregate_usd: 5,
}

NUM_AGGREGATE_TAX_CATEGORIES = {
    WorksheetType.aggregate_cad: 14,
    WorksheetType.aggregate_usd: 19,
}

GoogleSheetConfig = typing.NamedTuple(
    "GoogleSheetConfig", [("id", str), ("credentials_file", str)]
)


WORKSHEET_SOURCE_MODELS = {
    WorksheetType.items: models.Transaction,
    WorksheetType.forex: models.ForexRate,
}


def upload_to_gsheet(
    config: GoogleSheetConfig,
    start_timestamp: datetime.date,
    end_timestamp: datetime.date,
):
    # connect to spreadsheet
    gsheet_client = pygsheets.authorize(service_file=config.credentials_file,)
    spreadsheet = gsheet_client.open_by_key(config.id)

    # upload to data worksheets
    _upload_to_worksheet(
        spreadsheet, WorksheetType.forex, start_timestamp, end_timestamp
    )
    _upload_to_worksheet(
        spreadsheet, WorksheetType.items, start_timestamp, end_timestamp
    )

    # refresh formula worksheets
    total_items = _get_first_empty_row(spreadsheet, WorksheetType.items) - 1
    total_rates = _get_first_empty_row(spreadsheet, WorksheetType.forex) - 1
    _refresh_aggregate_worksheet(
        spreadsheet, WorksheetType.aggregate_cad, total_items, total_rates,
    )
    _refresh_aggregate_worksheet(
        spreadsheet, WorksheetType.aggregate_usd, total_items, total_rates,
    )
    _refresh_aggregate_hst(spreadsheet, total_items)


def _upload_to_worksheet(
    spreadsheet,
    worksheet_type: WorksheetType,
    start_timestamp: datetime.date,
    end_timestamp: datetime.date,
):
    worksheet = spreadsheet.worksheet_by_title(worksheet_type.value)
    source_model = WORKSHEET_SOURCE_MODELS[worksheet_type]
    source_data = list(
        source_model.objects.sorted_report(start_timestamp, end_timestamp)
    )
    flattened_data = [list(row) for row in source_data]
    num_rows = len(flattened_data)
    if not num_rows:
        LOGGER.warning("Range does not contain any data")
        return

    # look for the first row containing any empty rows in the spreadsheet
    first_empty_row = _get_first_empty_row(spreadsheet, worksheet)
    if first_empty_row + num_rows > worksheet.rows:
        worksheet.add_rows(num_rows)

    # upload the data into the target cell range
    worksheet.update_values(crange=(first_empty_row, 1), values=flattened_data)

    # format the columns
    format_requests = []
    for col, col_format in enumerate(WORKSHEET_COLUMN_FORMATS[worksheet_type]):
        # grid range is half-open [start, end) where 'end' is exclusive
        # indices are zero-based
        col_range = _make_column_range(
            worksheet, col, first_empty_row - 1, first_empty_row + num_rows
        )
        format_requests.append(_make_batch_format_request(col_range, col_format))

    # extend the conditional formatting to the new number of rows
    format_requests.append(
        _make_conditional_format_request(
            _make_grid_range(
                worksheet,
                0,
                len(WORKSHEET_COLUMN_FORMATS[worksheet_type]),
                1,
                first_empty_row + num_rows - 1,
            )
        )
    )

    spreadsheet.custom_request(format_requests, "*")

    LOGGER.info(
        "Finished uploading %d rows to %s worksheet", num_rows, worksheet_type.value
    )


def _aggregate_formula(
    start_row: int,
    total_items: int,
    converter_formula: str,
    col_asset: str,
    exclude_hst: bool,
) -> str:
    template = "=SUM(IFERROR(FILTER(ARRAYFORMULA("
    if exclude_hst:
        template += "({items}!$D$2:$D${total_items}-{items}!$F$2:$F${total_items})"
    else:
        template += "{items}!$D$2:$D${total_items}"

    template += (
        " * "
        "{converter}), {items}!$B$2:$B${total_items} = "
        "{col_asset}$1, {items}!$G$2:$G${total_items} = $A{start_row}),0))"
    )
    return template.format(
        start_row=start_row,
        items=WorksheetType.items.value,
        total_items=total_items,
        converter=converter_formula,
        col_asset=col_asset,
    )


def _refresh_aggregate_worksheet(
    spreadsheet, aggregate_type: WorksheetType, total_items: int, total_rates: int,
):
    worksheet = spreadsheet.worksheet_by_title(aggregate_type.value)
    batch_requests = []

    converter_formula = CONVERTER_SUBFORMULA[aggregate_type].format(
        items=WorksheetType.items.value,
        fx=WorksheetType.forex.value,
        total_items=total_items,
        total_rates=total_rates,
    )

    # special behavior to exclude HST from Gross rent
    for col in range(NUM_AGGREGATE_ASSETS[aggregate_type]):
        grid_range = _make_column_range(worksheet, col + 1, 1, 2)
        rendered_formula = _aggregate_formula(
            2, total_items, converter_formula, chr(ord("B") + col), True,
        )
        batch_requests += [
            _make_batch_formula_request(grid_range, rendered_formula),
            _make_batch_format_request(grid_range, AGGREGATE_FORMAT),
        ]

    # include HST for all other tax categories
    for col in range(NUM_AGGREGATE_ASSETS[aggregate_type]):
        grid_range = _make_column_range(
            worksheet, col + 1, 2, NUM_AGGREGATE_TAX_CATEGORIES[aggregate_type] + 1
        )
        rendered_formula = _aggregate_formula(
            3, total_items, converter_formula, chr(ord("B") + col), False,
        )
        batch_requests += [
            _make_batch_formula_request(grid_range, rendered_formula),
            _make_batch_format_request(grid_range, AGGREGATE_FORMAT),
        ]

    spreadsheet.custom_request(batch_requests, "*")
    LOGGER.info("Finished refreshing %s worksheet", aggregate_type.value)


def _refresh_aggregate_hst(
    spreadsheet, total_items: int,
):
    worksheet = spreadsheet.worksheet_by_title(WorksheetType.aggregate_cad.value)
    batch_requests = []

    hst_range = _make_grid_range(
        worksheet,
        HST_START_CELL[1],
        HST_START_CELL[1] + 1,
        HST_START_CELL[0],
        HST_START_CELL[0] + 1,
    )
    batch_requests.append(
        _make_batch_formula_request(
            hst_range, HST_FORMULA[LineItemType.revenue].format(total_items=total_items)
        )
    )

    hst_range = _make_grid_range(
        worksheet,
        HST_START_CELL[1],
        HST_START_CELL[1] + 1,
        HST_START_CELL[0] + 1,
        HST_START_CELL[0] + 2,
    )
    batch_requests.append(
        _make_batch_formula_request(
            hst_range, HST_FORMULA[LineItemType.cost].format(total_items=total_items)
        )
    )
    hst_range = _make_grid_range(
        worksheet,
        HST_START_CELL[1],
        HST_START_CELL[1] + 1,
        HST_START_CELL[0],
        HST_START_CELL[0] + 2,
    )
    batch_requests.append(_make_batch_format_request(hst_range, AGGREGATE_FORMAT),)

    spreadsheet.custom_request(batch_requests, "*")
    LOGGER.info("Finished refreshing HST formulas")


def _get_first_empty_row(spreadsheet, worksheet):
    if isinstance(worksheet, WorksheetType):
        worksheet = spreadsheet.worksheet_by_title(worksheet.value)
    return len(worksheet.get_col(1, include_empty=False)) + 1


def _make_grid_range(
    worksheet, start_col: int, end_col: int, start_row: int, end_row: int
):
    """
    Constructs a grid range for Google sheets

    :param worksheet:
    :param start_col: inclusive
    :param end_col: exclusive
    :param start_row: inclusive
    :param end_row: exclusive
    :return:
    """
    return {
        "sheetId": worksheet.id,
        "startRowIndex": start_row,
        "endRowIndex": end_row,
        "startColumnIndex": start_col,
        "endColumnIndex": end_col,
    }


def _make_column_range(worksheet, col: int, start_row: int, end_row: int):
    """
    Constructs a single column grid range for Google Sheets

    :param worksheet:
    :param col:
    :param start_row:
    :param end_row: this is exclusive
    :return:
    """
    return _make_grid_range(worksheet, col, col + 1, start_row, end_row)


def _make_batch_format_request(grid_range: dict, format_spec: dict):
    return {
        "repeatCell": {
            "range": grid_range,
            "cell": {"userEnteredFormat": {"numberFormat": format_spec,}},
            "fields": "userEnteredFormat.numberFormat",
        }
    }


def _make_batch_formula_request(grid_range: dict, formula: str):
    return {
        "repeatCell": {
            "range": grid_range,
            "cell": {"userEnteredValue": {"formulaValue": formula}},
            "fields": "userEnteredValue.formulaValue",
        }
    }


def _make_conditional_format_request(grid_range: dict):
    """
    Conditional formatting rule to color every other row

    NOTE: This assumes that only 1 rule exists on the worksheep specified in the range
    """
    return {
        "updateConditionalFormatRule": {
            "index": 0,
            "sheetId": 0,
            "rule": {
                "ranges": [grid_range],
                "booleanRule": {
                    "condition": {
                        "type": "CUSTOM_FORMULA",
                        "values": [{"userEnteredValue": "=ISEVEN(ROW())"}],
                    },
                    "format": {"backgroundColor": EVEN_ROW_BACKGROUND},
                },
            },
        }
    }
