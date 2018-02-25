import datetime
import pytest

from taxes.receipts import (
    constants, models, tax
)
from taxes.receipts.tests import factories


@pytest.mark.parametrize('total_amount, expected_tax_adjustment', (
    (50850, 5850),
    (-22599, -2600),
))
def test_hst_adjustment(total_amount, expected_tax_adjustment, transactional_db):
    vendor = factories.VendorFactory.create()
    periodic_payment = models.PeriodicPayment(
        name='test',
        vendor=vendor,
        currency=constants.Currency.CAD,
        amount=total_amount,
        tax_adjustment_type=constants.TaxType.HST,
    )
    periodic_payment.save()

    payment_method = factories.PaymentMethodFactory.create(currency=constants.Currency.CAD)
    receipt = models.Receipt(
        vendor=vendor,
        purchased_at=datetime.date.today(),
        payment_method=payment_method,
        total_amount=periodic_payment.amount,
        currency=periodic_payment.currency,
    )
    receipt.save()

    adjustment = tax.add_tax_adjustment(receipt)

    assert adjustment
    assert isinstance(adjustment, models.TaxAdjustment)
    assert adjustment.receipt == receipt
    assert adjustment.tax_type == constants.TaxType.HST
    assert adjustment.amount == expected_tax_adjustment
