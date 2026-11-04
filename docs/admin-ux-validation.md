# Cabinet UX/UI verification — 2026-11-04

Scope: Django cabinet templates, dedicated CSS, client workflow and the minimal JSON save/reorder contracts. Public site templates, stored projects, media, statuses and URLs are preserved. No dependencies or migrations added. Current categories and the existing crop/rotation editor are integrated; the obsolete featured checkbox is not restored.

## Automated checks

- `python manage.py test core --noinput`: 44 tests pass (37 existing and 7 new cabinet workflow tests).
- `python manage.py check`: no issues.
- `python manage.py makemigrations --check --dry-run`: no changes.
- `node --check` on both cabinet scripts and `git diff --check` pass.
- New regression tests cover composed search/category/status, accurate counts, sorting/empty results, JSON save with stale revision, unique generated Cyrillic slugs, atomic full reorder with invalid/foreign/duplicate IDs, authorization, POST and CSRF.

## Browser checks

Playwright CLI against the actual local Django/PostgreSQL application:

- New project from title alone; explicit save, reloaded persisted text, and inline validation preserving invalid input.
- Dirty indicator, blocked publication/preview, leave confirmation.
- Two-file sequential upload with rotation and persisted captions; photo drawer discard/cancel keeps edits.
- Drag reorder survives reload; native up/down remains available.
- Publish with confirmation, then unpublish.
- Location search, no matches, status filter, aborted network request retaining prior list, then successful retry.
- Desktop 1440×1000 and mobile 390×844: list, editor and photo drawer; no horizontal overflow. Mobile save stays visible.
- Visual review: neutral hierarchy, uniform thumbnail crops, separated public/private fields, readable focus and error feedback. Runtime console has only deliberately induced HTTP/network errors during negative tests.

Local screenshots are in ignored `.playwright-cli/admin-*-final.png`; they are review artifacts, not production assets. Temporary QA projects and their media are removed after verification. Real phone hardware and a production deployment are outside this local browser check.

## Design review

Manual Impeccable quality pass: task hierarchy, keyboard controls, native dialog focus, discarded-edit protection, mobile layout and gallery discoverability checked. Mechanical detector produced palette advisories and cannot resolve Django `{% static %}` links; its default-black template observations are parser limitations. Cabinet semantic colors and surface additions are documented in DESIGN.md and checked in rendered pages.


## Photo workspace refinement

The gallery now precedes basic information, including on the new-project screen. One bordered card contains upload controls, compact image thumbnails, explicit cover selection, overlay action menus, an add-photo tile and an ordering footer. A new project still needs a named draft before media can be uploaded; the initial card explains this and links to the name field.

Verified at 1440px and 390px with Playwright: two uploaded files persist, the add tile opens the native file chooser, drag reorder persists after reload and excludes the add tile from the request, aborted reorder restores the visible order with the add tile last, photo drawer opens, cover changes persist, and mobile menus remain within the viewport. Temporary test project 18 and its uploaded files were removed. All 44 server tests and Django checks pass. The design detector has palette advisories only; no blocking findings.

## Homepage photo navigation

Homepage project cards now show all saved photos, starting with the chosen cover. Catalog cards remain cover-only. Two additional server regressions check cover/order, draft-photo exclusion and the single-photo fallback; all 46 tests pass.

Playwright checks at 1440px and 390px cover previous/next buttons, disabled ends, keyboard Home/End and arrows, actual mouse drag without accidental navigation, independent cards, native touch swipe, rapid smooth-arrow clicks, resize preserving the current photo, normal photo links and the JavaScript-disabled fallback. A mobile browser context with touch enabled confirms vertical page scrolling over the photo; no horizontal page overflow. Reduced motion uses immediate navigation. Screenshots are ignored local artifacts in `.playwright-cli/card-gallery-*.png`. Mobile checks use browser emulation, not physical hardware.
