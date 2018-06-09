from django.core.management.base import BaseCommand

from taxes.receipts.management.shared import DateRangeMixin
from taxes.receipts.forex import download_rates, CURRENCY_PAIR


class Command(DateRangeMixin, BaseCommand):
    help = f'Downloads historical {CURRENCY_PAIR} rates'

    def handle(self, *args, **kwargs):
        download_rates(kwargs['start_date'], kwargs['end_date'])
