# Eva CRM rollout and controlled checks

## 13 November 2026

- Incoming CRM explicitly routes the website widget and the connected WhatsApp channel to «Новая заявка». The old sales funnel was detached from all channels and moved after the main funnel. The reserve has no channel assignments. The Telegram test funnel remains in use for the allowlist.
- In isolated PostgreSQL, five synthetic submissions passed Django endpoint → Eva worker → REST read-back. Repeat POST returned the same local reference. Verified source, UTM, test marker, next action, responsible and initial stage. The quick calculator preserved its snapshot. Four client submissions went to Artem; partnership went to Viktoria.
- With the same phone, Eva reused the contact and rejected an additional deal for the same executor with `userId: Parameters are not unique`. The site keeps every submission; the queue flags this case for manual review. Existing deals are preserved.
- The approved test WhatsApp sender received an Artem estimate and a reply that the requested measurement slot awaits Vladlen. The contact was linked to an incoming lead and marked as a test. The configured dialogue rule delays were 60 or 1440 minutes. All 23 dialogue rules now read back as 1 minute; zero fell back to 1440 in Eva. A fresh widget test after the delay change produced the expected estimate and measurement reply, but the deal still stayed at «Новая заявка». Automatic progression is unverified. No rule targets «Замер назначен».
- All 207 Django tests passed on isolated PostgreSQL and migration consistency passed. Docker Compose rebuilt the local web and Eva worker containers; both became healthy.

## 14 November 2026

- On later readback, the test WhatsApp and widget leads both reached «Ожидает согласования замера» through dialogue. The observed delays were roughly 11 minutes and 10½ minutes respectively. Neither reached «Замер назначен». The rule's one-minute delay does not establish a one-minute end-to-end transition.
- Eva sees the isolated `VLICO — тест` Google calendar and returns its controlled busy interval and empty adjacent intervals. See [the execution journal](STATUS.md#m4--google-calendar-readback-2026-11-14) for the test. Live agent lookup and the full manager approval flow remain unverified.

## SpaceWeb form delivery and campaign check

- On release `e7e0962`, exercised all five Django form submissions and the real Eva adapter on SpaceWeb. The synthetic batch `b4eda955` read back from Eva with the expected funnel, initial stage, executor, UTM, comment and calculator snapshot. Repeat submissions reused the same lead. The local test transaction was rolled back before the existing notification worker could see it. The five CRM records were marked as test records.
- Configured the API key and both routes in the private hosting environment. A separate SpaceWeb Crontab task invokes the active release through its WSGI adapter each minute. Capture and delivery remain disabled while VLICO reviews the form disclosure.
- Eva reported both knowledge sets indexed. The test Telegram bot and connected WhatsApp were online. The agreed production channel switch is still pending.
- Production touch tasks are disabled and have no assigned channels or contacts. The partner delays are set to 4320 and 11520 minutes from entry to the proposal stage. The client delay is 1440 minutes from entry to the quote stage. Eva documents removal from the queue when a lead leaves the stage or ceases to match filters. Actual cancellation remains unverified.
- The isolated touch task contained only the previously approved Telegram test contact and test bot, with automatic contact sync off. Eva moved the queue item to `error` without returning a reason. No matching message appeared in the test conversation. The task was disabled. A separate direct message request timed out and readback did not find the diagnostic text. Delivery is unconfirmed.

## Measurement approval

1. Artem records the location or district, preferred time and reply channel. CRM should move to «Ожидает согласования замера».
2. Vladlen opens the lead and reads the linked conversation, checks calendar availability, then creates or confirms the event and moves the lead to «Замер назначен». Only then does he confirm to the customer.
3. Configure Vladlen's verified Telegram notification channel before launch. A notification should identify the lead, source channel, request, preferred slot and link to the CRM. Verify what the native message contains and that it arrives. Where native fields are limited, the linked CRM card is the source of detail. Confirm receipt with a controlled recipient before routing notifications to Vladlen.

## Channel limits

- Eva's documented message creation takes an existing conversation ID; its Conversations API does not document creating a conversation. The Telegram bot requires the customer to start a chat. For a new WhatsApp recipient, a number alone does not authorize outreach. A customer-initiated conversation can be tested without automatic outreach to submitted numbers. Workflows should use the selected channel and require a verified conversation or approved platform workflow before sending.
- Partner campaign and client follow-up tasks are off. Agent-side calendar lookup, live manager notifications, campaign timing and opt-out tests, four KPIs, document deduplication and the production switch still require verification.
