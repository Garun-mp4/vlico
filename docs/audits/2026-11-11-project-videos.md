# Local project grid and video delivery

## Changes

- Homepage: six existing published projects in equal 3/2/1 columns (1100px / 801px breakpoints), equal 3:2 image frames, aligned text and actions. No database records were added or reordered.
- Portrait project images remain fully visible in their original proportions within those frames, with sand-colored side space. The shared image template applies this to all projects and carousel slides. Editor-selected compositions and original media remain intact.
- Seven client videos follow the solutions list, before the calculator. Four/two/one portrait previews, native horizontal scrolling, arrows, count and contact CTA use the existing visual system.
- One native dialog player supports play, sound, seeking, fullscreen, close/focus restoration and error/retry. MP4 sources are assigned only after activation and released on close. Direct MP4 links provide the no-JavaScript fallback.
- Original H.264/AAC streams were remuxed with faststart without recompression. Real WebP frames provide previews. No new player dependency, API or migration.
- Hero composition and other established blocks were preserved. The sticky CTA now yields to video controls as it already does to project controls.

## Verification performed

- Docker Compose rebuilt; db, web and delivery healthy; `/health/` returned `{"status":"ok"}`.
- `manage.py check`: passed.
- Django: `core.test_home_preview`, `core.test_public_site`, `core.test_navigation` (27 tests), plus `core.test_project_videos` (4 tests), passed. After the portrait adjustment, the 10 homepage/video tests passed again.
- `scripts/test-home-project-grid.js`: passed at 320–1920px, including equal card heights, two desktop rows, full portrait previews, catalogue, carousel arrows/keyboard/drag, original detail-image viewing and delayed-image layout stability.
- `scripts/test-project-videos.js`: all seven videos played and sought; zero MP4 requests before activation; every file returned 206 with exactly 1024 bytes for a range request; Chromium fullscreen, close/source cleanup, focus restoration and recovery from an intentionally failed request passed.
- Additional touch emulation: native swipe, tap to play and tap to close passed. With JavaScript disabled, the direct video link returned 206.
- Public-page audit: 48 routes at 1440, 390 and 320px (144 checks); Manrope headings, IBM Plex Mono body, no document overflow or broken images. Enlarged-text check passed.
- Existing `scripts/test-mobile-hero.js`: passed at 13 viewport sizes from 320 to 2560px, including enlarged text, touch, keyboard, Escape, native disclosures and sticky CTA behavior.
- Impeccable detector reviewed; additions reuse the existing palette and tokens. Black video letterboxing/backdrop is intentional. Existing unrelated palette advisories were left unchanged.
- Node syntax checks and `git diff --check`: passed.

Local review captures are in the ignored `.playwright-cli/` directory: `final-project-grid.png`, `final-video-section.png`, `final-video-section-mobile.png`, and desktop/mobile player captures.

## Limits and delivery

Real iPhone/Safari hardware was not available for verification. The player includes native controls, playsinline and feature-detected Safari video fullscreen; Chromium mobile emulation is not a physical iPhone check.

Work remains local. No deployment or push was performed. The pre-existing untracked `docs/implementation/` directory was preserved and excluded from the commit.

## Header logo follow-up, 12 November

Moved the homepage logo widths into shared `header.css` and removed the homepage-only duplicates and smaller internal-page overrides. The existing homepage sizes are preserved at each viewport. Browser verification covered all 48 public routes at 390px and 1440px, plus six representative internal pages at ten additional widths between 320px and 1920px: 156 comparisons passed with identical homepage/internal logo dimensions, no horizontal overflow and no overlap with header actions. Desktop catalogue and mobile service-header screenshots were inspected. Compose was rebuilt and all services are healthy. No push or deployment.
