---
type: story
id: ST-14-12
title: "Editor: sandbox debug panel UX (copyable diagnostics)"
status: done
owners: "agents"
created: 2025-12-29
updated: 2026-01-12
epic: "EPIC-14"
acceptance_criteria:
  - "Given a sandbox run has debug details available, when viewing sandbox results in the editor, then the user can expand a Debug panel showing stdout/stderr plus truncation badges."
  - "Given the Debug panel is shown, then the user can copy a JSON debug bundle and a human text bundle that include run_id, snapshot_id, version_id, status, started_at, finished_at, error_summary, stdout/stderr, and truncation metadata (bytes/max/truncated)."
  - "Given debug details are missing (stdout/stderr + metadata all absent), then the Debug panel is shown with a clear missing-details message."
  - "Given debug details exist but stdout/stderr are empty, then the Debug panel shows the copy: \"Ingen stdout/stderr för den här körningen.\""
dependencies:
  - "ST-14-11"
ui_impact: "Yes (SandboxRunner)"
data_impact: "No"
---

## Notes

AI alignment: provide a single “copy bundle” action so future chat UX can attach sandbox diagnostics without re-inventing formatting.

Reference: `docs/reference/ref-tool-editor-dx-review-2025-12-29.md`

## Decisions (2026-01-02)

- Panel location: render in `SandboxRunnerActions` so it follows the selected step (`displayedRun`).
- Visibility: show for completed runs; collapsed by default with a header row (Visa/Dölj) and copy buttons always visible.
- States:
  - Missing details: stdout/stderr + truncation metadata all absent.
  - No output: access present but stdout/stderr are empty strings → show “Ingen stdout/stderr för den här körningen.”
- Copy actions: two buttons, “Kopiera debug (JSON)” (primary) and “Kopiera debug (text)” (secondary).
- Bundles include: `run_id`, `snapshot_id`, `version_id`, `status`, `started_at`, `finished_at`, `error_summary`,
  `stdout`, `stderr`, `stdout_bytes`, `stderr_bytes`, `stdout_max_bytes`, `stderr_max_bytes`,
  `stdout_truncated`, `stderr_truncated`.
