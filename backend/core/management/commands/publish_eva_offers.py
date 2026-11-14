from django.core.management.base import BaseCommand, CommandError
from core.eva_delivery import EvaError
from core.offers import publish_offers


class Command(BaseCommand):
    help = "Publish approved offers and retire expired offers in the Eva instruction."

    def add_arguments(self, parser):
        parser.add_argument("--if-changed", action="store_true")
        parser.add_argument("--scheduled", action="store_true", help="Respect unpublished edits; update schedules only.")

    def handle(self, *args, **options):
        try:
            changed = publish_offers(only_changed=options["if_changed"], scheduled=options["scheduled"])
        except (EvaError, KeyError, TypeError) as exc:
            raise CommandError(getattr(exc, "code", "invalid_offer_response")) from None
        self.stdout.write("Offers verified in Eva" if changed else "No publication needed or edits await review")
