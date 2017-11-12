import abc
import datetime
import os

from django.conf import settings
import yaml

from taxes.receipts import constants, models
from taxes.receipts.util import currency


class BaseYamlLoader(metaclass=abc.ABCMeta):
    def __init__(self):
        self.fixture_path = settings.DATA_FIXTURE_DIR

    def load_fixture(self, fixture_name: str):
        yaml_filename = os.path.join(self.fixture_path, f'{fixture_name}.yaml')
        if not os.path.exists(yaml_filename):
            raise FileNotFoundError(yaml_filename)

        with open(yaml_filename, 'r') as f:
            data = yaml.safe_load(f)
            self.load_data(data)

    @abc.abstractmethod
    def load_data(self, data):
        pass


class PaymentMethodYamlLoader(BaseYamlLoader):
    def load_data(self, data):
        if not data.get('payment_methods'):
            raise ValueError('payment_methods not found')
        root = data['payment_methods']
        defaults = root['defaults']
        for o in root['objects']:
            item = defaults.copy()
            item.update(o)
            models.PaymentMethod.objects.create(**item)


class CustomVendorYamlLoader(BaseYamlLoader):
    def load_data(self, data):
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
                models.PeriodicPayment.objects.create(
                    vendor=new_vendor,
                    amount=payment['amount'],
                    name=payment.get('name'),
                    currency=constants.Currency(payment['currency'])
                )

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


def load_fixture(fixture_name):
    if fixture_name.endswith('.vendors'):
        loader = CustomVendorYamlLoader()
    elif fixture_name.endswith('.payment_methods'):
        loader = PaymentMethodYamlLoader()
    else:
        raise ValueError('Unsupported fixture name: ' + fixture_name)

    loader.load_fixture(fixture_name)
