# SpaceWeb rollout — 14 November 2026

SpaceWeb serves release `8c133ec` from `/home/v/vlico39ru/.vlico-release-20261114-8c133ec`. The release was built from tracked application files and uses the previous Python 3.11 environment. Production content remains in the existing PostgreSQL and media directories.

The private backup at `/home/v/vlico39ru/.vlico-backup-20261114-8c133ec` includes the previous application, media, environment, adapters and a PostgreSQL 17 custom dump. Archive inventories and the database dump checksum were checked. The SSH tunnel used for the dump was closed. Migrations `0018` and `0019` applied successfully. Public static was copied without deleting old hashed files. The WSGI adapter was switched atomically.

- The candidate homepage and health endpoint returned 200 through CGI before the switch. On the public domain, health, homepage, calculator, catalogue, services, blog, partners, contacts, legal pages, robots, sitemap and cabinet login returned 200. Private environment and Git paths returned 404.
- All 207 Django tests passed on local PostgreSQL after collecting static files. Django reports no uncommitted model migrations. Server deployment checks reported the two existing HSTS warnings.
- On SpaceWeb, all five submission types created one lead and one Eva job when capture was enabled within the test process. Repeat submits returned the same reference. Notification queue entries existed. The enclosing transaction was rolled back and all test records were verified absent.
- On the deployed domain, Playwright verified the quick calculator on desktop and mobile, error handling, duplicate-submit protection, and forms without attachments. Browser submission responses were intercepted for successful sends. All seven videos played and served byte ranges.
- The real Eva widget script and deployed VLICO adapter loaded, opened and closed at 1440 and 390 px on the production origin with the script tags injected into the browser test response only. This verifies the UI on the production origin. Live chat and CRM write-through from production remain pending. An authenticated read from SpaceWeb to Eva succeeded and found the test calendar.

Public chat and live form capture/delivery are off. The current consent and privacy pages do not identify Eva as a processor. Before turning them on, obtain VLICO approval for the updated disclosure and run controlled live checks with synthetic records. The previous email and Telegram notification process was left in place. This deployment did not send real notification messages.

For code rollback, atomically restore the backed-up `wsgi.py` into `public_html/wsgi.py` and verify the homepage and `/health/`. Leave the new tables and current lead records in PostgreSQL.
