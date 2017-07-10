from datetime import date

import pytest

from taxes.receipts import constants, models


@pytest.fixture(autouse=True)
def data_loaders_setup(transactional_db):
    return


@pytest.mark.usefixtures('payment_methods')
def test_payment_method_yaml_load():
    # verify sample payment method
    result = models.PaymentMethod.objects.get(name='BMO Paypass Mastercard')

    assert result.name == 'BMO Paypass Mastercard'
    assert result.description == 'Canadian card for Canadian purchases'
    assert result.type == constants.PaymentMethod.CREDIT_CARD
    assert result.currency == constants.Currency.CAD
    assert result.safe_numeric_id == '0004'

    # verify total number of methods loaded
    assert models.PaymentMethod.objects.count() == 11


@pytest.mark.usefixtures('vendors_and_exclusions')
def test_custom_yaml_load():
    # verify sample vendors and aliases
    result = models.Vendor.objects.get(name='Xoom')

    assert result
    assert result.name == 'Xoom'
    assert result.type == constants.VendorType.ADMINISTRATIVE
    assert result.fixed_amount == -499

    alias_patterns = result.alias_patterns.all()
    assert len(alias_patterns) == 1
    alias = alias_patterns[0]
    assert alias.pattern == 'XOOM.COM DEBIT%'
    assert alias.match_operation == constants.AliasMatchOperation.LIKE

    result = models.Vendor.objects.get(name='We Be Sushi')

    assert result
    assert result.name == 'We Be Sushi'
    assert result.type == constants.VendorType.MEALS_AND_ENTERTAINMENT
    assert result.fixed_amount is None

    alias_patterns = result.alias_patterns.all()
    assert len(alias_patterns) == 1
    alias = alias_patterns[0]
    assert alias.pattern == 'WE BE SUSHI 5'
    assert alias.match_operation == constants.AliasMatchOperation.EQUAL

    # verify sample vendor's sites
    sites = result.sites.all()
    assert len(sites) == 1
    site = sites[0]
    assert site.address == {
        "street_1": "538 Valencia St.",
        "city": "San Francisco",
        "state": "CA",
        "zip": "94110"
    }
    assert site.contact_info == {
        "phone": "415.565.0749"
    }

    # verify a regular payment method and its associated vendor
    result = models.PeriodicPayment.objects.get(name='1001-25 Wellesley monthly rent')
    assert result
    assert result.name == '1001-25 Wellesley monthly rent'
    assert result.amount == 160000
    assert result.currency == constants.Currency.CAD
    assert result.vendor
    assert result.vendor.type == constants.VendorType.RENT

    # verify some sample exclusions
    assert models.ExclusionCondition.objects.filter(
        prefix='AMAZON',
        on_date=None
    ).exists()

    assert models.ExclusionCondition.objects.filter(
        prefix="MAVEN",
        on_date=date(2016, 9, 21)
    ).exists()

    assert models.ExclusionCondition.objects.filter(
        prefix=None,
        amount=4219,
        on_date=date(2016, 9, 15)
    ).exists()
