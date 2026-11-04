# Product

## Platform
Web

## Stack
Django 5.2 LTS with server-rendered HTML, PostgreSQL and Docker Compose for local development. The existing static `wireframe/` remains an isolated Vercel preview.

## Users
Homeowners in Kaliningrad and the surrounding region are the primary audience. Commercial clients are a secondary audience.

## Product purpose
Show how VLICO combines ceiling systems and lighting, explain how price and timing are agreed, and help a visitor start a project conversation.

## Positioning
VLICO plans and installs stretched ceilings with integrated lighting for homes and commercial properties. The scope and estimate are agreed before installation.

## Page structure
- Full-screen, photo-led offer with a large VLICO wordmark.
- Editorial company statement about planning ceiling and lighting as one system.
- Selected work, including the documented Rumyantseva penthouse and Podlesnaya hotel project.
- A concise list of ceiling and lighting systems.
- A photo-led section explaining the project sequence.
- Contact form and oversized wordmark footer.

## Capabilities and constraints
- The hero contains no contact input. Its links stay within this page.
- The contact form is an interaction-only prototype. It validates fields locally and does not transmit or store submitted data.
- Do not invent a fixed price or installation duration. Explain that the estimate follows the measurement and selected system, and timing is agreed before work begins.
- State free measurement only for Kaliningrad. Discuss travel elsewhere in the region separately.
- Do not reuse the unconfirmed promotion in the supplied mockups.
- Keep the preview `noindex` and publish only the `wireframe/` directory. Do not expose the rest of `from-client/`.

## Evidence
Client materials state that VLICO has worked since 2009, completed more than 10,000 objects, and installed more than 500,000 m² of ceilings. These figures still need confirmation before publication. The client brief documents a penthouse at Rumyantseva 11 and the Podlesnaya hotel in Zelenogradsk. The hotel brief gives 10 floors, 49 rooms, and 5,500 m² of ceiling work, and says not to publish the price. No local case video was found.

## Product principles
- Make the service, pricing method, timing, region, and next step clear in the first screen.
- Use client photography for real projects and keep each case tied to its supplied brief.
- Keep the first screen focused on homeowners while showing commercial experience below.
- Agree the scope, estimate, and schedule before installation.
- Follow the VLICO-specific editorial system in `DESIGN.md`.

## Delivery stages

Milestone 1 establishes the server, database, migrations and durable public/private storage while preserving the homepage. The form remains explicitly demonstrational until milestone 3. Milestone 2 adds the custom portfolio cabinet; milestone 3 adds stored leads, Telegram delivery and a numeric calculator with editable provisional rates; milestone 4 adds six service pages, cooperation, Yandex reviews, analytics and SEO; milestone 5 verifies and deploys to the client's existing cloud server/domain.

The client will review provisional calculator prices selected for local development. Versioned rates and calculation snapshots preserve historical estimates. Eva and CRM integration follow when documentation and credentials are available.

## Milestone 2 delivered

A custom authenticated portfolio cabinet manages project text, photo uploads, ordering, cover selection, result/process groups, preview, publishing, unpublishing and archive/restore. Public project pages, the catalog and featured homepage entries read published database content. Project sitemap entries change immediately without rebuilding. Private editorial notes and missing-data placeholders are restricted to the cabinet/preview.

Eight prepared drafts can be seeded with the included command; their photo grouping is provisional where source evidence is incomplete. These are not eight confirmed distinct completed orders. Published portfolios should only use confirmed records. Forms remain demonstration-only until milestone 3.

## Project categories and homepage publication

Project categories are independently managed in the cabinet and support multiple selections per project. Six initial ceiling/light categories can be edited or deleted without changing services or losing projects. Public category tags and filters use published projects only. All published projects now appear on the homepage automatically in configured order; the former featured-only selection is removed from the editing workflow.
