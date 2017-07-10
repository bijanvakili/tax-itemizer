from decimal import Decimal


def parse_amount(amount_string):
    return round(Decimal(amount_string) * 100)


def cents_to_dollars(amount_in_cents):
    return '{dollars:0n}.{cents:02n}'.format(
        dollars=int(amount_in_cents / 100),
        cents=amount_in_cents % 100
    )
