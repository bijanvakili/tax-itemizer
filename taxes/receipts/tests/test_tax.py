import datetime
import pytest

from taxes.receipts import types, models, tax
from taxes.receipts.tests import factories


pytestmark = pytest.mark.usefixtures(  # pylint: disable=invalid-name
    "transactional_db",
)


@pytest.mark.parametrize(
    "total_amount, expected_tax_adjustment", ((50850, 5850), (-22599, -2600),)
)
def test_hst_adjustment_basic(total_amount, expected_tax_adjustment):
    vendor = factories.VendorFactory.create(tax_adjustment_type=types.TaxType.HST)
    payment_method = factories.PaymentMethodFactory.create(currency=types.Currency.CAD)
    receipt = models.Transaction(
        vendor=vendor,
        transaction_type=vendor.default_expense_type,
        transaction_date=datetime.date.today(),
        payment_method=payment_method,
        total_amount=total_amount,
        currency=types.Currency.CAD,
    )
    receipt.save()

    adjustment = tax.add_tax_adjustment(receipt)

    assert adjustment
    assert isinstance(adjustment, models.TaxAdjustment)
    assert adjustment.receipt == receipt
    assert adjustment.tax_type == types.TaxType.HST
    assert adjustment.amount == expected_tax_adjustment


@pytest.mark.parametrize(
    "total_amount, expected_tax_adjustment", ((50850, 5850), (-22599, -2600),)
)
def test_hst_adjustment_periodic(total_amount, expected_tax_adjustment):
    vendor = factories.VendorFactory.create(tax_adjustment_type=types.TaxType.HST)
    periodic_payment = models.PeriodicPayment(
        name="test", vendor=vendor, currency=types.Currency.CAD, amount=total_amount,
    )
    periodic_payment.save()

    payment_method = factories.PaymentMethodFactory.create(currency=types.Currency.CAD)
    receipt = models.Transaction(
        vendor=vendor,
        transaction_type=vendor.default_expense_type,
        transaction_date=datetime.date.today(),
        payment_method=payment_method,
        total_amount=periodic_payment.amount,
        currency=periodic_payment.currency,
    )
    receipt.save()

    adjustment = tax.add_tax_adjustment(receipt)

    assert adjustment
    assert isinstance(adjustment, models.TaxAdjustment)
    assert adjustment.receipt == receipt
    assert adjustment.tax_type == types.TaxType.HST
    assert adjustment.amount == expected_tax_adjustment
