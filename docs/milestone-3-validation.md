# Milestone 3 verification — 2026-11-04

## Delivered

Server forms for consultation, measurement, project upload, calculator and partnership; published-project/service context; first-touch attribution; private validated files; cabinet lead/status/retry screens; versioned editable calculator rates; PostgreSQL-backed Telegram delivery in a separate Compose service. Main-site forms persist real data; the isolated static preview remains a demonstration.

## Automated checks

- 68 Django tests pass, including PostgreSQL concurrency cases for identical submissions, conflicting payloads and competing delivery workers.
- Regression coverage includes consent/contact/token/CSRF/honeypot/rate limits, invalid and oversized files, private access, storage rollback, saved historical calculations, stale prices, rate permissions/units and non-JavaScript submission.
- Telegram transport tests cover success, temporary/permanent failures, 429, uncertain results, stale leases and resuming partial delivery without resending confirmed parts. Message splitting respects UTF-16 limits without dropping user text.
- Django checks, migration drift check, JavaScript syntax, Compose configuration and Git whitespace checks are required for delivery; no secret values are written into tracked artifacts.

## Browser checks

Playwright against the actual local Django/PostgreSQL app at 1440px and 390px, including a mobile context with touch:

- 20 m² PVC + 18 m ordinary perimeter = 16,240 ₽. Changing the PVC rate to 700 via the cabinet changes a new estimate to 17,240 ₽; the existing lead retains 16,240 ₽. Original provisional rates restored after QA.
- Unknown perimeter gives 13,000 ₽ for 20 m² PVC and a clear incomplete-estimate warning. Mobile order is parameters → result → contact.
- Published case CTA preserves project context. UTM persists across homepage, case and request page.
- Invalid contact and PDF show errors while retaining input. A deliberately aborted request keeps contact and submission key; retry saves successfully. A stale price returns an updated quote for review.
- Real PDF upload, success state, cabinet lead processing and responsive list/rate forms checked. No horizontal overflow on the reviewed mobile screens.
- Temporary QA leads, uploaded copies and temporary rate versions removed. One clearly marked acceptance-test lead is retained as evidence.

The design detector reports palette advisories from parsing standalone Django templates; no blocking finding. Screenshots and private test sessions stay in ignored `.playwright-cli/`. Browser emulation was used, not physical phone hardware.

## Actual Telegram acceptance

The configured bot token was valid. The initial attempt failed with `chat not found`; the test lead and PDF remained saved. After the recipient opened the bot and confirmed readiness, the same queued test was retried successfully: Telegram acknowledged one text message and one PDF. Confirmed progress and sent status were persisted. Credentials, recipient ID and message IDs are intentionally omitted here.

The background delivery switch is enabled in the local private environment. No customer data was used in the test. Public deployment, final legal operator details, analytics and client approval of provisional prices belong to the remaining milestones.

After recreating web and starting delivery from the built image, the saved lead, original rate version, calculation, PDF and sent progress remained intact. Requeuing the already-confirmed test progress exercised the background worker without sending another message or file. PostgreSQL, web and delivery healthchecks pass; Django check and migration drift checks pass. The final built image passes all 68 tests.
