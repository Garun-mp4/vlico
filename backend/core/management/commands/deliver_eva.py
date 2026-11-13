from django.core.management.base import BaseCommand
from core.eva_delivery import deliver_eva_one


class Command(BaseCommand):
    help = "Process one Eva outbox job; never prints contacts or credentials."

    def handle(self, *args, **options):
        self.stdout.write("Processed Eva job." if deliver_eva_one() else "No Eva job processed.")
