---
type: story
id: ST-10-06
title: "Curated app execution + persisted runs"
status: ready
owners: "agents"
created: 2025-12-19
epic: "EPIC-10"
acceptance_criteria:
  - "Given a user starts a curated app action, when execution completes, then a run is persisted with source_kind=curated_app and curated_app_id/app_version"
  - "Given a curated app returns typed outputs/actions/state, when normalized, then ui_payload is stored and rendered using the same UI contract as tools"
  - "Given a curated app run produces artifacts, when listed, then artifacts are downloadable with the same path safety rules as tool runs"
data_impact: "Extend tool_runs to support curated source_kind fields (or introduce a separate curated_app_runs table)."
dependencies: ["ADR-0023", "ADR-0024", "ST-10-03"]
---

## Context

Curated apps must be auditable and consistent with tool execution UX, while remaining separate from the tool version
governance model.

