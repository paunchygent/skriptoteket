---
type: story
id: ST-11-14
title: "Admin tools status enrichment"
status: done
owners: "agents"
created: 2025-12-22
epic: "EPIC-11"
acceptance_criteria:
  - "Given an admin visits /admin/tools, when the page loads, then tools are split into 'Pågående' and 'Klara' sections"
  - "Given a tool has no versions, when displayed in 'Pågående', then it shows 'Ingen kod' status badge"
  - "Given a tool has a draft version, when displayed in 'Pågående', then it shows 'Utkast' status badge"
  - "Given a tool has a version IN_REVIEW, when displayed in 'Pågående', then it shows 'Granskas' status badge"
  - "Given a tool has an active version, when displayed in 'Klara', then it shows toggle with 'Publicerad'/'Ej publicerad' label"
ui_impact: "Restructures AdminToolsView into two sections with richer status display."
dependencies: ["ST-11-11", "ADR-0033"]
---

## Context

ST-11-11 delivered the basic AdminToolsView with publish/depublish. Admins lacked visibility into
tool development lifecycle - they could not distinguish between tools awaiting code, those with
drafts in progress, and those pending review.

This story adds lifecycle visibility by:

- Separating tools by development stage (active_version_id null/not-null)
- Showing version-derived status for tools in development

Documented in ADR-0033.

## Notes

### ADR reference

- ADR-0033: Admin tool status enrichment for lifecycle visibility

### Backend changes

- Added `ToolVersionStats` value object to `domain/catalog/models.py`
- Added `get_version_stats_for_tools()` to `ToolVersionRepositoryProtocol`
- Implemented efficient batch aggregation in `PostgreSQLToolVersionRepository`
- Updated `ListToolsForAdminHandler` to include version stats
- Extended `AdminToolItem` DTO with `version_count`, `latest_version_state`, `has_pending_review`

### Frontend changes

- Split AdminToolsView into two sections: "Pågående" and "Klara"
- Added status badge logic for development tools
- Toggle + label ("Publicerad"/"Ej publicerad") only in "Klara" section

### Files modified

- Backend:
  - `src/skriptoteket/domain/catalog/models.py` - ToolVersionStats
  - `src/skriptoteket/protocols/scripting.py` - Protocol extension
  - `src/skriptoteket/infrastructure/repositories/tool_version_repository.py` - Aggregation query
  - `src/skriptoteket/application/catalog/queries.py` - Result type
  - `src/skriptoteket/application/catalog/handlers/list_tools_for_admin.py` - Handler update
  - `src/skriptoteket/di/catalog.py` - DI wiring
  - `src/skriptoteket/web/api/v1/admin_tools.py` - DTO extension
- Frontend:
  - `frontend/apps/skriptoteket/src/views/admin/AdminToolsView.vue` - Two-section layout
  - `frontend/apps/skriptoteket/src/api/openapi.d.ts` - Type updates
- Docs:
  - `docs/adr/adr-0033-admin-tool-status-enrichment.md`

### Status labels (Swedish)

| Condition | Label | Style |
|-----------|-------|-------|
| version_count == 0 | "Ingen kod" | muted background |
| has_pending_review == true | "Granskas" | warning color |
| latest_version_state == "draft" | "Utkast" | subtle border |
| is_published == true | "Publicerad" | success text |
| is_published == false | "Ej publicerad" | muted text |
