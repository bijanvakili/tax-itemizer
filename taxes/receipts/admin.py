from django.contrib import admin
from enumfields.admin import EnumFieldListFilter

from . import models


@admin.register(models.PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ('name', 'method_type', 'safe_numeric_id', )
    ordering = ('name', )


@admin.register(models.ExclusionCondition)
class ExclusionConditionAdmin(admin.ModelAdmin):
    list_display = ('prefix', 'on_date', 'amount', )
    ordering = ('prefix', 'on_date', 'amount', )
    search_fields = ('prefix', )


class VendorAliasPatternInline(admin.StackedInline):
    model = models.VendorAliasPattern
    ordering = ('pattern', )


@admin.register(models.Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ('name', 'assigned_asset', 'default_expense_type', )
    ordering = ('name',)
    search_fields = ('name', )
    list_filter = (
        ('default_expense_type', EnumFieldListFilter,),
        'assigned_asset',
    )
    inlines = [VendorAliasPatternInline]
    raw_id_fields = ('assigned_asset', )


@admin.register(models.PeriodicPayment)
class PeriodicPaymentAdmin(admin.ModelAdmin):
    list_display = ('vendor', 'name', 'amount')
    ordering = ('vendor', 'name', 'currency', 'amount')
    raw_id_fields = ('vendor', )


@admin.register(models.Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ('transaction_date', 'expense_type', 'vendor', 'total_amount', 'currency')
    ordering = ('transaction_date', 'expense_type', 'vendor', 'total_amount', )
    raw_id_fields = ('vendor', 'payment_method', )
    search_fields = ('transaction_date', 'vendor__name',)


@admin.register(models.FinancialAsset)
class FinancialAssetAdmin(admin.ModelAdmin):
    ordering = ('name', )
    list_display = ('name', 'asset_type', )


@admin.register(models.ForexRate)
class ForexRateAdmin(admin.ModelAdmin):
    ordering = ('pair', 'effective_at')
    list_display = ('pair', 'effective_at', 'rate')


@admin.register(models.TaxAdjustment)
class TaxAdjustmentAdmin(admin.ModelAdmin):
    list_display = ('receipt_transaction_date', 'receipt_vendor_name', 'tax_type', 'amount',)
    ordering = ('receipt__transaction_date', )
    raw_id_fields = ('receipt',)

    # pylint: disable=no-self-use
    def receipt_transaction_date(self, obj):
        return obj.receipt.transaction_date
    receipt_transaction_date.short_description = 'Receipt Transaction Date'
    receipt_transaction_date.admin_order_field = 'receipt__transaction_date'

    def receipt_vendor_name(self, obj):
        return obj.receipt.vendor.name
    receipt_vendor_name.short_description = 'Receipt Vendor Name'
    # pylint: enable=no-self-use
