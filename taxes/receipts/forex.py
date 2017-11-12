import datetime
from decimal import Decimal
import logging
import math

import requests

from taxes.receipts import models


LOGGER = logging.getLogger(__name__)

# currently we only support CAD/USD
BASE_CURRENCY = 'CAD'
QUOTE_CURRENCY = 'USD'

CURRENCY_PAIR = f'{BASE_CURRENCY}/{QUOTE_CURRENCY}'


def download_rates(start_date: datetime.date, end_date: datetime.date):
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

    rates = []
    for row in data:
        rates.append(
            models.ForexRate(
                pair=CURRENCY_PAIR,
                effective_at=datetime.datetime.utcfromtimestamp(math.floor(int(row[0]) / 1000)).date(),
                rate=Decimal(row[1]).quantize(Decimal('1.0000'))
            )
        )

    # TODO support bulk upsert
    models.ForexRate.objects.bulk_create(rates, batch_size=100)
    LOGGER.info(f'Saved {len(rates)} new forex rates')
