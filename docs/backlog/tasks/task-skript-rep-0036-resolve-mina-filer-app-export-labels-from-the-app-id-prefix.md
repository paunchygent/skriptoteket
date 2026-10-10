---
type: task
id: TASK-SKRIPT-REP-0036
title: Resolve Mina filer app-export labels from the app id prefix
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-10'
status: proposed
closeout_review:
  record: inline
  status: not_started
task_kind: repository
acceptance_criteria:
- APP_EXPORT files whose source artifact id is a plain app id or an app-scoped id
  shaped <app_id>:<parts> show the curated app title in Mina filer; unknown app ids
  keep the generic App-export label.
backlog_document_profile: contract-derived
---

## Implementation Contract

Mina filer resolves an `APP_EXPORT` file's source label by looking up its
`source_artifact_id` as a curated app id. Apps that save app-scoped ids
(`documents.conversion_hub:exam-converter:{job_id}:{artifact_key}` and
`documents.conversion_hub:exam-workspace:{lineage_id}:v{n}`) miss that lookup
and show the generic "App-export" label. Resolve the app id as the part of
`source_artifact_id` before the first `:`, keep plain app-id rows working, and
keep the generic label for unknown apps.

## Contract Inputs

- `application/scripting/handlers/list_vault_files.py` and
  `_vault_helpers.py` own the label lookup.
- Writers: Exam Converter saves and the exam workspace document store
  (TASK-SKRIPT-39-04-01) use app-scoped ids; older rows use plain app ids.
- Assigned by the user in the TASK-SKRIPT-39-04-01 session on 2026-10-10 as a
  separate small cleanup.

## Core Vertical And Performance

`list vault files -> APP_EXPORT row -> app id from prefix -> curated app
title`. One string split per listed row; no new queries or persistence.

## Validation

- Unit tests cover the three shapes (plain app id, Exam Converter artifact id,
  exam workspace version id) plus the unknown-app fallback:
  `tests/unit/application/scripting/handlers/test_vault_source_labels.py`.
- `pdm run lint`, `pdm run typecheck`, and the focused tests pass.

## Stop Conditions

- Stop if a writer stores an app id that itself contains `:`.
- No schema or data migration; existing rows keep their stored ids.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| D1  | The app id is the `source_artifact_id` text before the first `:`, trimmed; a value without `:` is the app id itself. |
| D2  | Unknown or empty app ids keep the generic "App-export" label. |
| D3  | The fix ships as its own commit, separate from TASK-SKRIPT-39-04-01. |
