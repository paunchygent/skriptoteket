---
type: story
id: ST-SKRIPT-14-29
title: 'Editor: Pro mode combined bundle view (tool.py + schemas)'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: ready
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
epic: EPIC-SKRIPT-14
acceptance_criteria:
- Given a tool author switches to Pro mode, when the combined editor opens, then it
  shows a single buffer containing tool.py, input_schema.json, and settings_schema.json
  using the Bundle v1 headers.
- Given Pro mode is enabled, when the combined editor is opened for the first time,
  then the required section headers are prefilled even if a section is empty.
- Given the combined buffer is edited, when saving or running sandbox, then the editor
  splits the buffer into source_code + input_schema + settings_schema and uses the
  unsaved split values (snapshot preview parity).
- Given the combined buffer is malformed (missing/duplicate/unknown sections), when
  saving or running sandbox, then the operation is blocked and the UI shows an actionable
  error including the bundle section and line number.
- Given a schema section is present but not valid JSON array, when saving or running
  sandbox, then the operation is blocked and the UI shows an actionable error including
  the schema section and line number.
- Given a tool has an empty settings_schema section, when rendering the combined buffer,
  then the settings_schema section is collapsed by default to reduce noise.
- 'Given the combined buffer is broken, then the UI provides one-click recovery actions:
  (1) rebuild combined view from last saved fields, (2) switch to structured view
  to repair.'
retired_ids:
- ST-14-29
---

## Context

Source: `docs/backlog/stories/story-14-29-editor-pro-mode-combined-bundle-view.md`. Editor: Pro mode combined bundle view (tool.py + schemas).

Provide a developer-friendly “one artifact” editing experience without changing the persistence model. The combined buffer is a UI presentation: the backend persists `source_code`, `input_schema`, and `settings_schema` as separate fields as before. Single-line section headers, no end markers: ``` ...python... ...json array... ...json array... ``` Parsing rules: - Only treat lines as headers if they match exactly: - `^# >>> skt:bundle:v1 >>>$` - `^# >>> skt:file:(tool.py|input_schema.json|settings_schema.json) >>>$` - Content of a section is everything until the next header or EOF. - Duplicates or unknown section names are errors (no silent typos). - Escape rule: if a tool needs to include a

## Epic Contract Slice

The story retains the source behavior slice and its actor/consumer boundary.

## ADR Coverage

Source references: none recorded.

## Contract Inputs

- Source story and audit-approved migration authority.
- Current epic/relationship fields in candidate frontmatter.

## Live Verification Plan

Verify the story slice through its current tasks and retain focused evidence at closeout.

## Non-Goals

No adjacent capability, terminal record, or unapproved implementation scope is added.

## Notes

### Source evidence

### Goal

Provide a developer-friendly “one artifact” editing experience without changing the persistence model.

The combined buffer is a UI presentation: the backend persists `source_code`, `input_schema`, and `settings_schema` as
separate fields as before.

### Bundle v1 format

Single-line section headers, no end markers:

```
### >>> skt:bundle:v1 >>>
### >>> skt:file:tool.py >>>
...python...
### >>> skt:file:input_schema.json >>>
...json array...
### >>> skt:file:settings_schema.json >>>
...json array...
```

Parsing rules:

- Only treat lines as headers if they match exactly:
  - `^# >>> skt:bundle:v1 >>>$`
  - `^# >>> skt:file:(tool.py|input_schema.json|settings_schema.json) >>>$`
- Content of a section is everything until the next header or EOF.
- Duplicates or unknown section names are errors (no silent typos).
- Escape rule: if a tool needs to include a literal header line inside `tool.py`, prefix it with an extra `#` or a
  leading space (e.g. `## >>> ...`), since matching requires the exact single-`#` form at column 0.

### Notes

- `usage_instructions` stays in its dedicated UI surface (not in the combined buffer), but can be treated as a virtual
  file for AI context in a later story line.

## Decision And Assumption Ledger

| ID | Type | Status | Question/Assumption | Recommendation/Decision | Source |
| --- | --- | --- | --- | --- | --- |
| MIG-ST-SKRIPT-14-29 | migration | closed | How is source meaning preserved? | Preserve the source story contract and current status while changing identity only. | ST-SKILL-08-06; TASK-SKRIPT-REP-0003 |

## Plan Document Review

No specialist approval is asserted; parent review remains required.

## Story Closeout Review

No closeout evidence is asserted in this candidate.
