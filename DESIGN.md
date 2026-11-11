---
name: VLICO Editorial Architecture
description: A restrained, photo-led visual system for VLICO ceilings and integrated lighting.
colors:
  canvas: "#f2f1e9"
  canvas-soft: "#eae8dd"
  ink: "#19191a"
  body: "#4d4c47"
  muted: "#68675f"
  rule: "#d5d3c8"
  night: "#191a19"
  night-ink: "#f2f1e9"
  brand: "#27be82"
  form-control-border: "#a6a498"
  focus: "#075f40"
  error: "#8b302b"
typography:
  family: "IBM Plex Mono"
  headings: "Manrope"
  weight-regular: 400
  weight-medium: 500
  weight-semibold: 600
  display: "clamp(2.1rem, 4.4vw, 4.5rem) / 0.99"
  body: "0.8rem / 1.6"
  micro: "0.625rem / 1.5"
layout:
  desktop: "12 columns, viewport gutters 3.35vw, 1.25vw column gap"
  tablet: "8 columns"
  mobile: "6 columns, 20px gutters"
  section-space: "clamp(90px, 11vw, 180px)"
components:
  primary-action: "Underlined text link with arrow; no pill button"
  project-meta: "Open rows separated by one-pixel rules"
  solution-row: "Number, title, short detail, arrow"
  form-field: "Transparent field with a single bottom rule"
motion:
  entrance: "Short page-cover wipe, image scale settle, wordmark and copy reveal"
  scroll: "Once-only opacity and vertical reveal on section entry"
  duration: "220ms for controls, 700-1050ms for section and hero motion"
  reduced-motion: "Disable the cover, reveal transforms, and smooth scrolling"
---

# VLICO Editorial Architecture

## Direction

Use Eleos as a composition and motion reference: an editorial, photo-led first screen, consistent 12-column alignment, editorial project layouts, thin rules, and a large fully visible wordmark in the footer. Build the page with VLICO markup, styles, copy, and imagery. Keep Eleos branding and project content out of the VLICO site.

The result should feel like an architecture and interiors portfolio, with the ceiling and light as the subject. Keep the supplied green VLICO mark as the brand accent. The page's main canvas stays warm cream, the dark sections use charcoal, and photography carries most of the visual richness.

## Color and surface

- Use `#f2f1e9` for the primary canvas and `#eae8dd` for the softer sand surface.
- Use `#19191a` for text on light backgrounds and `#f2f1e9` on dark backgrounds.
- Reserve `#27be82` for the VLICO mark, active states, and a rare detail.
- Use the existing column alignment without decorative grid guides; keep functional section rules in warm gray. Avoid cards with rounded corners, pill buttons, decorative gradients, and stacked shadows. Keep pointer responses restrained and tied to an actionable element.
- Grade photography with restrained warmth and reduced saturation. Keep architectural lines legible. Use grain lightly and only over the hero image.

## Typography

Use locally hosted Manrope for all headings and solution titles, and IBM Plex Mono in regular, medium, and semibold weights for body text and interface labels. Set major headings in uppercase with tight tracking and compact leading. Keep body copy in sentence case, left aligned, and no wider than about 60 characters per line. Use small uppercase labels for sections, places, and image captions. The footer SVG wordmark also uses Manrope, preserving its responsive sizing and pointer highlight.

## Grid and rhythm

On desktop use 12 columns across the viewport with gutters between 20px and 64px and a 24px maximum column gap. At tablet widths use eight columns; on mobile use six columns with 20px gutters. Keep text and image edges aligned to the same columns. Use an asymmetric rhythm: offset project images and captions, and let later gallery images step down the grid. Collapse to a single readable flow on phones.

Major sections receive generous top and bottom space. Use hairline rules for project metadata, case facts, and solution lists. Leave large open areas around headlines. Do not fill empty space with decorative icons or unsupported statistics.

## Components and behavior

