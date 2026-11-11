# SpaceWeb deployment, 12 November 2026

## Delivered

Live site: https://vlico39.ru/. Application code revision: `892438f`, in `/home/v/vlico39ru/.vlico-release-20261112-892438f`.

- Seven client videos, real posters, horizontal rail, native dialog playback, seeking and fullscreen. No MP4 is requested before activation; closing synchronously pauses playback and releases its source.
- Six equal homepage cards with full portrait-photo framing. D. Donskogo, 15 and Krasnokamennaya, 3 occupy the last two positions; Klubnaya and Leonova remain published in the catalogue.
- Four new projects and twelve photos were transferred from the local cabinet, preserving exact public derivatives, private editing sources, metadata and original-ratio/fit settings. Production IDs were allocated independently; local primary keys were not restored over production records.
- Header logo sizing is shared across public pages. Hero composition and other established blocks are preserved.

## Data preservation and backups

Before deployment production contained 29 projects, 93 project photos, 10 articles, 21 leads and 2 users. After import it contains 33 projects (29 published), 105 photos, the same 10 articles, 21 leads and 2 users. Existing project fields and photo records were compared against the backup; only the two agreed homepage ordering fields changed. Production-only projects and editor changes were preserved.

Fresh backups are in `/home/v/vlico39ru/.vlico-backup-20261112-054b3ab`: full PostgreSQL dump, original application, both media directories, environment, WSGI/CGI adapters, root htaccess and cron adapter. The database dump was made with PostgreSQL 17 through an SSH tunnel because the host's pg_dump is older; pg_restore inventory and transferred SHA-256 were verified. The tunnel is closed. A local copy is in ignored `backups/spaceweb-20261112-054b3ab/`.

`baseline.json` records pre-import metadata; `import-result.json` records inserted IDs and ordering changes. New records: Krasnokamennaya 49, Karabelnaya 50, Koloskova 51, Donskogo 52. Original photos and the portable import bundle remain outside the public web root.

Code was prepared and CGI-tested in a separate release directory, then WSGI/CGI files were switched with atomic file replacement. No migrations were pending. Dependencies are unchanged; the final release reuses the Python 3.11 environment in `.vlico-release-20261111-02c8280/.venv`. The existing notification cron and its configuration were preserved. Keep that older directory: both the virtual environment and cron still use it.

For code rollback restore the backed-up WSGI/CGI adapters. Do not restore the old database automatically: this would remove new projects and any later leads. Previously hashed public static files remain available to cached pages.

## Hosting corrections verified during rollout

Initial public checks exposed CGI saturation while hidden carousel photos were fetched in parallel. CSS, JavaScript, fonts, posters and MP4 now come directly from `public_html/static/`, containing only collected public assets. Existing hashed assets are retained; `scripts/spaceweb-static.htaccess` gives hashed files immutable caching. Video byte-range responses were verified as 206 with the correct content type and byte count.

Enhanced project carousels now assign image sources only to the active image and adjacent images on interaction, avoiding the initial hidden-slide request burst. Noscript images remain available. A queued dialog close event also caused a brief playback delay under hosting load; playback now stops during the close/cancel action itself, with protection against an older close event affecting a newly opened player.

## Checks performed

- All 189 Django tests passed locally after the hosting corrections; Node syntax and Git whitespace checks passed.
- Server `check` passed; `check --deploy` retains only the existing HSTS subdomain/preload warnings. Those settings were not expanded.
- Candidate CGI homepage, health and video range checks passed before switching; public `/health/` returns 200 and `status: ok`.
- Live `test-project-videos`: all seven played and sought; zero MP4 requests before activation; all range checks, Chromium fullscreen, close/source cleanup, focus restoration and controlled error/retry passed.
- Live `test-home-project-grid`: 320–1920px, two equal desktop rows, full portrait frames, aligned text without categories, arrows/keyboard/drag, catalogue and original detail-image viewing passed. Final scenario reported no media errors or application JavaScript errors.
- Four new case pages were checked as anonymous visitors at 1440, 390 and 320px: correct 4/4/2/2 photo grouping, gallery navigation, full-image framing and no leaked editorial placeholders. All 29 published projects remain in the catalogue.
- Existing hero checks passed at 13 viewport sizes, including enlarged text, touch, keyboard, Escape and native disclosure fallback. Navigation checks passed for nine directions, touch, keyboard, reduced motion and no-JavaScript navigation.
- Header and typography checks passed on seven public entry points at 1440, 390 and 320px. No document overflow; logo dimensions match the homepage at each width.
- Form loading/success/duplicate protection passed on desktop and mobile with browser-intercepted responses. One incomplete real API request was rejected with 400; no new lead or outbound notification was created. Existing email delivery was not retested by sending mail.
- Health, catalogue, all four new cases, services, blog, partnership, contacts, robots and sitemap returned 200; sitemap includes the new cases. `/.env` and `/.git/config` returned 404.

Final desktop card and mobile video screenshots were visually inspected and are in ignored `.playwright-cli/`. Real iPhone hardware was not available; mobile browser emulation does not constitute a physical Safari check.

## Existing external limitation

HTTPS access from SpaceWeb to `api.telegram.org:443` still times out, including a request with redirects disabled and no bot token. Telegram notifications therefore remain an existing infrastructure limitation. Credentials were not changed, uncertain deliveries were not retried, and no test messages were sent. This is separate from the delivered project/video changes.
