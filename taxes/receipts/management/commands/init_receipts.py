import logging

from django.core.management import call_command
from django.core.management.base import BaseCommand


LOGGER = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Initializes the receipts application"

    def handle(self, *args, **kwargs):
        LOGGER.info("Setting up database...")
        call_command("migrate", *args, **kwargs)

        LOGGER.info("Setting up admin accounts...")
        call_command("createsuperuser", *args, **kwargs)
