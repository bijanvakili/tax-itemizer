#!/usr/bin/python
import argparse
import datetime
import logging
import math
import requests
import sys


def get_rates(start_date, end_date):
    params = {
        'widget': 1,
        'data_range': 'c',
        'quote_currency': 'USD',
        'base_currency_0': 'CAD',
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
        'period': 'daily',
        'price': 'mid',
        'base_currency_1': '',
        'base_currency_2': '',
        'base_currency_3': '',
        'base_currency_4': '',
    }

    response = requests.get(
        'https://www.oanda.com/solutions-for-business/historical-rates-beta/api/update/',
        params
    )
    response.raise_for_status()

    content = response.json()
    data = []
    for widgets in content['widget']:
        data.extend(widgets.get('data', []))

    rates = {}
    for row in data:
        date_key = datetime.date.fromtimestamp(
            math.floor(int(row[0]) / 1000)
        )
        rates[date_key] = row[1]

    # output the results
    sorted_dates = sorted(rates.keys())
    for d in sorted_dates:
        print '{date_str},{rate:.4f}'.format(date_str=d, rate=rates[d])

def date_argument(value):
    try:
        return datetime.datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise argparse.ArgumentTypeError('{} not in YYYYMMDD format'.format(value))


def main():
    parser = argparse.ArgumentParser(description='Get Historical Rates')
    parser.add_argument('start_date', type=date_argument, help='Start date')
    parser.add_argument('end_date', type=date_argument, help='End date')

    args = parser.parse_args()
    get_rates(args.start_date, args.end_date)

if __name__ == '__main__':
    try:
        main()
    except Exception:
        logging.exception('Retrieving rates failed')
        sys.exit(1)