- All public pages share the same header. It is a flat cream bar from the start. Project directions come from editable portfolio categories. The catalogue link and disclosure button remain separate, with a quick 180ms panel transition, keyboard/Escape support and a touch disclosure inside the mobile menu.
- The homepage hero is one photographic row. The large interior carries the heading and project action over a warm dark scrim. Four tall, equal-height photographs share its top and bottom edges, with Manrope display headings, neutral IBM Plex Mono labels and the existing night palette. Keep the confirmed experience/proof line, a prominent project CTA, cost and measurement links, and direct phone/Telegram/WhatsApp links. Do not put a phone input in the hero.
- Project entries use real VLICO photos and only case facts present in the supplied brief. Avoid promo graphics and generated imagery presented as documented work.
- Solution rows remain open and text-led. Hover shifts the row slightly and moves its arrow.
- Desktop project-direction links reuse the solution preview engine: a small inertial image stays beside the dropdown without intercepting clicks. Known directions use their service illustration; custom directions use a published project cover, with no private draft imagery. Decorative previews stay disabled on touch, stop animating when idle, and remain stationary for reduced motion.
- Category visibility is editable in the cabinet. Hidden categories stay available to editors but disappear from public navigation, filters and project labels; their published projects remain in the catalogue. The process-only “Монтажные работы” and unprepared “Транспарентные потолки” directions start hidden.
- The contact form appears at the end of the page. Milestone 1 preserves its explicit demonstration state; milestone 3 replaces this with server submission and truthful loading, success and error states.
- Keep the homepage about section editorial and dark: concise company copy on the left, the supplied founder portrait on the right, with a linked two-line caption. On phones, stack the copy, portrait and caption before the data-driven project gallery. Do not publish an unapproved first-person quote or replace existing project photographs.
- Use a brief page cover, subtle image settling, once-only scroll reveals, native solution disclosures, and small arrow transitions. Keep motion on opacity and transforms; respect `prefers-reduced-motion`.

## Copy rules

Name the service plainly. Explain that price follows measurement and selected system, and that the schedule is agreed before installation. Say that free measurement applies only in Kaliningrad. Keep copy concise and grounded in the client materials. Avoid long dash punctuation, exaggerated promises, and claims that the briefs do not support.

## Server migration

The homepage HTML now lives in `backend/templates/site/home.html`. CSS, JavaScript, fonts and prepared imagery are shared with `wireframe/`. Preserve this visual system as service, case and cooperation pages are added. The custom administration interface prioritizes readable forms and task completion.

## Portfolio and cabinet (milestone 2)

The public portfolio extends the existing cream/graphite visual system, mono typography and photo-led composition. Case headers, metadata rows, project galleries and a restrained closing CTA share the same gutters. Gallery motion is limited to feedback; a native dialog supports keyboard, Escape and touch.

The cabinet uses system sans at 16px for readable editing, with a mono VLICO wordmark. Dense work remains on a light canvas without entrance animations. Flat lists, standard labelled fields and explicit publication actions take priority over marketing composition. Semantic UI colors: success/focus `#075f40` on `#ddedea`, errors `#82251e` on `#f9e9e5`, destructive actions `#8c2424`, muted text `#5c5b54`, control border `#9d9c90`, canvas `#f6f5ef`, white input surfaces. The active tab underline indicates selection; it is not a decorative card accent.

## Photo editing

The cabinet uses a native dialog for protected image preparation. A live 4:3 canvas matches the site's image frames; fit mode keeps the full subject with cream padding. Crop, scale, position and rotation controls remain keyboard-operable native inputs. A sequential upload queue preserves already saved photos, reports progress and allows skipping. Save/close controls remain visible while scrolling. No entrance choreography is added to this work surface.

## Project category navigation

Category controls remain text-led: simple flat rows in the cabinet, standard checkboxes in the project form, wrapping underlined filters and compact linked labels on public cards. Multiple categories are supported without nesting dropdowns or adding decorative badges. Destructive removal uses a dedicated confirmation page explaining what remains intact. Navigation wraps on small screens and long category names wrap without horizontal overflow.


## Cabinet workspace redesign

