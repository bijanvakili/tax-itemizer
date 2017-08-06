from django.contrib import admin
from enumfields.admin import EnumFieldListFilter
from . import models


@admin.register(models.PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'safe_numeric_id', )
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
    list_display = ('name', 'type', 'assigned_asset', )
    ordering = ('name',)
    search_fields = ('name', )
    list_filter = (
        ('type', EnumFieldListFilter,),
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
    list_display = ('purchased_at', 'vendor', 'total_amount', 'currency')
    ordering = ('purchased_at', 'vendor', 'total_amount', )
    raw_id_fields = ('vendor', 'payment_method', )


@admin.register(models.FinancialAsset)
class FinancialAssetAdmin(admin.ModelAdmin):
    ordering = ('name', )
    list_display = ('name', 'type', )
