from enum import Enum, unique

from django.core.management.base import BaseCommand

from taxes.receipts.csv_exporters import dump_receipts, dump_forex
from taxes.receipts.management.shared import DateRangeOutputMixin


@unique
class ExportType(Enum):
    """
    Export type
    """

    receipts = "receipts"
    forex = "forex"


COMMAND_MAP = {
    ExportType.receipts: dump_receipts,
    ExportType.forex: dump_forex,
}


class Command(DateRangeOutputMixin, BaseCommand):
    help = "Exports to a CSV"

    def add_arguments(self, parser):
        worksheet_choices = [e.name for e in ExportType]
        parser.add_argument(
            "export_type", choices=worksheet_choices, help="Export Type"
        )
        super().add_arguments(parser)

    def handle(self, *args, **options):
        f_dump = COMMAND_MAP[ExportType(options["export_type"])]
        with self.open_output(options["output_filename"]) as output_file:
            f_dump(
                output_file,
                options["start_date"],
                options["end_date"],
                output_header=options["with_header"],
            )
