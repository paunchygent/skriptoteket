---
type: task
id: TASK-SKRIPT-REP-0071
title: Cleanup of explicit Any, cast and type-ignore comments and the shared Pyrefly explicit-any producer
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-11-22'
status: done
closeout_review:
  record: inline
  status: approved
  reviewer: ruthless-reviewer
  decided_at: '2026-11-22T13:48:29+00:00'
  approval_protocol: agent-overseer:approved-review-closeout
  approval_evidence: TASK-SKRIPT-REP-0071#closeout
task_kind: repository
lead_role: implementation-specialist
acceptance_criteria:
  - 'Given the repository''s tracked Python files, when `pyrefly check --error explicit-any --only explicit-any` runs over them with Pyrefly 1.4.1, then it reports no error, and rg finds no `cast(` call or `# type: ignore` comment outside an exception recorded in this task.'
  - 'Given the released repository-governance runtime with explicit-any as an error, when the settings sync has run and `pdm run typecheck` runs, then a Pyrefly producer checks the typecheck-includes and passes, and a disposable module with `def f(x: Any) -> None` makes it fail.'
backlog_document_profile: contract-derived
---

## Implementation Contract

1. Cleanup (before the runtime release). Every explicit `Any`, `cast(` and
   `# type: ignore` in tracked Python files is rewritten to fit
   skill-repository's typing reference
   (`skills/agent-roles/references/coding-principles-typing.md`) or removed:
   parsed JSON goes through the repository's single recursive `JsonValue`
   alias and is narrowed at the boundary; test doubles and fixtures take the
   real class, a Protocol or `object` (TASK-SKILL-REP-0591 DCT-09); inherited
   third-party signatures and boundary refusal tests carry a coded
   single-line `# pyrefly: ignore[...]` with a reason comment. The
   repository's existing `pdm run typecheck` keeps passing.
2. After the release that turns explicit-any on: run
   `repository-governance-bindings sync --project-file pyproject.toml`, set
   `typecheck-includes` under `[tool.repository-governance.tooling]` to the
   repository's Python source and test roots, and add a typecheck producer
   `pyrefly check --config pyproject.toml --only explicit-any`
   (TASK-SKILL-REP-0591 DCT-08). Other type checkers stay unchanged.

## Contract Inputs

Survey of 22 Nov 2026 for skriptoteket: typecheck runs mypy and vue-tsc;
Pyrefly 1.4.1 installed; 249 explicit-any errors, 56 `cast(`, 28
`# type: ignore`.

## Core Vertical And Performance

`pdm run typecheck` passes with a Pyrefly producer checking the repository's
typecheck-includes with explicit-any as an error; a new explicit `Any`
fails the gate while mypy and vue-tsc keep covering their existing scope.

## Validation

- A disposable module with `def f(x: Any) -> None` fails
  `pdm run typecheck` with an `explicit-any` error after the settings sync
  and producer change.
- `pdm run check` passes on the changed set.

## Stop Conditions

- A site that fits no exception in the typing reference goes to the
  TASK-SKILL-REP-0591 orchestrator for Olof's decision; no junior adds an
  ignore for it.
- Unit 2 waits for the runtime release of TASK-SKILL-REP-0591.

## Decided Contract Terms

| ID     | Decided contract term                                                                                                                                                                                                               |
| ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| DCT-01 | Every permitted ignore is a coded single-line Pyrefly ignore with a reason comment; bare `# type: ignore` and `cast` stay forbidden. (TASK-SKILL-REP-0591)                                                                          |
| DCT-02 | A governed repository whose typecheck does not run Pyrefly adds a typecheck producer `pyrefly check --config pyproject.toml --only explicit-any`; its other type checkers stay unchanged (Olof, 22 Nov 2026). (TASK-SKILL-REP-0591) |
| DCT-03 | A test double or fixture typed `Any` is rewritten to the real class, a Protocol, or `object`; the typing reference gains no test-double exception (Olof, 22 Nov 2026). (TASK-SKILL-REP-0591)                                        |

## Closeout

The task removed every explicit `Any`, `cast(` call and bare `# type: ignore` from the repository's tracked Python files; at review, Pyrefly 1.4.1 reported zero `explicit-any` errors across all 2,479 tracked files and the tracked-file scan found no `cast(` or `# type: ignore`. After the runtime release it synced the shared Pyrefly settings, declared `typecheck-includes` as `src`, `tests`, `scripts`, `migrations` and `runner`, and kept a `typecheck-python` composite in which mypy keeps its existing cohort targets while Pyrefly checks the whole `typecheck-includes` with `explicit-any` as an error.

- `evidence/results/26b1792e-d350-4431-b47c-cf66990e3767.json` — unit 1 review of `4517ef148..870525d6b`: `changes_requested`, findings F1–F9. Closed by repair commits `8f0b774f0` (F4, F5, F6), `053b3cf28` (F1, F8, F9), `8d53bdad9` (F2, F7, F9), `fc545f9f9` (F3, F8) and `f621bd14d` (F9).
- `evidence/rereview-task-skript-rep-0071-f621bd14d.md` — rereview of head `f621bd14d` with repair commits `053b3cf28`, `8d53bdad9` and `fc545f9f9`: `approved` for F1, F2 and F3; the record did not decide F4–F9.
- `evidence/review-task-skript-rep-0071-post-release-493a73009.md` — post-release review of `493a73009`: `changes_requested`, finding F1 (the composite appended mypy's positional cohort targets to Pyrefly, so `scripts`, `migrations`, `runner` and the rest of `tests` were not checked). Closed by repair commit `f0594693c`, which put `{args}` on mypy only.
- `evidence/rereview-task-skript-rep-0071-f1-f0594693c.md` — rereview of `f0594693c`, decided `2026-11-22T13:48:29+00:00`: `approved`; unscoped `pdm run typecheck` rejected an explicit-`Any` probe in each of the five configured roots and passed clean once the probes were removed.
