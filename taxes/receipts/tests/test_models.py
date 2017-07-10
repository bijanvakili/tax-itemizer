import pytest

from . import factories


@pytest.fixture(autouse=True)
def data_loaders_setup(transactional_db):
    return


def test_site_summary():
    vendor = factories.VendorFactory.create()
    sites = factories.VendorSiteFactory.create_batch(
        3,
        vendor=vendor
    )
    all_site_ids = {s.id for s in sites}

    vendor.refresh_from_db()
    assert set(vendor.site_summary()) == all_site_ids