The admin is an Operate surface for a nontechnical editor. Preserve the warm VLICO canvas and mono wordmark; use system sans for work. The Notion reference library informs neutral surfaces, hairlines, density and predictable controls, without importing its marketing palette or layout. Use 29px page headings, 19px sections, 15px inputs, 12–13px supporting copy and 44px main controls. Cabinet tokens live in `body.cabinet` in `cabinet.css`; small 4–6px radii distinguish work controls from the public editorial pages. Secondary neutral surfaces: header `#fbfaf6`, upload `#faf9f5`, panel `#efeee6`, row hover `#f0efe8`, muted bands `#eae8df`. Button hover `#30332f`, destructive border `#c9a4a0`; supporting text `#55544c`, `#51514e`, placeholder `#737268`, placeholder icon `#77766b`.

Projects use horizontal rows with uniform 80×64 thumbnails, date, status and a disclosure menu. Search, category, status and sort compose on the server; client enhancement replaces only results, cancels stale requests and retains the list on network errors. Counts reflect the current search/category across statuses.

The editor uses a main work column and 300px publication rail, separated by 40px. Sections: gallery, basic information, description, characteristics/categories, display settings and private notes. The first section is one bordered photo workspace with upload controls, compact thumbnails, cover outline, overlay menus, an add-photo tile and a shared ordering footer. Fields belong to one project form; photo forms remain independent. Text changes save explicitly with visible dirty/saving/saved/error states. Saved data is the publication and preview source. Never publish while text is dirty. On narrow screens the rail enters the document flow and the same save control stays fixed at the bottom, with reserved content padding.

The gallery uses three thumbnail columns, then two where space is constrained. Clicking a photo opens a native dialog styled as a side panel for accessible descriptions, captions and gallery group. Cropping/rotation keep the existing dedicated image editor and sequential queue. All controls are available without hover. Native dialogs retain focus, Escape and discard confirmation. Drag reorder commits one complete order with a project revision; failure restores the prior order. Up/down actions remain available for keyboard/touch. Motion stays limited to brief control feedback and respects reduced motion. No decorative screen entrance animation.

## Homepage project photos

Each homepage card keeps a 4:3 photo viewport. Start with its chosen cover, then show remaining photos in their saved order. Use native horizontal scroll snapping for touch, mouse dragging, and 44px previous/next buttons that remain visible without hover. Controls use the canvas background, ink text, a hairline border and a small photo counter; disable them at the ends and omit them for single-photo projects. Native vertical page scrolling and pinch zoom remain available. Keyboard changes and reduced-motion navigation are immediate; other arrow changes use browser smooth scrolling. No autoplay or nested project carousel. Photo clicks retain the case link, while dragging suppresses navigation. The catalog keeps its cover-only grid.

## Leads and calculator

Reuse the existing canvas, mono public typography and cabinet system sans. Keep forms flat, with visible labels, 48px public controls and 16px input text on phones. The homepage and /calculator/ share one three-field quick-v1 form: object type, ceiling area and requested solution. Do not calculate or display a numeric price from these answers; show “Для предварительного расчёта уточним детали” and offer contact only after the visitor requests a preliminary estimate. Preserve the three answers in the lead snapshot and notifications, and do not persist personal data or form answers in browser storage. Keep consent, signed submission tokens, CSRF, throttling, idempotency and clear validation/network recovery. Detailed v2 estimates and their historical snapshots stay versioned and are not loaded as the public calculator interface.

Public errors use `#8b302b` on the canvas, inline field feedback and a readable summary; saved state confirms database receipt rather than promising Telegram delivery. Keep existing native inputs, focus feedback, file-progress indication and explicit consent. Cabinet lead/rate controls have 44px targets; six navigation items form a three-column grid on small phones. Rate changes, private downloads and delivery retries use the existing cabinet vocabulary. Motion only supports feedback and respects reduced motion.


The following sections document the retained v2 calculation model only. Their controls are not loaded on public pages; the v2 estimate API and historical snapshots remain intact.

## Retained v2 configurator controls and diagrams

The calculator extends the public form semantics: control border `#a6a498`, selected fill `#ddedea`, accessible focus/selection `#075f40`, errors `#8b302b`, neutral hover `#e6e5db`. Diagram wall tone `#b6b4a9` and LED amber `#b17c25` / `#a77829` distinguish physical components, never actions or text. All control text uses ink/body from the existing palette. Photos and diagrams keep explicit aspect ratios. ES module dependencies are fingerprinted by the existing static manifest pipeline.


