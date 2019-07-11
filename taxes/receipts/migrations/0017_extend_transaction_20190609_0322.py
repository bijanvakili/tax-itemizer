# Generated by Django 2.2.2 on 2019-06-09 03:22

from django.db import migrations, models
import django.db.models.deletion
import enumfields.fields
import taxes.receipts.types


def _populate_description(apps, schema_editor):
    Transaction = apps.get_model('receipts', 'Transaction')
    db_alias = schema_editor.connection.alias

    transactions_with_vendors = Transaction.objects.using(db_alias).filter(
        vendor__isnull=False,
    )
    for transaction in transactions_with_vendors.iterator():
        transaction.description = transaction.vendor.name
        transaction.save()


class Migration(migrations.Migration):

    dependencies = [
        ('receipts', '0016_rename_transaction_20190607_0624'),
    ]

    operations = [
        migrations.AddField(
            model_name='transaction',
            name='description',
            field=models.TextField(default='*UNKNOWN*'),
        ),
        migrations.AlterField(
            model_name='transaction',
            name='expense_type',
            field=enumfields.fields.EnumField(enum=taxes.receipts.types.ExpenseType, max_length=14, null=True),
        ),
        migrations.AlterField(
            model_name='transaction',
            name='vendor',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='client_receipts', to='receipts.Vendor'),
        ),
        migrations.RunPython(
            _populate_description,
            _populate_description,
            elidable=True
        ),
    ]