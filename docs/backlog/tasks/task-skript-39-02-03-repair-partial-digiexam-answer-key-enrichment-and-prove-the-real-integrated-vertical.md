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
status: done
closeout_review:
  record: inline
  status: approved
  reviewer: ruthless-reviewer
  decided_at: '2026-09-30'
  approval_protocol: agent-overseer:approved-review-closeout
  approval_evidence: Pi ruthless-reviewer closeout rereview approved e3ae9527..e877170d after the three closeout-review findings (vacuous replay spec cases, stale handoff, missing lint/typing/build/frontend evidence) were resolved; the real-DXE PostgreSQL integration test passed (1 passed), and the D5 real-browser click-through on Hemma staging skriptoteket-dev at e3ae9527 gave provider proposals for questions 1, 2, 4, 5 and 6, kept asset-bearing question 3 for manual review until a teacher key was saved, and produced downloadable Exam.net PDF and QTI zip with succeeded enrichment and conversion jobs. Records under Skriptoteket session 01a0f227-63b9-7435-8013-5f556eaf4905 evidence/ (d5-staging-click-through.md, reviews/TASK-SKRIPT-39-02-03/closeout-rereview-e877170d.md).
task_kind: story
acceptance_criteria:
- A real DigiExam source with both enrichable unkeyed items and an unsupported asset-bearing
  unkeyed item creates and completes an enrichment job for the eligible items while
  preserving the unsupported item for manual review instead of failing the whole conversion.
- The touched Exam Converter test slice contains no trivial fake-shape happy-path
  tests or negative archaeology tests, and real-DXE PostgreSQL-backed integration
  coverage exercises the production job, enrichment, worker, review projection, and
  artifact chain with only the external provider boundary isolated.
- After merge to main, the agent that owns the end-to-end proof uploads the exact real
  DXE on Hemma staging (skriptoteket-dev) and clicks through the review flow in a real
  browser it controls, with the configured API-model provider, before any production
  redeployment; focused or synthetic checks cannot satisfy this acceptance criterion.
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
real-input integration path and one real-browser click-through on Hemma staging.
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
above must execute through production code. The live proof runs on Hemma
staging, the rootless Docker Compose project `skriptoteket-dev` beside HuleEdu
staging, after merge to `main`, following
`docs/runbooks/run-skript-skriptoteket-staging-on-hemma-skriptoteket-staging-on-hemma.md`:
the agent that owns the end-to-end proof signs in through HuleEdu staging and
clicks through in a real browser it controls, with the actual configured
API-model provider. Neither a fabricated request body nor a Vite-only fixture
page qualifies.

The planner remains a linear pass over the already parsed exam. The repair adds
no extra network round trip, polling layer, or persistence authority.

## Validation

- A real-DXE PostgreSQL-backed integration test proves admission, durable job
  and enrichment state, worker completion, partial overlay creation, preserved
  manual review state, review projection, and artifact availability.
- After `main` is fast-forwarded on Hemma staging, the agent that owns the
  end-to-end proof, in a real browser it controls, uploads the exact genuine
  DXE, observes durable processing, reaches the review UI, exercises the
  agreed review controls and progression, and confirms the artifacts become
  available. This is the end-to-end release gate for production redeployment.
- Audit the touched backend, frontend, and script tests. Remove low-value
  fabricated happy paths, trivial event-only assertions, duplicate synthetic
  proof pages, and negative archaeology assertions.
- Run affected lint, typing, frontend build, and focused behavioral coverage as
  supporting checks. Report them as supporting checks, never as the integrated
  proof.
- Record the exact live development result in `handoff.md`, then run
  `pdm run handoff-validate`, `pdm run docs-validate`, and `git diff --check`.

## Stop Conditions

- The Hemma staging click-through or actual remote provider cannot complete
  the unchanged real-DXE path: do not redeploy production or close the task;
  fix forward on `main` or report the concrete blocker.
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
| D5 | The end-to-end gate is a real-browser click-through on Hemma's rootless Docker staging (`skriptoteket-dev`, beside HuleEdu staging) after merge to `main`, run by the agent that owns the end-to-end proof, with the configured API provider (user decision 2026-09-30; supersedes the local Docker development-stack Playwright gate). |
| D6 | Reviewed code may merge to `main` before the staging proof; focused and synthetic checks cannot prove the integrated vertical, close the task, or admit production redeployment, which require the D5 staging click-through. |
| D7 | No additional review stage is added; repair continues until the integrated vertical is green. |
| D8 | Production DXE acceptance remains user-owned. |
