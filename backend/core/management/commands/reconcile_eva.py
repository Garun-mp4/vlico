import uuid
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from core.eva_delivery import api, EvaError
from core.models import EvaSyncJob


class Command(BaseCommand):
    help = "Resolve an uncertain write using verified existing Eva contact AND lead ids; never creates remote records."

    def add_arguments(self, parser):
        parser.add_argument("job", type=int)
        parser.add_argument("--contact-id", required=True, type=uuid.UUID)
        parser.add_argument("--lead-id", required=True, type=uuid.UUID)

    def handle(self, *args, **options):
        try:
            job = EvaSyncJob.objects.get(pk=options["job"])
            contact = api("GET", "contacts/" + str(options["contact_id"]))["data"]
            lead = api("GET", "leads/" + str(options["lead_id"]))["data"]
            if (contact.get("id") != str(options["contact_id"]) or
                    lead.get("contactId") != str(options["contact_id"]) or
                    (lead.get("props") or {}).get("localleaduuid") != str(job.lead_id)):
                raise CommandError("Remote ownership does not match. Nothing changed.")
            with transaction.atomic():
                locked = EvaSyncJob.objects.select_for_update().get(pk=job.pk)
                if locked.status not in {"review", "blocked"}:
                    raise CommandError("Job must be in review or blocked state.")
                locked.contact_id, locked.remote_lead_id = options["contact_id"], options["lead_id"]
                locked.status, locked.attempts, locked.error_code = "pending", 0, ""
                locked.next_attempt_at = None
                locked.save()
        except EvaError as exc:
            raise CommandError("Eva verification failed: " + exc.code) from None
        except (EvaSyncJob.DoesNotExist, KeyError, TypeError):
            raise CommandError("Job or API result unavailable. Nothing changed.") from None
        self.stdout.write("Verified remote identities saved. Next delivery will reconcile without creating duplicates.")
