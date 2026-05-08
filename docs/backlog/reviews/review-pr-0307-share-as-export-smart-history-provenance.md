---
type: review
id: REV-PR-0307
title: "Review: PR-0307 share-as-export Smart history provenance"
status: approved
owners: "agents"
created: 2026-05-08
updated: 2026-05-08
reviewer: "codex"
prs:
  - PR-0307
links:
  - EPIC-26
  - ST-26-06
  - ST-29-11
  - PR-0150
  - PR-0274
  - PR-0305
  - PR-0306
---

## TL;DR

`PR-0307` is approved after the retained repository mapper blocker was fixed.
Authenticated `Dela` now records Smart-history checkpoints with explicit
`share_artifact` provenance, PDF/Excel exports retain `export_job` provenance,
and the checkpoint repository tests prove both persisted mapper shapes.

## Problem Statement

The review target is deciding whether authenticated share creation can safely
be treated as a Smart-history source without weakening public guest boundaries
or losing existing export-job provenance.

## Proposed Solution

The implementation introduces a shared seating/grouping checkpoint recorder,
adds `export_job` versus `share_artifact` provenance to checkpoint domain and
database rows, wires authenticated share creation through the recorder after
share artifact persistence, and keeps public guest share creation outside the
recorder path.

## Artifacts to Review

| File | Focus |
|------|-------|
| `docs/backlog/prs/pr-0307-st-26-06-share-as-export-smart-history-provenance.md` | Scope, acceptance criteria, test plan |
| `src/skriptoteket/application/curated_apps/classroom_planner/handlers/authenticated_shares.py` | Authenticated share checkpoint callback |
| `src/skriptoteket/application/curated_apps/classroom_planner/handlers/checkpoint_recorders.py` | Shared checkpoint build/dedupe logic |
| `src/skriptoteket/domain/curated_apps/classroom_planner/checkpoints.py` | Seating checkpoint provenance contract |
| `src/skriptoteket/domain/curated_apps/classroom_planner/grouping_checkpoints.py` | Grouping checkpoint provenance contract |
| `src/skriptoteket/infrastructure/repositories/classroom_planner_seating_export_checkpoints.py` | Seating checkpoint persistence mapper |
| `src/skriptoteket/infrastructure/repositories/classroom_planner_grouping_export_checkpoints.py` | Grouping checkpoint persistence mapper |
| `migrations/versions/f2a7c9d4e6b8_add_share_checkpoint_provenance.py` | Provenance schema migration |
| `tests/unit/application/apps/classroom_planner/test_authenticated_shares.py` | Authenticated share checkpoint proof |
| `tests/unit/infrastructure/repositories/test_classroom_planner_seating_export_checkpoints.py` | Seating mapper proof |
| `tests/unit/infrastructure/repositories/test_classroom_planner_grouping_export_checkpoints.py` | Grouping mapper proof |

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Add explicit checkpoint source provenance | Needed so export jobs and authenticated shares can both produce Smart-history rows without conflating source identity | [x] |
| Share recorder is authenticated-only | Keeps public guest shares outside owner/account-backed Smart history | [x] |
| Reuse one recorder for export and share checkpoint dedupe | Preserves existing dedupe behavior while allowing share-created checkpoints | [x] |
| Close only with green repository mapper proof | The changed persisted provenance fields are read through the checkpoint repositories | [x] |

## Review Checklist

- [x] Scope is bounded to authenticated share-as-export Smart history.
- [x] Public guest share semantics remain excluded from account-backed history.
- [x] Domain and database source-provenance invariants are explicit.
- [x] Repository mapper proof is green for the new provenance shape.

## Review Feedback

**Reviewer:** `codex`
**Date:** `2026-05-08`
**Verdict:** `changes_requested`

### Required Changes

1. Fix the checkpoint repository tests that now fail under the provenance
   contract.

   The existing mapper tests build mock ORM rows without `source_kind` and
   `source_share_artifact_id`, but the repository mapper now reads those fields
   into the domain model. Running:

   ```bash
   pdm run pytest tests/unit/infrastructure/repositories/test_classroom_planner_seating_export_checkpoints.py tests/unit/infrastructure/repositories/test_classroom_planner_grouping_export_checkpoints.py -q
   ```

   fails with three mapper validation errors:

   - `test_get_latest_for_roster_and_room_context_maps_model_to_domain`
   - `test_list_recent_for_roster_and_room_context_returns_newest_first_window`
   - `test_list_recent_for_roster_maps_models_to_domain_newest_first`

   Update those fixtures to include `source_kind="export_job"` and
   `source_share_artifact_id=None`, then add at least one explicit
   `share_artifact` mapper roundtrip assertion for seating and grouping so the
   new persisted provenance surface is actually covered.

### Suggestions

- Keep the public guest exclusion proof as a construction-level guarantee: the
  public guest creation helper should continue to avoid accepting or resolving a
  checkpoint recorder dependency.

### Passing Checks Observed

- `pdm run pytest tests/unit/application/apps/classroom_planner/test_authenticated_shares.py tests/unit/application/apps/classroom_planner/test_seating_export_job_completion.py tests/unit/application/apps/classroom_planner/test_grouping_export_job_completion.py -q`
- `pdm run pytest tests/unit/application/apps/classroom_planner/test_public_shares.py -q`
- `pdm run pytest tests/unit/web/apps/classroom_planner/test_smart_seating_api.py tests/unit/web/apps/classroom_planner/test_smart_grouping_api.py -q`
- `pdm run pytest 'tests/integration/test_migration_revision_coverage_idempotent.py::test_uncovered_migration_revision_is_idempotent[f2a7c9d4e6b8]' --override-ini addopts='' -q`
- `pdm run typecheck`

## Changes Made

1. Recorded the retained review outcome for `PR-0307` as `changes_requested`.
2. Resolved the retained mapper blocker by updating the seating/grouping
   checkpoint repository fixtures with explicit export provenance and adding
   share-artifact mapper assertions for both repositories.
3. Updated the review verdict to `approved` after rerunning the failing
   repository command successfully.

### Second Pass

**Reviewer:** `codex`
**Date:** `2026-05-08`
**Verdict:** `approved`

The retained blocker is resolved. The repository mapper proof now covers both
`export_job` and `share_artifact` provenance shapes for seating and grouping.

```bash
pdm run pytest tests/unit/infrastructure/repositories/test_classroom_planner_seating_export_checkpoints.py tests/unit/infrastructure/repositories/test_classroom_planner_grouping_export_checkpoints.py -q
```

Result: 7 passed.
