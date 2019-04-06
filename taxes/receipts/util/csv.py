from taxes.receipts.types import ItemizedReceiptRow, Transaction
from taxes.receipts.util.currency import cents_to_dollars


UNKNOWN_VALUE = '*UNKNOWN*'


def receipt_to_itemized_row(receipt, hst_amount) -> ItemizedReceiptRow:
    """
    Converts a receipt to an itemized receipt row for CSV output
    """
    financial_asset = receipt.vendor.assigned_asset
    return ItemizedReceiptRow(
        receipt.transaction_date.isoformat(),
        financial_asset.name if financial_asset else '',
        receipt.currency.value,
        cents_to_dollars(receipt.total_amount),
        receipt.vendor.name,
        cents_to_dollars(hst_amount) if hst_amount else '',
        receipt.expense_type.label,
        receipt.payment_method.name,
        '',
    )


def transaction_to_itemized_row(transaction: Transaction) -> ItemizedReceiptRow:
    """
    Converts an unmatched transaction to an itemized row
    """
    return ItemizedReceiptRow(
        transaction.transaction_date.isoformat(),
        UNKNOWN_VALUE,
        transaction.currency.value,
        cents_to_dollars(transaction.amount),
        transaction.description,
        '',
        UNKNOWN_VALUE,
        transaction.payment_method.name,
        ''
    )
