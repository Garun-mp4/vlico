# Cookie notice and chat launcher correction

Delivered to https://vlico39.ru/ on 14 November 2026. Code commit: `38695eb`.

The launcher obstruction calculation previously considered only an obstruction's vertical position. A cookie notice at the left therefore raised a launcher on the right despite the lack of intersection. Positioning now checks both axes from the launcher's normal anchor. On screens up to 760px the cookie notice leaves 84px plus the bottom safe area for the launcher; its maximum height preserves access on short screens. The existing mobile action already reserves horizontal space for the launcher.

Two additional defects were reproduced and corrected: the desktop popup's fixed 600px height placed its close button above a short landscape viewport, and Eva retained an empty full-screen mobile host after closing, intercepting clicks on the page. The popup now fits the viewport, and only the actual mobile chat window accepts pointer events.

## Verification

- The regression failed before the fix: at 1440px dismissing cookies moved the launcher from y=649.65625 to y=820.
- Candidate and published-site regression: 14 passing scenarios across the homepage and contacts, at 1440x900, 1024x768, 761x600, 760x600, 390x844, 320x568 and 844x390. Checks cover unchanged launcher position, no overlap, usable cookie bounds, chat open/close, editable input, fitting popup, reopening cookies with the keyboard, pointer clicks after mobile close, acceptance storage and document overflow. No application JavaScript exceptions.
- All ten desktop/mobile invitation presentation scenarios passed against the candidate assets with synthetic vendor configuration. This includes touch, keyboard, focus handling and reduced motion; no chat messages were sent.
- The existing navigation test passed on the published site: nine directions and nine widths, keyboard, touch navigation, reduced motion and navigation without JavaScript.
- Public smoke checks passed for eight entry points at 1440, 390 and 320px: 24 successful page loads, no document overflow, no already-loaded broken images and no application JavaScript exceptions.
- Mobile touch opening/closing was also exercised against the real vendor UI. Desktop, mobile and landscape screenshots were visually inspected. Physical iPhone/Safari hardware was not available.
- Node syntax checks, Git whitespace checks, production Django `check`, published health endpoint and public asset checks passed.

## Deployment and rollback

The prior active release was checked against the repository for both changed source assets. A separate copy was created at `/home/v/vlico39ru/.vlico-release-20261114-cookie-widget`, preserving its environment and existing virtual-environment link. Collected public assets were verified by SHA-256 and published before atomically switching `public_html/wsgi.py`.

The new public assets are `eva-widget.f8d720c01f47.js` and `site.1d1bb6ca5597.css`. Old hashed assets remain available to cached pages. The preceding WSGI adapter is backed up at `/home/v/vlico39ru/.vlico-backup-20261114-cookie-widget/wsgi.py`; restoring that adapter reselects the previous release. No migrations, database changes, media changes or notification configuration changes were made.

## Existing console diagnostics

The CGI relay supports Socket.IO polling and rejects WebSocket upgrades with 404. The vendor attempts an upgrade and reports that rejection in the console. This existed before this correction; real message delivery was not retested. Some Yandex iframe diagnostics originate from this computer's Kaspersky script injection and the iframe's CSP. Neither was classified as an application JavaScript exception or hidden by the correction.
