---
type: story
id: ST-14-20
title: "Editor intelligence: toolkit completions/hover/lints"
status: done
owners: "agents"
created: 2025-12-29
updated: 2026-01-14
epic: "EPIC-14"
acceptance_criteria:
  - "Given the toolkit module exists, when authoring scripts, then the editor provides completions/hover docs for toolkit APIs."
  - "Given toolkit best practices exist, when authoring scripts, then the editor linter suggests them where relevant."
  - "Given the toolkit is not imported, then the editor does not produce false-positive errors."
  - "Given the toolkit is part of the recommended authoring path, then the editor intelligence surfaces it in a way that reduces reliance on AI (autocomplete/hover as first-line help) while also improving the quality of AI suggestions (shared vocabulary)."
dependencies:
  - "ST-14-19"
ui_impact: "Yes (editor intelligence)"
data_impact: "No"
---

## Notes

AI alignment: treat toolkit intelligence as the “static baseline”; AI chat/editing should build on top of the same conventions, not replace them.

Reference: `docs/reference/ref-tool-editor-dx-review-2025-12-29.md`
