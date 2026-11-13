# Eva outbox operation

The existing submission transaction saves Lead and existing notification deliveries. With EVA_CAPTURE_ENABLED=true, it also saves one EvaSyncJob. EVA_SYNC_ENABLED is independent and false by default. Disabling Eva does not disable local forms or email. No old leads are automatically exported.

Configure incoming and partner funnel/status/executor UUIDs separately. Store EVA_API_KEY only in private server environment. The adapter uses a fixed HTTPS host and rejects redirects to prevent key leakage. Raw remote errors are not logged.

Run `python backend/manage.py deliver_eva` in the configured application environment. One invocation claims at most one job. On SpaceWeb schedule the separate scripts/deliver-eva-once.sh adapter against the verified release/virtualenv; do not blindly replace the existing notification cron. Existing release layouts must be checked before installing this script.

Eva allocates new UUIDs on POST even when a UUID is supplied as the data key. The adapter saves returned contact/lead IDs and reads them back. Retries of reads use saved IDs. Before each create, a durable write intent is recorded. A lost POST response or a crash between POST and ID checkpoint enters write_uncertain review and cannot be replayed from the cabinet. Contact externalId must match the local reference; conflicting remote identity enters review rather than being overwritten. Unexpected process failure is recovered after a 180-second lease. Five exhausted attempts require operator review. Retries are 30/120/600/1800/3600 seconds; no promise of external exactly-once semantics before live contract verification.

The protected lead detail page shows state and safe error code. Users with change_lead can requeue blocked/review/retry jobs. Requeue preserves returned UUIDs and always rechecks Eva. write_uncertain cannot be requeued; an operator must identify both existing records and run `python backend/manage.py reconcile_eva JOB --contact-id UUID --lead-id UUID`. This command checks ownership without creating records. If only a contact exists, resolve the missing CRM card manually before using this command. Sent jobs cannot be requeued through this action. Verify root cause before retrying; requeue does not delete or edit remote records.

Rollback: disable EVA_SYNC_ENABLED and EVA_CAPTURE_ENABLED, return previous code/adapters if necessary. Retain the additive queue table and all current leads. Do not restore an old database or replay historical Telegram delivery_uncertain records.


Live contract evidence: POST returns top-level items in the inspected account, while GET returns data. skipNotifications belongs to the envelope, not the record. Both shapes supported where documented. Model-attribute names are canonicalized by Eva (underscores removed); the adapter maps UTM names to the canonical names without fabricating missing values. See api-contract-evidence.json.

The embed uses the official containerId mode, verified in Eva Embed on site. It is loaded only on explicit chat opening. Native dialog supports Escape and focus return. The launcher moves above an open cookie panel. No REST key is sent to the browser. Local 390px emulation is not a physical-device or production check. The vendor initial contact form remained English during inspection despite language=ru; localization is a known issue to resolve before acceptance.
