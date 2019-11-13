from datetime import date
from decimal import Decimal
import logging

from django.conf import settings
import pytest

from taxes.receipts import (
    types,
    data_loaders,
    models,
)
from .logging import log_contains_message, MockLogger


@pytest.fixture(autouse=True)
def data_loaders_setup(transactional_db):  # pylint: disable=unused-argument
    return


@pytest.fixture()
def mock_logger(monkeypatch):
    mock = MockLogger()
    monkeypatch.setattr(data_loaders, "LOGGER", mock)
    return mock


@pytest.mark.usefixtures("payment_methods")
def test_payment_method_yaml_load():
    # verify sample payment method
    result = models.PaymentMethod.objects.get(name="BMO Paypass Mastercard")

    assert result.name == "BMO Paypass Mastercard"
    assert result.description == "Canadian card for Canadian purchases"
    assert result.method_type == types.PaymentMethod.CREDIT_CARD
    assert result.currency == types.Currency.CAD
    assert result.safe_numeric_id == "0004"

    # verify total number of methods loaded
    assert models.PaymentMethod.objects.count() == 10


# pylint: disable=too-many-statements
@pytest.mark.usefixtures("vendors_and_exclusions")
def test_vendor_yaml_load():
    # verify sample financial assets
    result = models.FinancialAsset.objects.get(name="1001-25 Wellesley St")

    assert result.name == "1001-25 Wellesley St"
    assert result.asset_type == types.FinancialAssetType.RENTAL

    # verify sample vendors and aliases
    result = models.Vendor.objects.get(name="Xoom")

    assert result
    assert result.name == "Xoom"
    assert result.default_expense_type == types.ExpenseType.ADMINISTRATIVE
    assert result.fixed_amount == -499
    assert result.assigned_asset.name == "1001-25 Wellesley St"

    alias_patterns = result.alias_patterns.all()
    assert len(alias_patterns) == 1
    alias = alias_patterns[0]
    assert alias.pattern == "XOOM.COM DEBIT%"
    assert alias.match_operation == types.AliasMatchOperation.LIKE
    assert alias.default_expense_type is None

    result = models.Vendor.objects.get(name="We Be Sushi")

    assert result
    assert result.name == "We Be Sushi"
    assert result.default_expense_type == types.ExpenseType.MEALS_AND_ENTERTAINMENT
    assert result.fixed_amount is None
    assert result.assigned_asset.name == "Sole Proprietorship"

    alias_patterns = result.alias_patterns.all()
    assert len(alias_patterns) == 1
    alias = alias_patterns[0]
    assert alias.pattern == "WE BE SUSHI 5"
    assert alias.match_operation == types.AliasMatchOperation.EQUAL
    assert alias.default_expense_type is None

    # verify a regular payment method and its associated vendor
    result = models.PeriodicPayment.objects.get(name="1001-25 Wellesley monthly rent")
    assert result
    assert result.name == "1001-25 Wellesley monthly rent"
    assert result.amount == 160000
    assert result.currency == types.Currency.CAD
    assert result.vendor
    assert result.vendor.default_expense_type == types.ExpenseType.RENT
    assert result.vendor.tax_adjustment_type is None

    # verify some sample exclusions
    assert models.ExclusionCondition.objects.filter(
        prefix="AMAZON", on_date=None
    ).exists()

    assert models.ExclusionCondition.objects.filter(
        prefix="MAVEN", on_date=date(2016, 9, 21)
    ).exists()

    assert models.ExclusionCondition.objects.filter(
        prefix=None, amount=4219, on_date=date(2016, 9, 15)
    ).exists()

    result = models.PeriodicPayment.objects.get(name="5-699 Amber St monthly rent")
    assert result
    assert result.vendor.name == "FootBlind Finance Analytic"
    assert result.vendor.tax_adjustment_type == types.TaxType.HST

    results = models.VendorAliasPattern.objects.filter(
        vendor__name="Wells Fargo"
    ).order_by("pattern")

    assert len(results) == 2

    assert results[0].pattern == "ANNUAL FEE FOR%"
    assert results[0].match_operation == types.AliasMatchOperation.LIKE
    assert results[0].default_expense_type == types.ExpenseType.ADMINISTRATIVE

    assert results[1].pattern == "INTEREST PAYMENT"
    assert results[1].match_operation == types.AliasMatchOperation.EQUAL
    assert results[1].default_expense_type == types.ExpenseType.CAPITAL_GAINS


# pylint: enable=too-many-statements


# pylint: disable=redefined-outer-name
def test_forex_json_load(mock_logger):
    forex_json_filename = f"{settings.TEST_DATA_FIXTURE_DIR}/forex.json"
    data_loaders.load_fixture(data_loaders.DataLoadType.FOREX, forex_json_filename)

    # verify loaded rates
    all_rates = models.ForexRate.objects.order_by("effective_at").all()
    assert len(all_rates) == 31

    assert all_rates[0].effective_at.isoformat() == "2018-03-01"
    assert all_rates[0].pair == "USD/CAD"
    assert all_rates[0].rate == Decimal("1.2844")

    assert all_rates[30].effective_at.isoformat() == "2018-03-31"
    assert all_rates[30].pair == "USD/CAD"
    assert all_rates[30].rate == Decimal("1.2898")

    assert log_contains_message(
        mock_logger,
        f"Saved %d new forex rates",
        level=logging.INFO,
        expected_args=(len(all_rates),),
    )


# pylint: enable=redefined-outer-name
