---
type: pr
id: PR-0307
title: "ST-26-06: Share-as-export Smart history provenance"
status: done
owners: "agents"
created: 2026-05-08
updated: 2026-05-11
stories:
  - "ST-26-06"
  - "ST-29-11"
tags: ["backend", "persistence", "exports", "sharing", "history", "klassrumskartan", "smart"]
dependencies:
  - "PR-0150"
  - "PR-0274"
  - "PR-0286"
  - "PR-0305"
  - "PR-0306"
acceptance_criteria:
  - "Given an authenticated teacher creates a seating share link from a persisted seating draft, when the share artifact is successfully created, then the seating arrangement is recorded as an eligible Smart-history checkpoint for the matching roster and normalized classroom context."
  - "Given an authenticated teacher creates a grouping share link from a persisted grouping draft, when the share artifact is successfully created, then the grouping partition is recorded as an eligible Smart-history checkpoint for the matching roster."
  - "Given an authenticated teacher repeats `Dela` without changing the normalized seating or grouping assignment, when the share succeeds again, then the checkpoint recorder deduplicates the unchanged history state."
  - "Given a public guest creates a share link, when the public helper persists the guest artifact, then no owner/account-backed Smart-history checkpoint is created."
  - "Given Smart `Historik` is enabled after a seating share link has been created for the selected classroom, when the teacher runs Smart seating, then the backend no longer returns the no-history blocker solely because the source was `Dela` instead of PDF/Excel export."
  - "Given checkpoint provenance is stored, when the source was PDF/Excel export or authenticated share, then the stored row identifies exactly one source kind without losing existing export-job provenance."
---

## Problem

Klassrumskartan treats `Dela länk` as an export action in the teacher-facing
`Dela och exportera` workflow, and `ST-26-06` says a shared page freezes the
plan at the moment of sharing. Smart history, however, is currently driven only
by export-backed checkpoint tables. Successful PDF/Excel exports create seating
or grouping checkpoints; authenticated share creation persists only a share
artifact.

Because `PR-0305` and `PR-0306` made authenticated `Historik` an opt-out
default, teachers can now reasonably share a seating chart and then immediately
hit the no-history Smart blocker even though they just created a durable shared
artifact.

## Goal

Make authenticated `Dela` count as an export-backed Smart-history source without
weakening the public guest boundary:

- share-created seating artifacts record seating checkpoints for Smart seating
  and grouping seating-continuity lookup
- share-created grouping artifacts record grouping checkpoints for Smart grouping
- PDF/Excel exports keep their existing provenance and dedupe semantics
- checkpoint rows record whether the source was an export job or an
  authenticated share artifact
- public guest shares remain outside account-backed Smart history

## Non-goals

- No frontend copy, toolbar, or toast changes.
- No change to Smart solver scoring weights.
- No public guest account-backed history.
- No import/discovery semantics for share artifacts.
- No change to immutable public share URL behavior, revoke behavior, or share
  page rendering.

## Implementation plan

1. Extend checkpoint provenance.
   - Add a source-kind field to seating and grouping checkpoint contracts.
   - Keep `source_export_job_id` for existing export provenance.
   - Add optional `source_share_artifact_id` for authenticated share provenance.
   - Enforce exactly one source id matching the source kind at the DB and domain
     boundaries.

2. Extract a checkpoint recorder.
   - Move dedupe and create logic out of export finalizers into a small
     application service shared by export finalizers and authenticated share
     handlers.
   - Keep repositories behind existing checkpoint protocols.

3. Wire authenticated share creation.
   - After successful owner-scoped share artifact creation, record the
     corresponding seating/grouping checkpoint from the same hydrated workspace.
   - Keep public guest share handlers unchanged for history.

4. Preserve export behavior.
   - Update PDF/XLSX finalizers to call the recorder with export-job provenance.
   - Do not create duplicate checkpoints for unchanged normalized assignments.

5. Lock with tests.
   - Focused application tests for seating/grouping share checkpoint creation
     and dedupe.
   - Regression test that public guest share creation does not call checkpoint
     persistence.
   - Migration/schema assertions for provenance columns, FKs, and check
     constraints.

## Test plan

- `pdm run pytest tests/unit/application/apps/classroom_planner/test_authenticated_shares.py tests/unit/application/apps/classroom_planner/test_seating_export_job_completion.py tests/unit/application/apps/classroom_planner/test_grouping_export_job_completion.py -q`
- `pdm run pytest tests/unit/application/apps/classroom_planner/test_public_shares.py -q`
- `pdm run pytest tests/unit/web/apps/classroom_planner/test_smart_seating_api.py tests/unit/web/apps/classroom_planner/test_smart_grouping_api.py -q`
- `pdm run pytest 'tests/integration/test_migration_revision_coverage_idempotent.py::test_uncovered_migration_revision_is_idempotent[<revision>]' --override-ini addopts='' -q`
- `pdm run alembic heads`
- `pdm run lint`
- `pdm run typecheck`
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Implementation Summary

Closed on 2026-05-08. Authenticated share creation now records explicit
`share_artifact` provenance for seating/grouping Smart-history checkpoints, while
public guest shares remain outside account-backed history.

The implementation landed as commit `913f76da Count Klassrumskartan shares as history exports`.

## Verification

- Retained review: `docs/backlog/reviews/review-pr-0307-share-as-export-smart-history-provenance.md`
  is approved.
- Repository evidence: commit `913f76da Count Klassrumskartan shares as history exports`.

## Rollback plan

Revert the provenance migration, checkpoint-recorder wiring, and share-handler
checkpoint calls together. Do not replace the checkpoint source boundary with a
frontend-only draft-history workaround; without a persisted checkpoint, Smart
history should remain honest even when Smart runs without history.
