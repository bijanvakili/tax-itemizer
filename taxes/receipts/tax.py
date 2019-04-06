from decimal import Decimal

from taxes.receipts import models, types


def add_tax_adjustment(receipt: models.Receipt):
    """
    Adds a tax adjustment for a receipt with a periodic payment
    :param receipt: models.Receipt
    :return: new models.TaxAdjustment instance (saved to database)
    """
    vendor = receipt.vendor
    tax_adjustment_type = vendor.tax_adjustment_type
    assert tax_adjustment_type

    # apply any tax adjustments
    return models.TaxAdjustment.objects.create(
        receipt=receipt,
        tax_type=tax_adjustment_type,
        amount=_compute_tax_adjustment_amount(receipt, tax_adjustment_type)
    )


def _compute_tax_adjustment_amount(receipt: models.Receipt, tax_type: types.TaxType.HST) -> int:
    if tax_type == types.TaxType.HST:
        tax_amount = Decimal(receipt.total_amount) * (Decimal(1) - (Decimal(1) / Decimal(1.13)))
        return round(tax_amount)

    raise ValueError('Unsupported tax type')
