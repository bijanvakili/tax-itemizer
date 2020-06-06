import uuid

from django.db import models


__all__ = ["uuid_primary_key_field", "text_choice_field"]


def uuid_primary_key_field(**kwargs):
    kwargs = kwargs.copy()
    kwargs["primary_key"] = True
    kwargs["editable"] = False
    kwargs["blank"] = True
    kwargs["serialize"] = False
    kwargs["default"] = uuid.uuid4
    return models.UUIDField(**kwargs)


def text_choice_field(choice_class: models.TextChoices, **kwargs):
    """
    Convenience method for creating a CharField restricted to
    the TextChoice enum-like class.

    Default behavior is to automatically determine the max_length
    based off the largest key name.
    """
    kwargs = kwargs.copy()
    kwargs.setdefault("max_length", max(len(e.name) for e in choice_class))
    return models.CharField(choices=choice_class.choices, **kwargs)
