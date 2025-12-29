---
type: story
id: ST-06-13
title: "Lint gutter filtering and diagnostics polish"
status: ready
owners: "agents"
created: 2025-12-29
epic: "EPIC-06"
acceptance_criteria:
  - "Given diagnostics include info/hint, when markers render in the gutter, then only error/warning are shown as gutter markers"
  - "Given info/hint diagnostics exist, when the user hovers a gutter marker or opens the lint panel, then info/hint diagnostics remain discoverable"
  - "Given any diagnostic is produced, when it is surfaced in UI, then it includes a stable source identifier"
ui_impact: "Reduces gutter clutter while keeping lower-severity diagnostics discoverable."
dependencies: ["ST-06-10"]
---

## Context

If every diagnostic is shown as a gutter marker, the gutter becomes noisy. IDEs prioritize errors/warnings in the gutter
while still showing informational hints in the Problems list and hover UI.

## Scope

- Configure `lintGutter({ markerFilter, tooltipFilter })`:
  - gutter markers: only `error` and `warning`
  - tooltip: all diagnostics
- Ensure all diagnostics include `source` for grouping and filtering.
