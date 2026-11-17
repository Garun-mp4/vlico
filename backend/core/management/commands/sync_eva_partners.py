from django.core.management.base import BaseCommand, CommandError

from core.eva_delivery import EvaError
from core.eva_partner_campaign import sync


class Command(BaseCommand):
    help = "Reconcile Victoria's selected campaign contacts with their Eva CRM cards."

    def handle(self, *args, **options):
        try:
            count = sync()
        except EvaError as exc:
            raise CommandError(exc.code) from None
        self.stdout.write(f"Eva partner campaign contacts checked: {count}")
