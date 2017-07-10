import pytest

from taxes.receipts.data_loaders import load_fixture


@pytest.fixture
def payment_methods():
    load_fixture('tests/tests.payment_methods')


@pytest.fixture
def vendors_and_exclusions():
    load_fixture('tests/tests.vendors')


@pytest.fixture(scope='session')
def transaction_fixture_dir():
    return 'data/fixtures/tests/transactions'
