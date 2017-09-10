from django.core.management.base import BaseCommand

from taxes.receipts.data_reporters import dump_receipts as run_dump_receipts
from .shared import DateRangeOutputMixin


class Command(DateRangeOutputMixin, BaseCommand):
    help = 'Export itemized receipts as CSV'

    def handle(self, *args, **options):
        with self.open_output(options['output_filename']) as f:
            run_dump_receipts(
                f,
                options['start_date'],
                options['end_date'],
                output_header=options['with_header']
            )
