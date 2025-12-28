---
type: story
id: ST-14-08
title: "Editor sandbox settings isolation"
status: ready
owners: "agents"
created: 2025-12-27
epic: "EPIC-14"
acceptance_criteria:
  - "Given a draft head and settings_schema, when the user saves sandbox settings, then values are stored per user + draft head and do not affect production tool settings."
  - "Given the editor schema text is unsaved but valid, when sandbox settings are resolved or saved, then the backend validates and stores values using that schema."
  - "Given the settings schema is invalid JSON, when the sandbox settings panel is opened, then the UI shows a parse error and disables saving."
  - "Given sandbox settings are saved, when the next sandbox preview run starts, then the runner receives those values via SKRIPTOTEKET_MEMORY_PATH."
  - "Given no settings_schema exists, when the sandbox is shown, then the settings panel is hidden."
  - "Given the user does not own the draft head lock, when sandbox settings are resolved or saved, then the API rejects the request."
dependencies:
  - "ADR-0045"
  - "ST-14-06"
  - "ST-14-07"
links: ["EPIC-14", "ADR-0045"]
ui_impact: "Yes (SandboxRunner settings panel + API integration)"
data_impact: "Yes (sandbox settings sessions)"
risks:
  - "Mismatch between unsaved schema and stored values can cause validation errors; UI must surface actionable messages."
---

## Context

Settings are currently shared across sandbox and production runs when the schema
matches. This blocks rapid experimentation because settings changes leak into
normal tool runs.

## Goal

Provide sandbox-only settings persistence per user + draft head while supporting
unsaved schema edits.

## Non-goals

- Changes to the settings schema contract or field kinds.
- Persisting sandbox settings into published tool runs.

## Implementation plan

1) Add sandbox settings resolve/save endpoints that accept settings_schema.
2) Store settings under `sandbox-settings:{sha256(f"{draft_head_id}:{schema_hash}")[:32]}`.
3) Require draft head lock ownership for resolve/save.
4) Update sandbox settings UI to use the new endpoints.

## Test plan

- Unit: sandbox settings validation and context derivation.
- Manual: save sandbox settings, run preview, confirm output uses saved values
  and production runs remain unchanged.
