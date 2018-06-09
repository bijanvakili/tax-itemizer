from django.db import models
from django.db.models import fields as django_fields

from taxes.receipts import constants
from . import fields, lookups, managers


__all__ = [
    'FinancialAsset',
    'Vendor',
    'VendorAliasPattern',
    'ExclusionCondition',
    'PaymentMethod',
    'PeriodicPayment',
    'Receipt',
    'ForexRate',
    'TaxAdjustment',
]


class SurrogateIdMixin(models.Model):
    """
    Base class for any model that requires a standard UUID surrogate primary key
    """
    class Meta:
        abstract = True

    id = fields.uuid_primary_key_field()


class FinancialAsset(SurrogateIdMixin):
    class Meta:
        db_table = 'financial_asset'

    name = models.CharField(max_length=200, unique=True, db_index=True)
    type = fields.enum_field(constants.FinancialAssetType)

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<FinancialAsset({id}, {name})>'.format(**self.__dict__)


class Vendor(SurrogateIdMixin):
    class Meta:
        db_table = 'vendor'

    name = models.CharField(max_length=200, unique=True, db_index=True)
    default_expense_type = fields.enum_field(constants.ExpenseType, db_index=True,
                                             null=True, blank=True)
    fixed_amount = models.IntegerField(null=True, default=None, blank=True)
    assigned_asset = models.ForeignKey('FinancialAsset', on_delete=models.SET_NULL,
                                       db_index=True, related_name='assigned_vendors',
                                       null=True, default=None, blank=True)
    tax_adjustment_type = fields.enum_field(constants.TaxType, null=True, blank=True)

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<Vendor({id}, {name})>'.format(**self.__dict__)


class VendorAliasPattern(SurrogateIdMixin):
    class Meta:
        db_table = 'vendor_alias_pattern'

    vendor = models.ForeignKey('Vendor', on_delete=models.CASCADE,
                               db_index=True, related_name='alias_patterns')
    pattern = models.CharField(max_length=200, unique=True, db_index=True)
    match_operation = fields.enum_field(constants.AliasMatchOperation, db_index=True, blank=False,
                                        default=constants.AliasMatchOperation.LIKE)
    default_expense_type = fields.enum_field(constants.ExpenseType, db_index=True,
                                             null=True, blank=True)

    def __str__(self):
        return f'{self.match_operation.name}("{self.pattern}")'

    def __repr__(self):
        return '<VendorAliasPattern({id}, {vendor}, {pattern}, {match_operation})>'.format(
            id=self.id,
            vendor=self.vendor.name,
            pattern=self.pattern,
            match_operation=self.match_operation.name
        )


class ExclusionCondition(SurrogateIdMixin):
    class Meta:
        db_table = 'exclusion_condition'

    # TODO enforce uppercase through validation
    prefix = models.CharField(max_length=200, db_index=True, null=True, blank=True)
    on_date = models.DateField(db_index=True, null=True, blank=True)
    amount = models.IntegerField(null=True, blank=True)

    def __repr__(self):
        return '<ExclusionCondition({id}, {on_date}, {prefix}, {amount})>'.format(
            **self.__dict__
        )


class PaymentMethod(SurrogateIdMixin):
    class Meta:
        db_table = 'payment_method'

    name = models.CharField(max_length=200, unique=True, db_index=True)
    description = models.TextField()
    type = fields.enum_field(constants.PaymentMethod)
    safe_numeric_id = models.CharField(max_length=4, db_index=True)
    currency = fields.enum_field(constants.Currency)

    def __repr__(self):
        return '<PaymentMethod({id}, {name})>'.format(**self.__dict__)


class Receipt(SurrogateIdMixin):
    objects = managers.ReceiptManager()

    class Meta:
        db_table = 'receipt'

    vendor = models.ForeignKey('Vendor', on_delete=models.PROTECT,
                               db_index=True, related_name='client_receipts')
    expense_type = fields.enum_field(constants.ExpenseType)
    # TODO rename this to transaction_date
    purchased_at = models.DateField(db_index=True)
    payment_method = models.ForeignKey('PaymentMethod', on_delete=models.PROTECT,
                                       db_index=True)
    # TODO should this be a DecimalField?
    total_amount = models.IntegerField()  # in cents
    currency = fields.enum_field(constants.Currency)

    def __repr__(self):
        return f'<Receipt({self.id}, {self.vendor.name}, {self.total_amount})>'


class PeriodicPayment(SurrogateIdMixin):
    class Meta:
        db_table = 'periodic_payment'
        index_together = ('currency', 'amount', )

    name = models.CharField(max_length=200, null=True)
    vendor = models.OneToOneField('Vendor', on_delete=models.PROTECT, db_index=True,
                                  related_name='periodic_payment')
    currency = fields.enum_field(constants.Currency)
    amount = models.IntegerField()

    def __str__(self):
        return f'{self.vendor.name} ({self.amount})'

    def __repr__(self):
        return f'<PeriodicPayment({self.id}, {self.vendor.name}, {self.amount})>'


class ForexRate(SurrogateIdMixin):
    objects = managers.ForexRateManager()

    class Meta:
        db_table = 'forex_rate'
        unique_together = ('pair', 'effective_at', )

    pair = models.CharField(max_length=8)  # e.g. CAD/USD
    effective_at = models.DateField(db_index=True)
    rate = models.DecimalField(max_digits=10, decimal_places=4)

    def __str__(self):
        return f'{self.pair},{self.effective_at:%Y-%m-%d}={self.rate:0.4f}'

    def __repr__(self):
        return f'<ForexRate({self.id}, {self.pair}, {self.effective_at})>'


class TaxAdjustment(SurrogateIdMixin):
    class Meta:
        db_table = 'tax_adjustment'
        ordering = ('receipt__purchased_at', 'receipt__vendor__name', 'tax_type',)

    receipt = models.ForeignKey('Receipt', on_delete=models.CASCADE,
                                db_index=True, related_name='tax_adjustments')
    tax_type = fields.enum_field(constants.TaxType)
    amount = models.IntegerField()  # in cents

    def __repr__(self):
        return f'<TaxAdjustment({self.tax_type}, {self.amount})>'


django_fields.CharField.register_lookup(lookups.AliasMatchLookup)
django_fields.CharField.register_lookup(lookups.PrefixMatchLookup)
