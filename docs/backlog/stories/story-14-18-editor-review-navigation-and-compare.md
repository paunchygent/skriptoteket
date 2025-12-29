---
type: story
id: ST-14-18
title: "Editor: review navigation improvements (compare targets + deep links)"
status: ready
owners: "agents"
created: 2025-12-29
epic: "EPIC-14"
acceptance_criteria:
  - "Given a reviewer is in an in_review version, when opening compare, then the UI selects a sensible default target (derived_from_version_id if present, else previous visible version)."
  - "Given the reviewer shares a link, then compare state can be deep-linked via query params without leaking access."
  - "Given there are unsaved changes, then switching versions/compare targets prompts for confirmation."
dependencies:
  - "ST-14-17"
ui_impact: "Yes"
data_impact: "No"
---

## Notes

Reference: `docs/reference/ref-tool-editor-dx-review-2025-12-29.md`
