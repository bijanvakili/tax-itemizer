import csv
import datetime
from decimal import Decimal
import math
import typing

from django.core.management.base import BaseCommand
import requests

from .shared import DateRangeOutputMixin


BASE_CURRENCY = 'CAD'
QUOTE_CURRENCY = 'USD'

CURRENCY_PAIR = '{}/{}'.format(BASE_CURRENCY, QUOTE_CURRENCY)


class Command(DateRangeOutputMixin, BaseCommand):
    help = 'Downloads historical {} rates to a CSV file'.format(CURRENCY_PAIR)

    def handle(self, *args, **kwargs):
        with self.open_output(kwargs['output_filename']) as f:
            self._download_rates(f, kwargs['start_date'], kwargs['end_date'], output_header=kwargs['with_header'])

    @staticmethod
    def _download_rates(out_stream: typing.io, start_date: datetime.date, end_date: datetime.date,
                        output_header=False):
        params = {
            'widget': 1,
            'data_range': 'c',
            'quote_currency': QUOTE_CURRENCY,
            'base_currency_0': BASE_CURRENCY,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'period': 'daily',
            'price': 'mid',
            'source': 'OANDA',
            'display': 'absolute',
            'view': 'graph',
            'adjustment': 0,
            'base_currency_1': '',
            'base_currency_2': '',
            'base_currency_3': '',
            'base_currency_4': '',
            'base_currency_5': '',
            'base_currency_6': '',
            'base_currency_7': '',
            'base_currency_8': '',
            'base_currency_9': '',
        }

        response = requests.get(
            'https://www.oanda.com/fx-for-business/historical-rates/api/update/',
            params
        )
        response.raise_for_status()

        content = response.json()
        data = []
        for widgets in content['widget']:
            data.extend(widgets.get('data', []))

        rates = {}
        for row in data:
            date_key = datetime.datetime.utcfromtimestamp(
                math.floor(int(row[0]) / 1000)
            ).date()
            rates[date_key] = Decimal(row[1]).quantize(Decimal('1.0000'))

        # output the results
        writer = csv.DictWriter(out_stream, fieldnames=['date', 'rate'])
        if output_header:
            writer.writeheader()

        sorted_dates = sorted(rates.keys())
        for d in sorted_dates:
            writer.writerow({'date': d, 'rate': str(rates[d])})
