---
type: story
id: ST-14-11
title: "Editor: sandbox run debug details API (stdout/stderr, gated)"
status: done
owners: "agents"
created: 2025-12-29
updated: 2026-01-12
epic: "EPIC-14"
acceptance_criteria:
  - "Given a sandbox run exists, when an authorized user fetches the editor run details endpoint, then the response includes stdout/stderr (truncated) along with explicit truncation flags."
  - "Given a non-authorized user fetches the same endpoint, then stdout/stderr are omitted (or null) and are never exposed."
  - "Given stdout/stderr are returned, then the response includes explicit caps/byte counts so the UI can clearly communicate truncation."
  - "Given stdout/stderr may contain sensitive data, when the endpoint is used, then logs remain metadata-only and never include stdout/stderr content."
dependencies:
  - "ST-14-06"
ui_impact: "Yes (enables editor UI)"
data_impact: "No (API surface change only)"
---

## Notes

AI alignment: keep debug details explicit, bounded, and easy to copy/attach without adding any server-side content logging.

Reference: `docs/reference/ref-tool-editor-dx-review-2025-12-29.md`