## Retained v2 material comparison

Compare matte PVC, satin PVC, gloss PVC and textile in one identical room, camera and daylight. Use a 2×2 grid with full 4:3 images and concise optical descriptions; help-with-choice spans the last row. Show a labelled matte preview before a choice without preselecting the answer. The native enlarged-image dialog preserves focus and closes with Escape. Large images use 1440px WebP with 480px variants for cards. Satin/gloss express a preference pending availability and price confirmation; no invented finish tariff. Store the material group and surface texture separately in calculation snapshots.


## Retained v2 ceiling-wall junction comparison

The edge step uses three matched architectural detail images: classic white closed joint, unlit dark shadow gap, and concealed warm LED floating edge. Frame the same corner closely enough to read the junction at card size. Unknown/help answers are text-only. Reuse the image-preview dialog for both surface and edge choices, with labelled examples before selection and explicit AI provenance. No cross-section diagram appears in edge answer cards. Tariffs and selection codes remain unchanged.


## Retained v2 lighting comparison

The lighting step uses five generated views of the same room at consistent dusk ambient exposure: recessed spots, integrated lines, magnetic tracks, pendant, perimeter LED. No client photographs or SVG substitutes appear in lighting answer cards. Show full 4:3 frames, explain the lighting character briefly, and reuse the enlarged-image dialog. Latest selected lighting drives the preview; a separate labelled group can inspect selected systems without changing the configuration. State clearly that each illustration shows one system, not a composite simulation of all selected lights. None/undecided answers remain text-only. Preserve quantities, exclusivity and server tariffs.


## Curtain comparison

Show four generated views of exactly one window and room: visible ceiling track, concealed ceiling niche, wall-mounted rod, and uncovered window without curtains. Use a closer window framing so the top fixing is readable. Keep unknown/help text-only; never illustrate it with a specific mounting system. Reuse 4:3 responsive images, selected preview and the enlarged-image dialog. Remove the old client photo and curtain cross-sections from the calculator; SVG now only explains room geometry. Preserve length-field conditions, pricing and saved selections.

## Live calculator price

Keep one price block above the desktop visual, sticky at 95px inside its sidebar. Large tabular mono numerals carry the known total; a short note distinguishes missing base data, partial positions and a completed preliminary estimate. Show the latest total difference and server-derived unit/whole-position prices beside relevant choices. No browser tariff table or guessed finish premium. During recalculation hide the previous number; errors offer an explicit retry. On phones the same block becomes one bottom panel, reserves its measured height in the calculator and includes the safe-area inset. Hide it while text fields have focus and outside the question shell; navigation stays in document flow. Full warnings remain available on desktop and on the final itemized result.

## Footer wordmark

The footer VLICO wordmark fills the available grid width with equal gutters and a clear gap above the dark footer bar. Keep all letters visible; never restore negative bottom margins or cropped type. A soft brand-green spotlight follows a fine pointer only over the letters, with a brief opacity fade. Touch and reduced-motion use a static wordmark. No autoplay or idle animation loop.

## Hero layout safety

Keep the copy, proof line and actions in the main photo panel’s flow. Reserve the panel height before the images load. At 1100px and wider, the overview and four solutions share one row. Exactly one occupies the wide track. Mouse movement onto another panel shifts the track in 260ms and reveals a display heading, description and action. The panel stays open until another is selected or Escape returns to the overview. Keyboard selection switches instantly; at tablet sizes use a two-by-two grid; on phones use a native horizontal rail with a visible next-card cue and no document-level overflow. Let the hero grow when the viewport is short or text is enlarged. Show the mobile project CTA only after the hero action has passed out of view; it must yield to the consent notice, open menu, visible contact section, and text-entry keyboard.

## Homepage project preview

