---
type: epic
id: EPIC-14
title: "Admin tool authoring (draft-first workflow)"
status: active
owners: "agents"
created: 2025-12-25
outcome: "Admins can quickly create draft tools directly from /admin/tools, iterate without contributor-only hoops, and publish only when slug and taxonomy are finalized."
---

## Scope

- Admin-only draft tool creation directly from `/admin/tools` (bypass suggestion stage).
- Draft placeholder slug convention for admin quick-create: `draft-<tool_id>`.
- Unify suggestion acceptance placeholder slug to `draft-<tool_id>` (single convention for all draft tools).
- Admin-only slug editing for unpublished tools (pre-publish churn support).
- Publish-time guards:
  - reject placeholder slugs (`draft-...`)
  - enforce slug validation + uniqueness
  - block publish until taxonomy is set (at least one profession and one category)
- Keep contributor suggestion flow intact; accepted suggestions still create a draft tool (ADR-0010), and admins finalize
  slug before publishing.

## Out of scope

- Post-publish slug renames, slug aliases, or redirects (explicitly deferred).
- Tool deletion UX (scrapped tools remain unpublished).
- Public/internal slug differentiation (no extra slug fields).

## Stories

- [ST-14-01: Admin quick-create draft tool](../stories/story-14-01-admin-quick-create-draft-tools.md)
- [ST-14-02: Draft slug edit + publish guards](../stories/story-14-02-draft-slug-edit-and-publish-guards.md)
- [ST-14-03: Editor sandbox next_actions parity](../stories/story-14-03-sandbox-next-actions-parity.md)

## Risks

- Slug validation/publish guards can block publishing of existing draft tools until slugs/taxonomy are fixed.
  - This is expected and should surface as actionable validation errors for admins.

## Dependencies

- ADR-0037 (tool slug lifecycle)
- Existing editor + metadata/taxonomy panels:
  - ST-11-17 (metadata editor)
  - ST-11-20 (tool taxonomy editor)
