import csv
import datetime
import typing

from taxes.receipts.models import (
    Transaction,
    ForexRate,
    managers,
)


def dump_receipts(
    fileobj: typing.io,
    start_timestamp: datetime.date,
    end_timestamp: datetime.date,
    output_header: bool = False,
):
    _dump_as_csv(
        fileobj,
        start_timestamp,
        end_timestamp,
        Transaction.objects,
        output_header=output_header,
    )


def dump_forex(
    fileobj: typing.io,
    start_timestamp: datetime.date,
    end_timestamp: datetime.date,
    output_header: bool = False,
):
    _dump_as_csv(
        fileobj,
        start_timestamp,
        end_timestamp,
        ForexRate.objects,
        output_header=output_header,
    )


def _dump_as_csv(
    fileobj: typing.io,
    start_timestamp: datetime.date,
    end_timestamp: datetime.date,
    model_manager: managers.ReportMixinBase,
    output_header: bool = False,
):
    writer = csv.writer(fileobj)

    if output_header:
        writer.writerow(model_manager.headers)

    writer.writerows(model_manager.sorted_report(start_timestamp, end_timestamp))