Show at most six published projects on the landing page: two columns from 801px and one below. Use the large 3:2 desktop/tablet photo and a two-line description; mobile retains the 4:3 image. The full catalogue uses two columns from 801px and one below so tablet frames stay wide enough to read. Use the existing 640px thumbnail and full-size WebP derivative through `srcset` and accurate `sizes`; keep dimensions reserved and lazy-load galleries below the fold. Preserve arrows, dragging and swipe within each project, and let the project detail page show the full image. Place the full-catalogue link below the grid. Keep result and process galleries separate on detail pages.

The special-offer section uses an editorial two-column layout on the sand canvas: clear offer copy and a consultation action on the left, a labelled interior visualization on the right. Keep the gift callout flat and integrated into the image. Collapse to one column on phones and do not add eligibility conditions that have not been confirmed.

The homepage hero uses responsive WebP derivatives in `backend/static/home-hero/`, with its source artwork kept intact. Preload only the main interior at high priority. Set a focal point for each narrow solution photo so the ceiling detail remains recognizable. Use native `<details>` as the no-JavaScript and touch fallback. With JavaScript, the desktop row switches on mouse hover, click or keyboard selection. Below the wide breakpoint, cards disclose details in place. Keep the expanded state synchronized with `aria-expanded`. Do not autoplay, jump the page, or move focus when a card opens. Under reduced motion, remove transitions and scroll snapping.

## Homepage refinements, 11 November

The three new solutions continue the hero directly below the tall image panels, inside the same bounded width and gutters. Use a compact 24–36px heading and three photo-led columns on wide screens. Below 1100px use a native horizontal rail, showing two cards on tablets and one card with the next-card cue on phones. Include 48px previous/next controls and a current-card count when the rail overflows. Keep the full image composition, readable descriptions, immediate card actions and reduced-motion support.

The cookie notice stays fixed at the bottom left at every breakpoint, outside the hero grid. It never becomes a full grid row. On phones retain viewport gutters and the safe-area inset. The mobile project action yields to consent and visible interactive controls in both project and solution galleries. Successful lead forms offer an explicit new-request link while retaining duplicate protection.

The homepage partnership invitation is a full photo-and-copy section immediately after real projects and before the service list. Retain the approved headline and cooperation copy, a labelled AI visualization of a designer and technical specialist working together in a showroom inspired by the supplied VLICO office photo, and a high-contrast “Стать партнёром” action linking directly to `/partners/#partner-form`. On phones place the action before the photo. Keep the header “Партнёрам” link to the complete cooperation page.

The process section uses the approved three-line headline “СОВЕРШЕНСТВО / НАЧИНАЕТСЯ / С ДЕТАЛЕЙ.”, the supplied explanatory paragraph, and five numbered rule-separated stages. Keep the existing background, larger readable step labels, a five-column intro on wide screens, and one continuous reading order on phones.

The hero introduction pairs “Обсудить проект” with a transparent, light 1px outlined “Стать партнёром” button to its right. Keep both in the same row on phones with readable wrapping. Only the project button has the restrained pulse; the partnership action has no pulse.

Present the three approved hero advantages as a semantic list of compact, non-interactive labels: small cream bullet, thin translucent outline, lightly darkened background, 11px body type and 6px gaps. Let whole labels wrap naturally, with text wrapping inside them when enlarged. Keep them quieter than the two main actions and avoid animation or button-like hover states.

Public lead forms, including both partnership entry points, contain no file inputs and reject all file uploads at the form and submission boundaries. Keep existing private historical attachments and cabinet portfolio/article image uploads intact.


## Rating visibility and mobile rail spacing

Remove the decorative vertical grid overlay globally; retain the underlying layout grid and functional separators. At 1100px and wider, place the homepage Yandex rating inside the main photo, at the bottom right of the copy grid, alongside the contact links with a reserved 150px column. On tablets and phones retain the compact rating-and-reviews strip directly below the photo row, before the new solutions. Move the same unmodified live badge between these positions; do not duplicate it or hard-code its value. Without JavaScript retain the visible strip at all widths.

On phones, size the solutions rail to the active card, observing card/image/font size changes, so the long TEQTUM text does not leave a gap below the short smart-home card. Preserve all copy, horizontal swipe, arrow controls, zoom, and keyboard access. Keep only 16px of section padding after the rail. Restore natural equal-height columns on desktop.
