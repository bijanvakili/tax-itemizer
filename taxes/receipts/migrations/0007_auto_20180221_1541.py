# Generated by Django 2.0.1 on 2018-02-21 15:41

from django.db import migrations, models
import django.db.models.deletion
import enumfields.fields
import taxes.receipts.constants
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('receipts', '0006_auto_20180106_0612'),
    ]

    operations = [
        migrations.CreateModel(
            name='TaxAdjustment',
            fields=[
                ('id', models.UUIDField(blank=True, default=uuid.uuid4, editable=False, primary_key=True,
                                        serialize=False)),
                ('tax_type', enumfields.fields.EnumField(enum=taxes.receipts.constants.TaxType, max_length=3)),
                ('amount', models.IntegerField()),
                ('receipt', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                              related_name='tax_adjustments', to='receipts.Receipt')),
            ],
            options={
                'db_table': 'tax_adjustment',
                'ordering': ('receipt__purchased_at', 'receipt__vendor__name', 'tax_type'),
            },
        ),
        migrations.AddField(
            model_name='periodicpayment',
            name='tax_adjustment_type',
            field=enumfields.fields.EnumField(blank=True, enum=taxes.receipts.constants.TaxType, max_length=3,
                                              null=True),
        ),
        migrations.AlterField(
            model_name='periodicpayment',
            name='vendor',
            field=models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name='periodic_payment',
                                       to='receipts.Vendor'),
        ),
    ]