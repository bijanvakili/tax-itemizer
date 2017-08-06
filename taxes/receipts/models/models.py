from django.db import models
from django.db.models import fields as django_fields

from taxes.receipts import constants
from . import fields, lookups


__all__ = [
    'FinancialAsset',
    'Vendor',
    'VendorAliasPattern',
    'ExclusionCondition',
    'PaymentMethod',
    'PeriodicPayment',
    'Receipt',
]


class FinancialAsset(models.Model):
    class Meta:
        db_table = 'financial_asset'

    id = fields.uuid_primary_key_field()
    name = models.CharField(max_length=200, unique=True, db_index=True)
    type = fields.enum_field(constants.FinancialAssetType)

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<FinancialAsset({id}, {name})>'.format(**self.__dict__)


class Vendor(models.Model):
    class Meta:
        db_table = 'vendor'

    id = fields.uuid_primary_key_field()
    name = models.CharField(max_length=200, unique=True, db_index=True)
    type = fields.enum_field(constants.VendorType, db_index=True)
    fixed_amount = models.IntegerField(null=True, default=None, blank=True)
    assigned_asset = models.ForeignKey('FinancialAsset', db_index=True, related_name='assigned_vendors',
                                       null=True, default=None, blank=True)

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<Vendor({id}, {name})>'.format(**self.__dict__)


class VendorAliasPattern(models.Model):
    class Meta:
        db_table = 'vendor_alias_pattern'

    id = fields.uuid_primary_key_field()
    vendor = models.ForeignKey('Vendor', db_index=True, related_name='alias_patterns')
    pattern = models.CharField(max_length=200, unique=True, db_index=True)
    match_operation = fields.enum_field(constants.AliasMatchOperation, db_index=True, blank=False,
                                        default=constants.AliasMatchOperation.LIKE)

    def __str__(self):
        return '{match_operation}("{pattern}")'.format(
            match_operation=self.match_operation.name,
            pattern=self.pattern
        )

    def __repr__(self):
        return '<VendorAliasPattern({id}, {vendor}, {pattern}, {match_operation})>'.format(
            id=self.id,
            vendor=self.vendor.name,
            pattern=self.pattern,
            match_operation=self.match_operation.name
        )


class ExclusionCondition(models.Model):
    class Meta:
        db_table = 'exclusion_condition'

    id = fields.uuid_primary_key_field()
    # TODO enforce uppercase through validation
    prefix = models.CharField(max_length=200, db_index=True, null=True, blank=True)
    on_date = models.DateField(db_index=True, null=True, blank=True)
    amount = models.IntegerField(null=True, blank=True)

    def __repr__(self):
        return '<ExclusionCondition({id}, {on_date}, {prefix}, {amount})>'.format(
            **self.__dict__
        )


class PaymentMethod(models.Model):
    class Meta:
        db_table = 'payment_method'

    id = fields.uuid_primary_key_field()
    name = models.CharField(max_length=200, unique=True, db_index=True)
    description = models.TextField()
    type = fields.enum_field(constants.PaymentMethod)
    safe_numeric_id = models.CharField(max_length=4, db_index=True)
    currency = fields.enum_field(constants.Currency)

    def __repr__(self):
        return '<PaymentMethod({id}, {name})>'.format(**self.__dict__)


class Receipt(models.Model):
    class Meta:
        db_table = 'receipt'

    id = fields.uuid_primary_key_field()
    vendor = models.ForeignKey('Vendor', db_index=True, related_name='client_receipts')
    purchased_at = models.DateField(db_index=True)
    payment_method = models.ForeignKey('PaymentMethod', db_index=True)
    # TODO should this be a DecimalField?
    total_amount = models.IntegerField()  # in cents
    currency = fields.enum_field(constants.Currency)

    def __repr__(self):
        return '<Receipt({id}, {vendor}, {amount})>'.format(
            id=self.id,
            vendor=self.vendor.name,
            amount=self.total_amount
        )


class PeriodicPayment(models.Model):
    class Meta:
        db_table = 'periodic_payment'
        index_together = ('currency', 'amount', )

    id = fields.uuid_primary_key_field()
    name = models.CharField(max_length=200, null=True)
    vendor = models.OneToOneField('Vendor', db_index=True)
    currency = fields.enum_field(constants.Currency)
    amount = models.IntegerField()

    def __str__(self):
        return '{vendor} ({amount})'.format(vendor=self.vendor.name, amount=self.amount)

    def __repr__(self):
        return '<PeriodicPayment({id}, {vendor}, {amount})>'.format(
            id=self.id,
            vendor=self.vendor.name,
            amount=self.amount
        )


django_fields.CharField.register_lookup(lookups.AliasMatchLookup)
django_fields.CharField.register_lookup(lookups.PrefixMatchLookup)
