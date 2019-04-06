from decimal import Decimal


def parse_amount(amount_string):
    return round(Decimal(amount_string) * 100)


def cents_to_dollars(amount_in_cents):
    return f'{amount_in_cents * 0.01:0.2f}'
