import random

import factory

from taxes.receipts import models, constants


class VendorFactory(factory.DjangoModelFactory):
    class Meta:
        model = models.Vendor

    id = None
    name = factory.Faker('company')
    type = factory.LazyFunction(lambda: random.choice(list(constants.VendorType)))
    fixed_amount = None


class PaymentMethodFactory(factory.DjangoModelFactory):
    class Meta:
        model = models.PaymentMethod

    name = factory.Faker('credit_card_provider')
    description = factory.Faker('text')
    type = constants.PaymentMethod.CREDIT_CARD
    safe_numeric_id = factory.LazyFunction(lambda: '{:04d}'.format(random.randint(1, 10000)))
    currency = factory.LazyFunction(lambda: random.choice(list(constants.Currency)))
