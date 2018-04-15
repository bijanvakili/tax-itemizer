import datetime
import logging

import requests

from taxes.receipts.data_loaders import load_data, DataLoadType


LOGGER = logging.getLogger(__name__)

# currently we only support USD/CAD
BASE_CURRENCY = 'USD'
QUOTE_CURRENCY = 'CAD'

CURRENCY_PAIR = f'{BASE_CURRENCY}/{QUOTE_CURRENCY}'


def download_rates(start_date: datetime.date, end_date: datetime.date):
    params = {
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
        'period': 'daily',
        'price': 'mid',
        'source': 'OANDA',
        'view': 'graph',
        'adjustment': 0,
        'base_currency': BASE_CURRENCY,
        'quote_currency_0': QUOTE_CURRENCY,
        'quote_currency_1': '',
        'quote_currency_2': '',
        'quote_currency_3': '',
        'quote_currency_4': '',
        'quote_currency_5': '',
        'quote_currency_6': '',
        'quote_currency_7': '',
        'quote_currency_8': '',
        'quote_currency_9': '',
    }

    response = requests.get(
        'https://www.oanda.com/fx-for-business/historical-rates/api/data/update/',
        params
    )
    response.raise_for_status()

    load_data(DataLoadType.FOREX, response.json())
