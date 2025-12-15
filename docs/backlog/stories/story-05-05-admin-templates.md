---
type: story
id: ST-05-05
title: "Admin template migration"
status: done
owners: "agents"
created: 2025-12-15
epic: "EPIC-05"
acceptance_criteria:
  - "Given the tools list loads, when viewing publish button, then it displays in burgundy"
  - "Given the script editor loads, when viewing CodeMirror, then it uses canvas background and navy border"
  - "Given a sandbox run completes, when viewing results, then they display in a brutal shadow card"
---

## Context

Migrating the administrative interfaces, including the complex script editor, to the new design system.

## Tasks

- Convert `admin_tools.html` with button hierarchy (publish=burgundy, depublish=outline)
- Convert `admin/script_editor.html` with editor layout, tabs, pills
- Convert `admin/partials/version_list.html` with row styling
- Convert `admin/partials/run_result.html` with card and status badges
- Apply CodeMirror theme overrides
