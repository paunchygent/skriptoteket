---
type: story
id: ST-14-20
title: "Editor intelligence: toolkit completions/hover/lints"
status: ready
owners: "agents"
created: 2025-12-29
epic: "EPIC-14"
acceptance_criteria:
  - "Given the toolkit module exists, when authoring scripts, then the editor provides completions/hover docs for toolkit APIs."
  - "Given toolkit best practices exist, when authoring scripts, then the editor linter suggests them where relevant."
  - "Given the toolkit is not imported, then the editor does not produce false-positive errors."
dependencies:
  - "ST-14-19"
ui_impact: "Yes (editor intelligence)"
data_impact: "No"
---

## Notes

Reference: `docs/reference/ref-tool-editor-dx-review-2025-12-29.md`
