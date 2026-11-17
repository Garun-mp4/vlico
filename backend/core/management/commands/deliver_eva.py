from pathlib import Path
import time

from django.core.management.base import BaseCommand
from django.db import close_old_connections

from core.eva_delivery import deliver_eva_one
from core.eva_outreach_monitor import ALERT_CHANNEL, monitor_one
from core.email_delivery import deliver_email_one


def process_once():
    crm = deliver_eva_one()
    monitor = monitor_one()
    alert = deliver_email_one(ALERT_CHANNEL)
    return crm or monitor or alert


class Command(BaseCommand):
    help = "Process one Eva outbox job or watch the queue continuously."

    def add_arguments(self, parser):
        parser.add_argument("--watch", action="store_true")

    def handle(self, *args, **options):
        if not options["watch"]:
            self.stdout.write("Processed Eva job." if process_once() else "No Eva job processed.")
            return

        heartbeat = Path("/tmp/vlico-eva-heartbeat")
        while True:
            heartbeat.touch()
            close_old_connections()
            if not process_once():
                time.sleep(2)
