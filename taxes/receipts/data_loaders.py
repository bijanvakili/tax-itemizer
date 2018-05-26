import abc
import datetime
from decimal import Decimal
import enum
import logging
import math
import os

import json


from taxes.receipts import constants, models
from taxes.receipts.util import currency, yaml


__all__ = [
    'DataLoadType',
    'load_fixture',
]


LOGGER = logging.getLogger(__name__)


@enum.unique
class DataLoadType(enum.Enum):
    PAYMENT_METHOD = 'payment_method'
    VENDOR = 'vendor'
    FOREX = 'forex'


class BaseDataLoader(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def load_fixture(self, filename: str):
        pass

    @abc.abstractmethod
    def load_data(self, data: dict):
        pass


class BaseYamlDataLoader(BaseDataLoader, metaclass=abc.ABCMeta):
    def load_fixture(self, filename: str):
        if not os.path.exists(filename):
            raise FileNotFoundError(filename)

        with open(filename, 'r') as f:
            data = yaml.load(f)
            self.load_data(data)


class BaseJsonDataLoader(BaseDataLoader, metaclass=abc.ABCMeta):
    def load_fixture(self, filename: str):
        if not os.path.exists(filename):
            raise FileNotFoundError(filename)

        with open(filename, 'r') as f:
            data = json.load(f)
            self.load_data(data)


class PaymentMethodYamlLoader(BaseYamlDataLoader):
    def load_data(self, data: dict):
        if not data.get('payment_methods'):
            raise ValueError('payment_methods not found')
        root = data['payment_methods']
        defaults = root['defaults']
        for o in root['objects']:
            item = defaults.copy()
            item.update(o)
            models.PaymentMethod.objects.create(**item)


class VendorYamlLoader(BaseYamlDataLoader):
    def load_data(self, data: dict):
        # NOTE: assumes all assets can fit into memory
        asset_map = {}

        all_assets = data['assets'] or []
        for financial_asset in all_assets:
            new_asset_params = {}
            new_asset_params['name'] = financial_asset['name']
            new_asset_params['type'] = constants.FinancialAssetType(financial_asset['type'])
            asset_map[new_asset_params['name']] = models.FinancialAsset.objects.create(**new_asset_params)

        all_vendors = data['vendors'] or []
        for vendor in all_vendors:
            new_vendor_params = {}
            new_vendor_params['name'] = vendor['name']
            new_vendor_params['type'] = constants.VendorType(vendor['type'])
            if vendor.get('merchant_id'):
                new_vendor_params['merchant_id'] = vendor['merchant_id']
            if vendor.get('fixed_amount'):
                new_vendor_params['fixed_amount'] = vendor['fixed_amount']
            if vendor.get('assigned_asset'):
                try:
                    new_vendor_params['assigned_asset'] = asset_map[vendor['assigned_asset']]
                except KeyError:
                    raise ValueError(f"Unable to locate financial asset: {vendor['assigned_asset']}")
            if vendor.get('tax_adjustment_type'):
                new_vendor_params['tax_adjustment_type'] = constants.TaxType(vendor['tax_adjustment_type'])
            new_vendor = models.Vendor.objects.create(**new_vendor_params)

            for alias in vendor.get('aliases', []):
                if type(alias) == str:
                    pattern = alias
                    match_operation = constants.AliasMatchOperation.EQUAL
                elif type(alias) == dict:
                    pattern = alias['pattern']
                    match_operation = alias['match_operation']
                else:
                    raise ValueError(f'Unable to parse alias: {alias}')
                models.VendorAliasPattern.objects.create(
                    vendor=new_vendor,
                    pattern=pattern,
                    match_operation=match_operation
                )

            for payment in vendor.get('regular_payments', []):
                new_periodic_payment = models.PeriodicPayment(
                    vendor=new_vendor,
                    amount=payment['amount'],
                    name=payment.get('name'),
                    currency=constants.Currency(payment['currency']),
                )
                new_periodic_payment.save()

        for exclusion in data['exclusions']:
            exclusion_kwargs = {'on_date': None, 'amount': None}
            if type(exclusion) == str:
                exclusion_kwargs['prefix'] = exclusion
            elif type(exclusion) == dict:
                exclusion_kwargs['prefix'] = exclusion.get('prefix')
                on_date_str = exclusion.get('on_date')
                if on_date_str:
                    exclusion_kwargs['on_date'] = datetime.datetime.strptime(
                        on_date_str,
                        '%Y-%m-%d'
                    ).date()
                amount_str = exclusion.get('amount')
                if amount_str:
                    exclusion_kwargs['amount'] = currency.parse_amount(amount_str)

            models.ExclusionCondition.objects.create(**exclusion_kwargs)


class ForexJsonLoader(BaseJsonDataLoader):
    def load_data(self, data: dict):
        rates = []
        for widget in data['widget']:
            if not widget:
                continue
            currency_pair = f"{widget['baseCurrency']}/{widget['quoteCurrency']}"
            for row in widget['data']:
                rates.append(
                    models.ForexRate(
                        pair=currency_pair,
                        effective_at=datetime.datetime.utcfromtimestamp(math.floor(int(row[0]) / 1000)).date(),
                        rate=Decimal(row[1]).quantize(Decimal('1.0000'))
                    )
                )

        # TODO support bulk upsert
        models.ForexRate.objects.bulk_create(rates, batch_size=100)
        LOGGER.info(f'Saved {len(rates)} new forex rates')


DATALOAD_TYPE_TO_LOADER = {
    DataLoadType.PAYMENT_METHOD: PaymentMethodYamlLoader,
    DataLoadType.VENDOR: VendorYamlLoader,
    DataLoadType.FOREX: ForexJsonLoader,
}


def _make_loader(load_type: DataLoadType) -> BaseDataLoader:
    try:
        loader_cls = DATALOAD_TYPE_TO_LOADER[load_type]
    except KeyError:
        raise ValueError('Unsupported data load type: ' + load_type.value)
    return loader_cls()


def load_data(load_type: DataLoadType, data: dict):
    loader = _make_loader(load_type)
    loader.load_data(data)


def load_fixture(load_type: DataLoadType, fixture_path: str):
    loader = _make_loader(load_type)
    loader.load_fixture(fixture_path)
