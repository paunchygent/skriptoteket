---
type: story
id: ST-14-34
title: "Settings suggestions from tool runs"
status: ready
owners: "agents"
created: 2026-01-12
epic: "EPIC-14"
dependencies:
  - "ADR-0057"
  - "ST-12-03"
acceptance_criteria:
  - "Given a tool run returns settings_suggestions, when the UI renders results, then a suggestion card appears without showing raw JSON."
  - "Given a user clicks Save on a settings suggestion, when the backend validates the payload, then settings are persisted and applied on future runs."
  - "Given a suggestion payload fails validation, when the user attempts to save, then the UI shows an actionable error and does not persist changes."
  - "Given a tool does not return settings_suggestions, when rendering results, then behavior is unchanged."
---

## Context

Tools may derive reusable settings (e.g., class rosters) from input files. Manual copy/paste into the settings panel is
error-prone and a poor UX. We need a safe, explicit mechanism to suggest settings changes from a run without allowing
the runner to persist settings directly.

## Notes

- The suggestion payload is non-persistent until the user explicitly saves.
- Validation must reuse the existing settings schema pipeline.
