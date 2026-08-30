---
type: task
id: TASK-SKRIPT-39-02-03
title: Repair partial DigiExam answer-key enrichment and prove the real integrated
  vertical
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-08-30'
status: ready
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
- A real DigiExam source with both enrichable unkeyed items and an unsupported asset-bearing
  unkeyed item creates and completes an enrichment job for the eligible items while
  preserving the unsupported item for manual review instead of failing the whole conversion.
- The touched Exam Converter test slice contains no trivial fake-shape happy-path
  tests or negative archaeology tests, and real-DXE PostgreSQL-backed integration
  coverage exercises the production job, enrichment, worker, review projection, and
  artifact chain with only the external provider boundary isolated.
- The exact real DXE passes through the authenticated Docker development stack and
  browser review flow before integration or redeployment; focused or synthetic checks
  cannot satisfy this acceptance criterion.
story: ST-SKRIPT-39-02
backlog_document_profile: contract-derived
---

## Implementation Contract

Repair the incorrect all-or-nothing answer-key enrichment rule introduced by
the original Skriptoteket port. Enrichment is item-local: when a parsed
DigiExam contains at least one supported unkeyed machine-marked item, the
application queues the enrichment job and processes those supported items.
An unsupported asset-bearing item remains an explicit manual-review item and
does not prevent the rest of the exam from reaching review and export.

Keep PostgreSQL and the existing Unit of Work as the only job, enrichment,
lease, correction-session, and replay authority. Do not add a second queue,
filesystem state, compatibility path, or verification subsystem.

Audit the touched Exam Converter tests and remove tests or proof scripts that
only exercise fabricated UI shapes, assert trivial event emission, or assert
that removed symbols remain absent. Replace the missing confidence with one
real-input integration path and one real development-runtime browser path.
There is no additional review stage for this repair; implementation continues
until the agreed integrated vertical is green.

## Contract Inputs

- The production failure for
  `1776888013-ak7-lag-och-ratt.dxe`, which parses successfully but currently
  enters the synchronous failure path because one unkeyed item contains an
  embedded asset.
- The genuine unchanged source file at
  `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/inputs/examples/digiexam-dxe-fixtures/2026-05-12-onedrive-pure-dxe/1776888013-ak7-lag-och-ratt.dxe`.
- The previous Sir Convert behavior at `76983339`, where candidate generation
  was item-local and unsupported items remained manual follow-ups.
- The published Skriptoteket answer-key, worker, lease, correction-session,
  review-projection, and artifact contracts already owned by
  `ST-SKRIPT-39-02` and the cutover tasks.
- The approved Exam Converter review UI. This task repairs its input/runtime
  path and test quality; it does not redesign the UI.

## Core Vertical And Performance

The walking skeleton is:

`real DXE upload -> authenticated application endpoint -> PostgreSQL conversion
and enrichment rows -> execution worker -> configured remote provider ->
machine-proposed overlay plus preserved manual item -> review projection ->
teacher review actions -> generated artifacts`.

The automated integration test uses the genuine unchanged DXE and real
PostgreSQL/UoW repositories. It may isolate only the external provider network
behind the production provider protocol; every Skriptoteket transition listed
above must execute through production code. The live development proof uses
the authenticated Docker/Gateway stack, the actual configured API-model
provider, and browser interactions. Neither a fabricated request body nor a
Vite-only fixture page qualifies.

The planner remains a linear pass over the already parsed exam. The repair adds
no extra network round trip, polling layer, or persistence authority.

## Validation

- A real-DXE PostgreSQL-backed integration test proves admission, durable job
  and enrichment state, worker completion, partial overlay creation, preserved
  manual review state, review projection, and artifact availability.
- An authenticated Playwright run through the Docker development stack uploads
  the exact genuine DXE, observes durable processing, reaches the review UI,
  exercises the agreed review controls and progression, and confirms the
  artifacts become available. This is the end-to-end release gate.
- Audit the touched backend, frontend, and script tests. Remove low-value
  fabricated happy paths, trivial event-only assertions, duplicate synthetic
  proof pages, and negative archaeology assertions.
- Run affected lint, typing, frontend build, and focused behavioral coverage as
  supporting checks. Report them as supporting checks, never as the integrated
  proof.
- Record the exact live development result in `handoff.md`, then run
  `pdm run handoff-validate`, `pdm run docs-validate`, and `git diff --check`.

## Stop Conditions

- The authenticated Docker/Gateway development lane or actual remote provider
  cannot complete the unchanged real-DXE path: do not integrate, publish, or
  redeploy; repair the vertical or report the concrete blocker.
- The repair would require a second job-state authority, a filesystem queue, a
  legacy Sir processing dependency, or a compatibility fallback: stop and
  return to the accepted PostgreSQL/UoW boundary.
- The exact source cannot remain unchanged or its unsupported item cannot be
  preserved for manual review: stop rather than weakening the input or hiding
  the unresolved item.
- Production DXE submission is not authorized. Production acceptance remains
  with the user.

## Decided Contract Terms

| ID | Decided contract term |
| --- | --------------------- |
| D1 | Enrichment is item-local; one unsupported asset-bearing item does not block eligible items. |
| D2 | PostgreSQL/UoW remains the single state authority. |
| D3 | Low-value fake-shape, trivial happy-path, and negative-archaeology tests in the touched slice are removed rather than counted as proof. |
| D4 | The unchanged real DXE and real application transitions are mandatory test inputs. |
| D5 | The authenticated Docker development-stack browser path with the configured API provider is the end-to-end gate. |
| D6 | Focused and synthetic checks cannot establish integration or release readiness. |
| D7 | No additional review stage is added; repair continues until the integrated vertical is green. |
| D8 | Production DXE acceptance remains user-owned. |
