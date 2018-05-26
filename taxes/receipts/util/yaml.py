import yaml
import typing

try:
    DefaultLoader = yaml.CSafeLoader
except AttributeError:
    DefaultLoader = yaml.SafeLoader


def load(stream: typing.IO) -> dict:
    return yaml.load(stream, Loader=DefaultLoader)
