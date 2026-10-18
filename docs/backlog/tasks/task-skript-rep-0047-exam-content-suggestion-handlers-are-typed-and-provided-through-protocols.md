---
type: task
id: TASK-SKRIPT-REP-0047
title: Exam content-suggestion handlers are typed and provided through protocols
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-18'
status: ready
closeout_review:
  record: inline
  status: not_started
task_kind: repository
acceptance_criteria:
  - The content-suggestion routes, the DI provider, the AI route-gate guard policy and the gate test double depend on RequestExamContentSuggestionsHandlerProtocol and GetExamContentSuggestionsHandlerProtocol; outside the DI provider and the handlers' own unit tests, no module names the concrete handler classes
  - The gate test double implements the protocol and does not subclass a concrete handler
  - The REP-0044 admin gate, the guard's expected paid-route snapshot and the guard's self-checks are unchanged and green
backlog_document_profile: contract-derived
---

## Implementation Contract

The exam-workspace content-suggestion routes in `web/api/v1/apps_conversion_hub_exam_workspace.py` resolve the concrete `RequestExamContentSuggestionsHandler` and `GetExamContentSuggestionsHandler` from Dishka. The DI provider returns the concrete types, the AI route-gate guard policy (`tests/unit/web/ai_route_gate_policy.py`) keys them by class, and the REP-0044 test double (`tests/unit/web/exam_workspace_ai_gate_test_support.py`) subclasses the concrete request handler and overrides its `__init__`. Every other exam-workspace handler is typed by a protocol in `protocols/exam_workspace.py` and provided under that protocol (Mac parent ruling 2026-10-18, a defect seen in the REP-0044 repair).

This task adds the two handler protocols, provides the handlers under them, and moves every consumer to the protocols (P1-P6). No behaviour changes.

Non-goals: changing the handlers' behaviour, the REP-0044 gate, the worker lane (`ProcessExamContentSuggestionsHandler`), or the course-content route.

## Contract Inputs

- Mac parent ruling 2026-10-18 (assignment `96f0456b` in root `01a14f6a`).
- `src/skriptoteket/application/curated_apps/handlers/exam_workspace_content_tags.py`, `src/skriptoteket/di/exam_workspace.py`, `src/skriptoteket/protocols/exam_workspace.py`.
- REP-0044 guard: `tests/unit/web/ai_route_gate_policy.py`, `ai_route_gate_discovery.py`, `test_ai_route_gate_coverage.py`; gate API test `test_apps_exam_workspace_ai_gate_api.py` and its support module.

## Core Vertical And Performance

The vertical is one HTTP request to the content-suggestion routes, which resolve a handler by its protocol through Dishka. No performance concern.

## Root Cause (R1)

`ContentSuggestionsResponse` is defined in the handler module `handlers/exam_workspace_content_tags.py`. That module imports `protocols/exam_workspace.py` (for `GetExamWorkspaceDocumentHandlerProtocol`), so a protocol in `protocols/exam_workspace.py` cannot name the response without an import cycle. The other exam-workspace handlers keep their response models in application model modules (`application/curated_apps/exam_workspace.py`, `exam_workspace_misspellings.py`), which the protocols layer imports. With no importable response type, the content-suggestion handlers never got protocols, and the routes, DI provider, guard and test double bound to the concrete classes.

## Validation

- `pdm run test tests/unit/web/test_apps_exam_workspace_ai_gate_api.py`
- `pdm run test tests/unit/web/test_ai_route_gate_coverage.py`
- `pdm run test tests/unit/application/curated_apps/test_exam_content_suggestion_jobs.py`
- `pdm run lint` and `pdm run typecheck`
- One domain-wide run of `tests/unit/web` and `tests/unit/application/curated_apps` at the end.

## Stop Conditions

Stop and report to the parent if the guard's expected paid-route snapshot would have to change, if a guard self-check fails after the switch, or if the change needs a behaviour change.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                                                                                                                                                                                              |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| P1  | `ContentSuggestionsResponse` moves to a new application model module `src/skriptoteket/application/curated_apps/exam_workspace_content_suggestions.py`; the old definition in the handler module is deleted and every importer imports from the new module. No re-export from the handler module.                                                                                                  |
| P2  | `protocols/exam_workspace.py` gains `RequestExamContentSuggestionsHandlerProtocol` (`handle(*, actor, lineage_id) -> ContentSuggestionsResponse`) and `GetExamContentSuggestionsHandlerProtocol` (`handle(*, actor, lineage_id, job_id) -> ContentSuggestionsResponse`). The concrete handlers stay plain classes that satisfy the protocols structurally, like the other exam-workspace handlers. |
| P3  | The DI providers `request_content_suggestions` and `get_content_suggestions` return the protocol types.                                                                                                                                                                                                                                                                                            |
| P4  | Both routes resolve `FromDishka[...Protocol]`. The request route keeps `require_app_ai_api`; the status route keeps `require_app_user_api`.                                                                                                                                                                                                                                                        |
| P5  | The guard policy keys `JOB_ENQUEUERS` by `RequestExamContentSuggestionsHandlerProtocol` and `NON_AI_JOB_REPOSITORY_USERS` by `GetExamContentSuggestionsHandlerProtocol`. `EXPECTED_AI_ROUTES` is unchanged.                                                                                                                                                                                        |
| P6  | `ContentSuggestionsDouble` subclasses `RecordingDouble` and `RequestExamContentSuggestionsHandlerProtocol` only, like the sibling doubles, and the test provider returns the protocol type.                                                                                                                                                                                                        |
| P7  | The status handler is included under the same rule (Boy Scout: the same defect on the sibling route in the same files).                                                                                                                                                                                                                                                                            |

## Resume Here (2026-10-18 clean break)

- Branch `codex/task-skript-rep-0047-remote`, implementation commit `67d1ecdc`; all work committed.
- Done: P1-P7 in one junior unit. Focused proof green: `test_apps_exam_workspace_ai_gate_api.py`, `test_ai_route_gate_coverage.py`, `test_exam_content_suggestion_jobs.py`; `pdm run lint` and `pdm run typecheck` green. `EXPECTED_AI_ROUTES` unchanged.
- Next: confirm the one domain-wide run (`pdm run pytest -q tests/unit/web tests/unit/application/curated_apps`; log at `evidence/commands/domain-suite-rep-0047.log` in the retained root). If the run did not finish, rerun it. Then independent review, routed by the parent.
- Open findings: none. Blockers and user gates: none.
- Retained root: `/home/paunchygent/apps/skriptoteket/.orchestration/context/sessions/01a14f6a-f57b-7b24-9672-320bf5884dbc`.
- Running children: none. Junior `4d4b1ee9` completed; result at `evidence/results/4d4b1ee9-73bd-4643-9af5-fe3df849123d.json` in the retained root.
