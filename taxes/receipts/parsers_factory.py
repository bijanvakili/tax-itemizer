import importlib
import inspect
import os

from dataclasses import dataclass
from taxes.receipts.models import PaymentMethod
from taxes.receipts.parsers import BaseTransactionParser


class ParserFactoryException(Exception):
    pass


@dataclass
class ParserManifestEntry:
    file_prefix: str
    parser_class: BaseTransactionParser
    payment_method: PaymentMethod


class ParserFactory:
    def __init__(self):
        self.parser_module = importlib.import_module("taxes.receipts.parsers")
        configured_parsers = PaymentMethod.objects.exclude(
            file_prefix__isnull=True, parser_class__isnull=True,
        ).order_by("file_prefix")
        self.parser_manifest = [
            ParserManifestEntry(
                pm.file_prefix, self._get_parser_class(pm.parser_class), pm
            )
            for pm in configured_parsers
        ]

    def get_parser(self, pathname: str) -> BaseTransactionParser:
        """
        Returns an appropriate parser based on the filename
        """
        filename = os.path.basename(pathname)

        # perform a linear search for a matching parser
        manifest_entry = next(
            (p for p in self.parser_manifest if filename.startswith(p.file_prefix)),
            None,
        )
        if not manifest_entry:
            raise ParserFactoryException(f"No class found for file: {filename}")

        # construct the class
        return manifest_entry.parser_class(manifest_entry.payment_method)

    def _get_parser_class(self, class_name: str):
        clz = getattr(self.parser_module, class_name, None)
        if not clz:
            raise ParserFactoryException(f"Parser class not found: {class_name}")

        if (
            inspect.isclass(clz)
            and not inspect.isabstract(clz)
            and issubclass(clz, BaseTransactionParser)
        ):
            return clz

        raise ParserFactoryException(f"Invalid parser class name: {class_name}")
