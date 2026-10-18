---
type: task
id: TASK-SKRIPT-41-02-02
title: Guests open, edit and export exams in the workspace without login
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-18'
status: ready
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
- At the guest converter's URL a guest starts from QTI or blank, edits, and exports QTI, print PDF, DOCX and the fallback Exam.net PDF without login, with the exam kept in the browser
- Guest imports and exports pass per-caller and pooled hourly limits in the database
- After sign-in the draft is saved to Mina filer and opens there
story: ST-SKRIPT-41-02
backlog_document_profile: contract-derived
---

## Implementation Contract

Open the exam workspace to guests at the guest converter's URL under ST-SKRIPT-41-02 P1-P5. Guest edits, undo and autosave live in the browser; imports and exports go to public stateless routes that take the document in the request and return the result, under database-backed per-caller and pooled hourly limits that replace the in-memory per-IP throttle for these routes. AI-triggering controls and DigiExam/Word import show a sign-in prompt instead of calling. Sign-in moves the draft into Mina filer.

Non-goals: public AI; changing the signed-in workspace beyond what the shared editor needs.

## Contract Inputs

- ST-SKRIPT-41-02 P1-P5; TASK-SKRIPT-41-02-01 (QTI parse); User grilling 2026-10-18 in the Mac orchestration session (retained root 01a14ee0-903e-7423-b969-30e3661e9006); explorer maps of the DigiExam lines and paid AI call sites the same day.
- `infrastructure/security/public_helper_request_throttle.py`, `web/request_metadata.py`, `web/api/v1/public_apps*.py`, the exam workspace views and stores, `exam_workspace_exports.py`.

## Core Vertical And Performance

The vertical is the shared workspace editor running on a browser document store for guests and the server store for signed-in teachers, behind one store interface; the public export and QTI routes are stateless and limited by one database-backed limiter (per caller and pooled per hour). Performance: export rendering cost bounds the pooled limit.

## Validation

- Focused tests: public export and parse routes with no auth, refused past per-caller and pooled limits regardless of user-agent, surviving a restart; no AI client reachable from any public route (extend the REP-0044 guard); sign-in handoff saves the draft once.
- Vitest for the guest store, sign-in prompts and handoff. Lint and typecheck for touched domains.
- Staging walk per ST-SKRIPT-41-02.

## Stop Conditions

Stop and report if the shared editor cannot run on a browser store without forking the workspace, or before merge with the proposed limit defaults for the user to confirm.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| G1  | ST-SKRIPT-41-02 P1-P5 apply as written. |
| G2  | The guest and signed-in workspace are one editor behind one document store interface; no forked workspace. |
| G3  | Limit numbers are settings; the lead proposes defaults and the user confirms them before merge. |
| G4  | Sign-in prompts read "Logga in för att importera från DigiExam eller Word." and "Logga in för att få AI-hjälp." |

## Resume Here (clean break 2026-10-18)

- Branch `codex/task-skript-41-02-02-remote`. The head is the commit that adds this note. Merged origin/main 188a2139 (REP-0044 and 39-06-10) at b454590b. The lead has proven every unit below with focused tests. There has been no independent review yet.
- Retained root: `/home/paunchygent/apps/skriptoteket/.orchestration/context/sessions/01a14f56-345b-7f38-ab9e-a441663b90d8`. Design and facts: `evidence/planning/synthesis-41-02-02.md`. Junior work orders: `evidence/planning/work-orders/` (each one is `_preamble.md` plus `<unit>.body.md`). Child results: `evidence/results/<id>.json`.
- Done and committed:
  - B1 and B1m: database limiter, table `public_request_windows`, migration a1c2e3f4b5d6 (P4).
  - B2a: public guest exports and export checklist (P3).
  - B2b and B2c: public stateless blank, part, group/empty/move, change-type, misspellings and course routes.
  - B3: signed-in POST `/exam-workspace/guest-drafts`. The `exam_guest_draft_handoffs` ledger (migration c8e4f2a6d9b3) makes sure each draft is saved once per user (P5).
  - F1a-c: one injected exam workspace store (G2).
  - F2a-c: the guest browser store in IndexedDB (P2).
  - G1: `tests/unit/web/test_ai_route_gate_public_routes.py` proves that no public or guest route reaches an AI client. The REP-0044 modules are unchanged apart from one `NON_AI_JOB_REPOSITORY_USERS` entry for the guest-draft handler.
- Next units, in order (orders are written):
  1. `f3a-guest-host`: guest host, entry swap, sign-in prompt, copy constants, limit notice. One run completed it and then reverted its edits on the lead's stop order. Rerun it fresh; its design is recorded in result `22a5493f-c8bd-41d9-a6a3-0bb9bb47be31.json`.
  2. `f3b-guest-gating`: its addendum covers main's `canUseAi` gate.
  3. `f4-guest-handoff` (P5, client side of B3).
  4. The guest QTI start, after the parent confirms that 41-02-01 is on main.
  5. Then lint, typecheck, frontend checks, docs-validate and one domain-wide suite.
- Open findings:
  - `tests/integration/test_exam_workspace_parts_vertical.py:145` fails mypy because B2a (5372014a) gave the export handler a `renderer` argument. The lead must repair this.
  - B3 does not refuse a title that is already in use in Mina filer, so a handoff can create a second exam with the same title. The signed-in save path has no name uniqueness either. Returned to the parent as a product decision.
  - The caller key is an unsalted sha256 of the client IP. Rows are pruned after about 2 hours.
  - `ExamConverterPublicView.vue` stays until 41-02-03.
- User gate (G3): the six `PUBLIC_GUEST_*_PER_HOUR` settings hold provisional values in `config.py`. The user must confirm them before merge. Local render timing for an 8-question exam with no images: QTI 3 ms, PDF about 0.11 s, DOCX about 0.05 s. The probe is `evidence/probes/render_timing.py`; it has not been run on Hemma.
- No children are running.
- Remove the temporary worktree `/tmp/sk-4102-head` with `git worktree remove`.
