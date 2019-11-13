from datetime import datetime


def parse_iso_datestring(date_string):
    return parse_date(date_string, "%Y-%m-%d")


def parse_date(date_string, date_format):
    return datetime.strptime(date_string, date_format).date()
