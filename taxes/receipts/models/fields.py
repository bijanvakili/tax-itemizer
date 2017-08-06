import uuid

from django.db import models
from enumfields.fields import EnumField


__all__ = [
    'uuid_primary_key_field',
    'enum_field'
]


def uuid_primary_key_field(**kwargs):
    kwargs = kwargs.copy()
    kwargs['primary_key'] = True
    kwargs['editable'] = False
    kwargs['blank'] = True
    kwargs['serialize'] = False
    kwargs['default'] = uuid.uuid4
    return models.UUIDField(**kwargs)


def enum_field(enum_class, **kwargs):
    kwargs = kwargs.copy()
    kwargs['max_length'] = max(len(e.value) for e in enum_class)
    return EnumField(enum_class, **kwargs)
