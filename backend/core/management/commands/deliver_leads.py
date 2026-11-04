from pathlib import Path
import time
from django.core.management.base import BaseCommand
from django.db import close_old_connections
from core.telegram_delivery import deliver_one


class Command(BaseCommand):
    help = "Deliver queued lead notifications without printing contacts or credentials."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true")

    def handle(self, *args, **options):
        heartbeat = Path("/tmp/vlico-delivery-heartbeat")
        while True:
            heartbeat.touch()
            close_old_connections()
            processed = deliver_one()
            if options["once"]:
                self.stdout.write("Processed one queued delivery." if processed else "No delivery processed.")
                return
            if not processed:
                time.sleep(2)
