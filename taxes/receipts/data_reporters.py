import csv

from taxes.receipts import constants
from . import models

RECEIPT_DUMP_HEADERS = ['Date', 'Source', 'Amount (CAD)', 'Transaction Party', 'Notes', 'CAD/USD rate',
                        'Amount (USD)', 'HST Amount (CAD)', 'Tax Category', 'Payment Method']


def dump_receipts(fileobj, start_timestamp, end_timestamp, output_header=False):
    writer = csv.DictWriter(fileobj, fieldnames=RECEIPT_DUMP_HEADERS)
    if output_header:
        writer.writeheader()

    receipts = models.Receipt.objects \
        .select_related('vendor', 'payment_method') \
        .filter(purchased_at__range=(start_timestamp, end_timestamp)) \
        .order_by('purchased_at', 'vendor__name', 'total_amount')
    for receipt in receipts:
        row = {}
        row['Date'] = receipt.purchased_at.isoformat()

        # TODO update to include associated asset
        row['Source'] = ''

        amount_in_cents = '{0:.2f}'.format(receipt.total_amount * 0.01)
        if receipt.currency == constants.Currency.CAD:
            row['Amount (CAD)'] = amount_in_cents
            row['Amount (USD)'] = ''
        else:
            row['Amount (CAD)'] = ''
            row['Amount (USD)'] = amount_in_cents

        row['Transaction Party'] = receipt.vendor.name
        row['Notes'] = ''
        row['CAD/USD rate'] = ''
        row['HST Amount (CAD)'] = ''
        row['Tax Category'] = receipt.vendor.type.label
        row['Payment Method'] = receipt.payment_method.name

        writer.writerow(row)
