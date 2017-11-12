import csv
import datetime
import typing

from . import models

RECEIPT_DUMP_HEADERS = ['Date', 'Source', 'Amount (CAD)', 'Transaction Party', 'Notes', 'CAD/USD rate',
                        'Amount (USD)', 'HST Amount (CAD)', 'Tax Category', 'Payment Method']

FOREX_DUMP_HEADERS = ['Date', 'Rate']


def dump_receipts(
    fileobj: typing.io,
    start_timestamp: datetime.date,
    end_timestamp: datetime.date,
    output_header: bool=False
):
    writer = csv.DictWriter(fileobj, fieldnames=RECEIPT_DUMP_HEADERS)
    if output_header:
        writer.writeheader()

    rows = models.Receipt.objects.sorted_report(start_timestamp, end_timestamp)
    writer.writerows(rows)


def dump_forex(
    fileobj: typing.io,
    start_timestamp: datetime.date,
    end_timestamp: datetime.date,
    output_header: bool=False
):
    writer = csv.DictWriter(fileobj, fieldnames=FOREX_DUMP_HEADERS)
    if output_header:
        writer.writeheader()

    rows = models.ForexRate.objects.sorted_report(start_timestamp, end_timestamp)
    writer.writerows(rows)
