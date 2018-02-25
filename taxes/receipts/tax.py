from decimal import Decimal

from taxes.receipts import models, constants


def add_tax_adjustment(receipt: models.Receipt):
    """
    Adds a tax adjustment for a receipt with a periodic payment
    :param receipt: models.Receipt
    :return: new models.TaxAdjustment instance (saved to database)
    """
    vendor = receipt.vendor
    assert vendor.periodic_payment
    assert vendor.periodic_payment.tax_adjustment_type

    # apply any tax adjustments
    return models.TaxAdjustment.objects.create(
        receipt=receipt,
        tax_type=vendor.periodic_payment.tax_adjustment_type,
        amount=_compute_tax_adjustment_amount(receipt, vendor.periodic_payment.tax_adjustment_type)
    )


def _compute_tax_adjustment_amount(receipt: models.Receipt, tax_type: constants.TaxType.HST) -> int:
    if tax_type == constants.TaxType.HST:
        tax_amount = Decimal(receipt.total_amount) * (Decimal(1) - (Decimal(1) / Decimal(1.13)))
        return round(tax_amount)
