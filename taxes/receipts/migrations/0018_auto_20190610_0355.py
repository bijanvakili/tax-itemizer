# Generated by Django 2.2.2 on 2019-06-10 03:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('receipts', '0017_extend_transaction_20190609_0322'),
    ]

    operations = [
        migrations.AlterField(
            model_name='paymentmethod',
            name='safe_numeric_id',
            field=models.CharField(blank=True, db_index=True, max_length=4, null=True),
        ),
    ]
