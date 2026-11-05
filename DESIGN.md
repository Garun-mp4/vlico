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
typography:
  family: "IBM Plex Mono"
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

Use Eleos as a composition and motion reference: a full-frame hero, oversized wordmark, visible 12-column grid, editorial project layouts, thin rules, and a large cropped wordmark in the footer. Build the page with new VLICO markup, styles, copy, and imagery. Keep Eleos branding and project content out of the VLICO site.

The result should feel like an architecture and interiors portfolio, with the ceiling and light as the subject. Keep the supplied green VLICO mark as the brand accent. The page's main canvas stays warm cream, the dark sections use charcoal, and photography carries most of the visual richness.

## Color and surface

- Use `#f2f1e9` for the primary canvas and `#eae8dd` for the softer sand surface.
- Use `#19191a` for text on light backgrounds and `#f2f1e9` on dark backgrounds.
- Reserve `#27be82` for the VLICO mark, active states, and a rare detail.
- Draw vertical grid guides and section rules in the existing warm gray. Avoid cards with rounded corners, pill buttons, gradients, and stacked shadows.
- Grade photography with restrained warmth and reduced saturation. Keep architectural lines legible. Use grain lightly and only over the hero image.

## Typography

Use the locally hosted IBM Plex Mono family in regular, medium, and semibold weights. Set major headings in uppercase with tight tracking and compact leading. Keep body copy in sentence case, left aligned, and no wider than about 60 characters per line. Use small uppercase labels for sections, places, and image captions. The VLICO wordmark is oversized text, not an imported copy of the Eleos wordmark.

## Grid and rhythm

On desktop use 12 columns across the viewport with gutters between 20px and 64px and a 24px maximum column gap. At tablet widths use eight columns; on mobile use six columns with 20px gutters. Keep text and image edges aligned to the same columns. Use an asymmetric rhythm: offset project images and captions, and let later gallery images step down the grid. Collapse to a single readable flow on phones.

Major sections receive generous top and bottom space. Use hairline rules for project metadata, case facts, and solution lists. Leave large open areas around headlines. Do not fill empty space with decorative icons or unsupported statistics.

## Components and behavior

- Header sits over the hero and turns into a flat cream navigation bar after scroll. Mobile navigation uses a compact disclosure menu.
- Hero shows a full-bleed ceiling photograph, dark warm overlay for legibility, large VLICO wordmark, offer copy, and same-page links. Do not put a phone field in the hero.
- Project entries use real VLICO photos and only case facts present in the supplied brief. Avoid promo graphics and generated imagery presented as documented work.
- Solution rows remain open and text-led. Hover shifts the row slightly and moves its arrow.
- The contact form appears at the end of the page. Milestone 1 preserves its explicit demonstration state; milestone 3 replaces this with server submission and truthful loading, success and error states.
- Use a brief page cover, subtle image settling, once-only scroll reveals, and small arrow transitions. Keep motion on opacity and transforms; respect `prefers-reduced-motion`.

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

Reuse the existing canvas, mono public typography and cabinet system sans. Keep forms flat, with visible labels, 48px public controls and 16px input text on phones. The calculator is one shared eight-step configurator on the homepage after solutions and on /calculator/. Desktop uses a unified 40/60 visual/question shell; mobile places the question and options before a compact diagram or preview. Use native radio and checkbox inputs, flat image choices, explicit back/continue controls, a progress indicator, and numeric steppers. Preserve answers when navigating; store only the versioned configuration draft in sessionStorage. Show an itemized result before offering contact and optional plan. SVG illustrates geometry and junction principles; mark AI material illustrations explicitly. Unknown base dimensions or material require an individual estimate, while missing quantities and unpriced work produce explicit warnings. Unknown perimeter has a prominent textual explanation. Never autoplay steps or erase entered fields after an error.

Public errors use `#8b302b` on the canvas, inline field feedback and a readable summary; saved state confirms database receipt rather than promising Telegram delivery. Keep existing native inputs, focus feedback, file-progress indication and explicit consent. Cabinet lead/rate controls have 44px targets; six navigation items form a three-column grid on small phones. Rate changes, private downloads and delivery retries use the existing cabinet vocabulary. Motion only supports feedback and respects reduced motion.


## Configurator controls and diagrams

The calculator extends the public form semantics: control border `#a6a498`, selected fill `#ddedea`, accessible focus/selection `#075f40`, errors `#8b302b`, neutral hover `#e6e5db`. Diagram wall tone `#b6b4a9` and LED amber `#b17c25` / `#a77829` distinguish physical components, never actions or text. All control text uses ink/body from the existing palette. Photos and diagrams keep explicit aspect ratios. ES module dependencies are fingerprinted by the existing static manifest pipeline.


## Material comparison

Compare matte PVC, satin PVC, gloss PVC and textile in one identical room, camera and daylight. Use a 2×2 grid with full 4:3 images and concise optical descriptions; help-with-choice spans the last row. Show a labelled matte preview before a choice without preselecting the answer. The native enlarged-image dialog preserves focus and closes with Escape. Large images use 1440px WebP with 480px variants for cards. Satin/gloss express a preference pending availability and price confirmation; no invented finish tariff. Store the material group and surface texture separately in calculation snapshots.


## Ceiling-wall junction comparison

The edge step uses three matched architectural detail images: classic white closed joint, unlit dark shadow gap, and concealed warm LED floating edge. Frame the same corner closely enough to read the junction at card size. Unknown/help answers are text-only. Reuse the image-preview dialog for both surface and edge choices, with labelled examples before selection and explicit AI provenance. No cross-section diagram appears in edge answer cards. Tariffs and selection codes remain unchanged.


## Lighting comparison

The lighting step uses five generated views of the same room at consistent dusk ambient exposure: recessed spots, integrated lines, magnetic tracks, pendant, perimeter LED. No client photographs or SVG substitutes appear in lighting answer cards. Show full 4:3 frames, explain the lighting character briefly, and reuse the enlarged-image dialog. Latest selected lighting drives the preview; a separate labelled group can inspect selected systems without changing the configuration. State clearly that each illustration shows one system, not a composite simulation of all selected lights. None/undecided answers remain text-only. Preserve quantities, exclusivity and server tariffs.


## Curtain comparison

Show four generated views of exactly one window and room: visible ceiling track, concealed ceiling niche, wall-mounted rod, and uncovered window without curtains. Use a closer window framing so the top fixing is readable. Keep unknown/help text-only; never illustrate it with a specific mounting system. Reuse 4:3 responsive images, selected preview and the enlarged-image dialog. Remove the old client photo and curtain cross-sections from the calculator; SVG now only explains room geometry. Preserve length-field conditions, pricing and saved selections.

## Live calculator price

Keep one price block above the desktop visual, sticky at 95px inside its sidebar. Large tabular mono numerals carry the known total; a short note distinguishes missing base data, partial positions and a completed preliminary estimate. Show the latest total difference and server-derived unit/whole-position prices beside relevant choices. No browser tariff table or guessed finish premium. During recalculation hide the previous number; errors offer an explicit retry. On phones the same block becomes one bottom panel, reserves its measured height in the calculator and includes the safe-area inset. Hide it while text fields have focus and outside the question shell; navigation stays in document flow. Full warnings remain available on desktop and on the final itemized result.
