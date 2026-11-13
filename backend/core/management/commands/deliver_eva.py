from pathlib import Path
import time

from django.core.management.base import BaseCommand
from django.db import close_old_connections

from core.eva_delivery import deliver_eva_one


class Command(BaseCommand):
    help = "Process one Eva outbox job or watch the queue continuously."

    def add_arguments(self, parser):
        parser.add_argument("--watch", action="store_true")

    def handle(self, *args, **options):
        if not options["watch"]:
            self.stdout.write("Processed Eva job." if deliver_eva_one() else "No Eva job processed.")
            return

        heartbeat = Path("/tmp/vlico-eva-heartbeat")
        while True:
            heartbeat.touch()
            close_old_connections()
            if not deliver_eva_one():
                time.sleep(2)
