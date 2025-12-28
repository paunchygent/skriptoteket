---
type: epic
id: EPIC-14
title: "Admin tool authoring (draft-first workflow)"
status: active
owners: "agents"
created: 2025-12-25
updated: 2025-12-28
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
- [ST-14-04: Editor sandbox input_schema form preview](../stories/story-14-04-sandbox-input-schema-form-preview.md)
- [ST-14-05: Editor sandbox settings parity](../stories/story-14-05-editor-sandbox-settings-parity.md)
- [ST-14-06: Editor sandbox preview snapshots](../stories/story-14-06-editor-sandbox-preview-snapshots.md)
- [ST-14-07: Editor draft head locks](../stories/story-14-07-editor-draft-head-locks.md)
- [ST-14-08: Editor sandbox settings isolation](../stories/story-14-08-editor-sandbox-settings-isolation.md)

## Risks

- Slug validation/publish guards can block publishing of existing draft tools until slugs/taxonomy are fixed.
  - This is expected and should surface as actionable validation errors for admins.

## Dependencies

- ADR-0037 (tool slug lifecycle)
- Existing editor + metadata/taxonomy panels:
  - ST-11-17 (metadata editor)
  - ST-11-20 (tool taxonomy editor)
