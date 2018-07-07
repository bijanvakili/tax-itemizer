import typing

import yaml


try:
    DefaultLoader = yaml.CSafeLoader
except AttributeError:
    DefaultLoader = yaml.SafeLoader


def load(stream: typing.IO) -> dict:
    return yaml.load(stream, Loader=DefaultLoader)
