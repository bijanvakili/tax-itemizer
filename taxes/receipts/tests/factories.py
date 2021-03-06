import random

import factory

from taxes.receipts import models, types


class VendorFactory(factory.DjangoModelFactory):
    class Meta:
        model = models.Vendor

    id = None
    name = factory.Faker("company")
    default_expense_type = factory.LazyFunction(
        lambda: random.choice(list(types.TransactionType))
    )
    fixed_amount = None
    tax_adjustment_type = None


class PaymentMethodFactory(factory.DjangoModelFactory):
    class Meta:
        model = models.PaymentMethod

    name = factory.Faker("credit_card_provider")
    description = factory.Faker("text")
    method_type = types.PaymentMethod.CREDIT_CARD
    safe_numeric_id = factory.LazyFunction(
        lambda: "{:04d}".format(random.randint(1, 9999))
    )
    currency = factory.LazyFunction(lambda: random.choice(list(types.Currency)))
