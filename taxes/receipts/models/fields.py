import uuid

from django.db import models
from enumfields.fields import EnumField, import_string


__all__ = [
    'uuid_primary_key_field',
    'enum_field'
]


class TaxesEnumField(EnumField):
    @staticmethod
    def _fully_qualified_class_name(enum_class):
        return f'{enum_class.__module__}.{enum_class.__name__}'

    def __init__(self, enum, **options):
        kwargs = options.copy()
        if isinstance(enum, str):
            enum_class = import_string(enum)
        else:
            enum_class = enum
        kwargs['max_length'] = max(len(e.value) for e in enum_class)
        super().__init__(enum_class, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs.pop('max_length', None)
        # this ensure the class is always serialized to a string to avoid
        kwargs['enum'] = self._fully_qualified_class_name(self.enum)
        return name, path, args, kwargs


def uuid_primary_key_field(**kwargs):
    kwargs = kwargs.copy()
    kwargs['primary_key'] = True
    kwargs['editable'] = False
    kwargs['blank'] = True
    kwargs['serialize'] = False
    kwargs['default'] = uuid.uuid4
    return models.UUIDField(**kwargs)


def enum_field(enum_class, **kwargs):
    return TaxesEnumField(enum_class, **kwargs)
