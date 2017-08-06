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
