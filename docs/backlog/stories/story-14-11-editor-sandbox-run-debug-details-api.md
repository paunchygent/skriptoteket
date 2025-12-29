---
type: story
id: ST-14-11
title: "Editor: sandbox run debug details API (stdout/stderr, gated)"
status: ready
owners: "agents"
created: 2025-12-29
epic: "EPIC-14"
acceptance_criteria:
  - "Given a sandbox run exists, when a maintainer/admin fetches the editor run details endpoint, then the response can include truncated stdout/stderr fields."
  - "Given a non-authorized user fetches the same endpoint, then stdout/stderr are omitted (or null) and are never exposed."
  - "Given stdout/stderr are large, when returned, then they are truncated to platform caps and truncation is signaled in the response."
dependencies:
  - "ST-14-06"
ui_impact: "Yes (enables editor UI)"
data_impact: "No (API surface change only)"
---

## Notes

Reference: `docs/reference/ref-tool-editor-dx-review-2025-12-29.md`
