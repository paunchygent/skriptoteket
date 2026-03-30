---
type: story
id: ST-11-24
title: "Home view messaging reset for curated library"
status: in_progress
owners: "agents"
created: 2026-03-30
updated: 2026-03-30
epic: "EPIC-11"
acceptance_criteria:
  - "Given an unauthenticated visitor opens `/`, when the page renders, then the copy presents Skriptoteket as a professional app and tool library for teachers instead of implying that ordinary users can create their own scripts immediately."
  - "Given the current alpha role model, when the visitor reads the landing-page hero and supporting cards, then contributor/admin-only capabilities are described as approval-gated rather than as the default user journey."
  - "Given the landing page describes the current product value, when a visitor scans it, then the main promises center on logging in, running curated apps/tools, sharing trusted tools with colleagues, and GDPR-safe handling."
  - "Given this slice only resets messaging, when the page ships, then no new contributor-application workflow is implied as already available if the underlying form flow does not exist yet."
dependencies: ["ST-11-21", "ST-11-22"]
ui_impact: "Refreshes the unauthenticated `HomeView.vue` hero and supporting content without changing the authenticated dashboard shell."
data_impact: "No schema change."
---

## Context

The current landing page still leans on a broad 'create your own scripts' pitch, but the live role
model does not let ordinary self-registered users do that yet. In the current alpha, most users can
log in and use curated or published tools, while contributor/admin access is promoted manually.

That mismatch makes the home page feel less trustworthy than the product actually is.

## Implementation notes

### Messaging direction

- Present Skriptoteket as:
  - a professional app/tool library for teachers
  - a place to log in and use trusted tools
  - a place to share proven tools with colleagues
  - a product with GDPR-safe handling
- Remove or sharply tone down copy that suggests everyone can generate their own scripts today.
- Keep the page concise and factual; avoid marketing-style promise stacking.

### Scope boundary

- This slice is a messaging and structure reset only.
- A contributor-application form may be a future follow-up, but it is not part of this slice unless
  a dedicated story is approved separately.

### Verification

- Frontend unit test coverage for the updated landing-page copy/CTAs.
- Manual proof in local dev that `/` renders correctly in the unauthenticated state on desktop and
  mobile widths.
