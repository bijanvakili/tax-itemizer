from django.conf import settings
import pytest

from taxes.receipts.data_loaders import DataLoadType, load_fixture


def _testfile_pathname(filename: str) -> str:
    return f'{settings.TEST_DATA_FIXTURE_DIR}/{filename}'


@pytest.fixture
def payment_methods():
    load_fixture(DataLoadType.PAYMENT_METHOD, _testfile_pathname('payment_methods.yaml'))


@pytest.fixture
def vendors_and_exclusions():
    load_fixture(DataLoadType.VENDOR, _testfile_pathname('vendors.yaml'))


@pytest.fixture(scope='session')
def transaction_fixture_dir():
    return _testfile_pathname('transactions')
