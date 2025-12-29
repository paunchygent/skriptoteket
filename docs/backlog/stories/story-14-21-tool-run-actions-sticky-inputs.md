---
type: story
id: ST-14-21
title: "Tool run actions: remember prior inputs (sticky action forms)"
status: ready
owners: "agents"
created: 2025-12-29
epic: "EPIC-14"
acceptance_criteria:
  - "Given a user submits a next_action, when the same action is rendered again for the same tool version, then the form pre-fills matching fields with the last submitted values."
  - "Given a user reloads the page during an interactive session, when the next_action form is rendered again, then remembered values still pre-fill (at least within the same browser tab/session)."
  - "Given an action field is a file upload, when remembering inputs, then the UI does not attempt to persist file contents and leaves file fields empty."
  - "Given a user wants a clean slate, when choosing a reset/clear option, then remembered values are cleared for that tool+action."
dependencies:
  - "ST-14-03"
ui_impact: "Yes (ToolRunActions / action form UX)"
data_impact: "No"
---

## Context

Interactive tools often require repeated submissions of the same action while iterating. Today, the action form resets on
each render, forcing users (and tool authors in sandbox) to repeatedly retype the same values.

## Goal

Make next_action forms “sticky” by default (or via a small toggle), so repeated steps feel fast and predictable.

## Notes

Reference: `docs/reference/ref-tool-editor-dx-review-2025-12-29.md`
