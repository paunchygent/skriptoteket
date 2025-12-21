---
type: story
id: ST-11-12
title: "Script editor migration (CodeMirror 6)"
status: ready
owners: "agents"
created: 2025-12-21
epic: "EPIC-11"
acceptance_criteria:
  - "Given a contributor/admin visits the editor route, when the SPA loads, then CodeMirror 6 renders and supports save + draft workflows via the API"
  - "Given a user runs a sandbox test, when the run completes, then the SPA renders outputs/logs and allows artifact download"
ui_impact: "Replaces the current server-rendered editor and island surfaces with a unified SPA editor."
dependencies: ["ST-11-01", "ST-11-04", "ST-11-05"]
---

## Context

The script editor is the highest-complexity admin surface and benefits strongly from SPA state management and component
composition.
