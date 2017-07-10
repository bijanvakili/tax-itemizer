from datetime import datetime


def parse_iso_datestring(date_string):
    return parse_date(date_string, '%Y-%m-%d')


def parse_date(date_string, format):
    return datetime.strptime(date_string, format).date()
