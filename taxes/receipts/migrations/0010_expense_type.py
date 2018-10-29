# Generated by Django 2.0.1 on 2018-06-09 20:41

from django.db import migrations
import enumfields.fields
import taxes.receipts.constants


def _expense_type_vendor_to_receipt(apps, schema_editor):
    Vendor = apps.get_model('receipts', 'Vendor')
    Receipt = apps.get_model('receipts', 'Receipt')
    db_alias = schema_editor.connection.alias

    for vendor in Vendor.objects.using(db_alias).iterator():
        vendor.default_expense_type = vendor.type
        vendor.save()

    for receipt in Receipt.objects.using(db_alias).iterator():
        receipt.expense_type = receipt.vendor.default_expense_type
        receipt.save()


class Migration(migrations.Migration):

    dependencies = [
        ('receipts', '0009_invert_fx_pairs'),
    ]

    operations = [
        migrations.AddField(
            model_name='receipt',
            name='expense_type',
            field=enumfields.fields.EnumField(default='ignore', enum=taxes.receipts.constants.ExpenseType, max_length=14),
            preserve_default=False,
        ),
        # use temporary default
        migrations.AddField(
            model_name='vendor',
            name='default_expense_type',
            field=enumfields.fields.EnumField(blank=True, db_index=True, enum=taxes.receipts.constants.ExpenseType, max_length=14, null=True),
        ),
        migrations.RunPython(
            _expense_type_vendor_to_receipt,
            _expense_type_vendor_to_receipt,
            elidable=True
        ),
        # remove temporary default
        migrations.AlterField(
            model_name='receipt',
            name='expense_type',
            field=enumfields.fields.EnumField(enum=taxes.receipts.constants.ExpenseType, max_length=14),
            preserve_default=False,
        ),
        migrations.RemoveField(
            model_name='vendor',
            name='type',
        ),
    ]