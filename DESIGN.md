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
- The contact form appears at the end of the page. Its prototype behavior is local only and says that it does not transmit or store data.
- Use a brief page cover, subtle image settling, once-only scroll reveals, and small arrow transitions. Keep motion on opacity and transforms; respect `prefers-reduced-motion`.

## Copy rules

Name the service plainly. Explain that price follows measurement and selected system, and that the schedule is agreed before installation. Say that free measurement applies only in Kaliningrad. Keep copy concise and grounded in the client materials. Avoid long dash punctuation, exaggerated promises, and claims that the briefs do not support.
