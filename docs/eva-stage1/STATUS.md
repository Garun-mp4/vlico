# VLICO × Eva — execution journal

## 2026-11-13

Approved scope: stage 1, M0–M7. Work directly on main under the user's explicit Git policy. Preserve existing untracked docs/implementation. No production deployment, trial changes, payment, external test messages or live channel switch authorized.

M0: inspected forms, save_submission, attribution, delivery, deployment reports and authenticated Eva API docs. Docker started once using host procedure; daemon 29.8.2 verified. Current production state is derived from November 12 report, not a fresh SSH inspection.

Initial audit ingested the package and original PDFs. See implementation checkpoint below for the resulting knowledge and dialogue work.

M2: implemented separate transactional EvaSyncJob, server adapter, bounded retries and ID reconciliation, independent command and authenticated diagnostic/requeue action. Capture and sync default OFF. No historical backfill. Live API contract tests and widget are pending.

Initial Eva inventory found two agents and duplicate sales funnels. The owner notification channel was missing.

## Verified API facts

Source: authenticated https://eva.bz/support/api, inspected November 13.

- Base: https://eva.bz/api/dashboard. Token header carries API key. Do not combine Token with Authorization.
- HTTP 200 is not sufficient: inspect JSON code, including 402 quota, 422 validation.
- POST contacts/leads uses data keyed by UUID. GET resource/:id supports reconciliation.
- Contacts support externalId, props, phone, email; leads require contactId and support funnelId/statusId/userId/description/props.
- skipNotifications suppresses assignment notifications; this does NOT establish suppression of every automation. Live testing requires a safe isolated funnel with no outgoing tasks.
- Tasks can be disabled, channel selection must be explicit. Avoid all-channel automatic expansion.
- Outgoing webhook signing was not documented in the inspected section. No inbound webhook endpoint is implemented.

## Next actions

1. Finish and record local tests; verify API envelope and idempotency using approved synthetic records.
2. Obtain API key through private local environment, never chat or Git; no request sent without it.
3. Complete agent knowledge and local audio transcription, then configure Eva UI.
4. User authorizes own Telegram/WhatsApp/Google accounts and explicitly identifies test destinations before any live message.
5. Production and working channel changes require separate permission after backup/rollback review.

No milestone is declared complete merely because code or a configuration exists. Acceptance TC-01–34 remains pending real evidence.


## Implementation checkpoint

- 205 Django tests passed on isolated PostgreSQL, including 16 new Eva tests; migrations dry run: no changes detected. JavaScript syntax and Git whitespace checks passed.
- Additive 0018 migration applied to LOCAL development database only. Production untouched.
- Live API tested with synthetic contacts lacking phone/email/channel accounts. Returned IDs saved; second ensure issued GET only. No external messaging destinations in contract checks.
- API differences discovered: UUID data keys are temporary, create returns top-level items, skipNotifications is envelope-level, update fields differ from create, attribute names lose underscores. Adapter adjusted and regression tests added. Two empty partner scaffolds were created during initial ID assumption; one retained as primary, one explicitly renamed reserve; none deleted.
- M1: four recordings transcribed locally; anonymous style guide prepared. Both agent prompts and complete knowledge documents now saved in Eva. Offer wording still draft before campaign approval.
- M3 partial: main incoming funnel and partner funnel/stages/14 contact attributes exist; safe dialogue rules configured; automatic booking rule redirected to handoff. Four new touch tasks plus two old tasks OFF. No real partner base imported.
- M4 partial: real widget code integrated behind OFF flag, desktop and 390px layout/overflow/close/focus inspected locally; production still pending. Vendor initial form labels remain English. Widget channel disabled.
- Telegram test bot connected by the user. The test sender is the account explicitly approved by the user. Native Telegram Bot whitelist is restricted to VLICO_TEST funnel, containing the approved user's contact only. This whitelist applies to all channels of that type; review at production cutover. Test channel enabled; all other external channels receive-only/unauthed. No messages to Vladlen or other third parties authorized.
- Telegram observations: MSD 25m² -> 22500 plus exclusions; regional measurement 1500 with distance caveat; no final booking without Vladlen. Track answer initially invented that rate was installation-only; both prompts tightened; retest pending.
- Original configuration backup and raw transcripts live in Downloads package/_execution and 06_ORIGINAL_SOURCES/TEXT_EXTRACTS, outside Git/public assets. API key created with explicit action-time approval; stored only in ignored .env. Never reproduce its value in reports.

Pending: complete dialogue tests, opt-out/handoff/partner automation validation, Google/WhatsApp user authorization, source/KPI filtering demonstration, isolated live form-to-CRM checks, production read-only inspection, consent proposal approval, deploy/working-channel approval, partner Excel, handover and acceptance. No complete milestone or final acceptance is claimed while these checks remain.

- Site implementation committed and pushed as 61b7eda. Pending Telegram retest could not be read after browser access became unavailable and the Eva API timed out during TLS handshake. Retest result unverified.
