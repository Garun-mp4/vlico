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
- Original Yandex reviews as the third main section, with three visible previews, the live rating and links to read or write reviews.
- Selected work, including the documented Rumyantseva penthouse and Podlesnaya hotel project.
- A concise list of ceiling and lighting systems.
- A photo-led section explaining the project sequence.
- Contact form and oversized wordmark footer.

## Capabilities and constraints
- The hero contains no contact input. Its links stay within this page.
- The server-site forms persist real leads without public file uploads; Telegram is a notification channel. The isolated legacy static preview retains its demonstration-only form.
- The owner authorized provisional numeric calculator rates for local review. Label the result preliminary and show its composition and exclusions. A final estimate follows measurement; installation timing is agreed separately.
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

Milestones 1–3 establish the server, database, durable storage, portfolio cabinet, stored leads, Telegram delivery and a numeric calculator with editable provisional rates. Milestone 4 now provides six service pages, cooperation, verified contacts, live Yandex reviews, consent-aware site analytics and SEO; milestone 5 verifies and deploys to the client's existing cloud server/domain.

The client will review provisional calculator prices selected for local development. Versioned rates and calculation snapshots preserve historical estimates. Eva and CRM integration follow when documentation and credentials are available.

## Milestone 2 delivered

A custom authenticated portfolio cabinet manages project text, photo uploads, ordering, cover selection, result/process groups, preview, publishing, unpublishing and archive/restore. Public project pages, the catalog and featured homepage entries read published database content. Project sitemap entries change immediately without rebuilding. Private editorial notes and missing-data placeholders are restricted to the cabinet/preview.

Eight prepared drafts can be seeded with the included command; their photo grouping is provisional where source evidence is incomplete. These are not eight confirmed distinct completed orders. Published portfolios should only use confirmed records.

## Milestone 3 delivered

One server workflow handles consultation, measurement, project discussion, calculator and partnership leads, including service/project context and first-touch attribution. The cabinet lists and processes leads, downloads private attachments and shows delivery/retry state. Editing a rate creates a version; each calculator lead keeps the applied version, selected parameters, line items and total. Unknown perimeter produces a clearly incomplete estimate rather than a guessed value.

PostgreSQL holds the notification queue. A dedicated Compose process sends Telegram messages and documents, records confirmed progress and retries explicit temporary failures. Ambiguous delivery needs manual review to avoid automatic duplicate messages. One marked test with its PDF was delivered to the configured Telegram after the recipient started the bot. Privacy, separate consent and cookie documents are implemented. Unknown operator, retention and infrastructure details remain bracketed fields to complete before launch; deployment and the real analytics dashboard remain milestone 5 checks.

## Project categories and homepage publication

Project categories are independently managed in the cabinet and support multiple selections per project. Six initial ceiling/light categories can be edited or deleted without changing services or losing projects. Public category tags and filters use published projects only. All published projects now appear on the homepage automatically in configured order; the former featured-only selection is removed from the editing workflow.

Public visitors do not attach files, including in the calculator and project inquiry. Existing private lead attachments remain accessible to authorized staff; portfolio photo management is unchanged.
