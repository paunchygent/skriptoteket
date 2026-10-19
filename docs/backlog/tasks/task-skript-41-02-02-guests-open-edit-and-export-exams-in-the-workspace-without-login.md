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

| ID  | Decided contract term                                                                                           |
| --- | --------------------------------------------------------------------------------------------------------------- |
| G1  | ST-SKRIPT-41-02 P1-P5 apply as written.                                                                         |
| G2  | The guest and signed-in workspace are one editor behind one document store interface; no forked workspace.      |
| G3  | Limit numbers are settings; the lead proposes defaults and the user confirms them before merge.                 |
| G4  | Sign-in prompts read "Logga in för att importera från DigiExam eller Word." and "Logga in för att få AI-hjälp." |

## Resume Here (lead 2, 2026-10-19)

- Branch `codex/task-skript-41-02-02-remote`. origin/main d4d267cc (REP-0047) merged at d7f99dee; G1 and the AI route-gate guard pass after the merge. No independent review yet.
- Retained root: `/home/paunchygent/apps/skriptoteket/.orchestration/context/sessions/01a14f56-345b-7f38-ab9e-a441663b90d8`. Design: `evidence/planning/synthesis-41-02-02.md`. Lead-2 work orders: `evidence/planning/work-orders-lead2/`. Child results: `evidence/results/<id>.json`.
- Done and committed: B1, B1m, B2a-c, B3, F1a-c, F2a-c, G1 (see the earlier units in git history), and:
  - R1 (2dbac7e6): the parts-vertical test builds the export handler with its `renderer`; mypy clean.
  - F3a (8f598329): the public converter URL mounts `ExamWorkspaceGuestHost.vue` on the guest store, with the browser-only notice, the limit sign-in prompt and a redirect to the signed-in workspace for a signed-in visitor.
  - F4 + R2 (c8e61d9e): `ExamWorkspaceTeacherHost.vue` hands a stored guest draft to Mina filer once on mount; an unreadable browser store hands off nothing and the workspace still renders.
  - F3b (9de1523d): blank start, G4 sign-in prompts on every AI control and the DigiExam/Word import, teacher-only controls hidden in guest mode.
- R3: each guest control is gated once, in its component; the shared AI mode lives in `useExamWorkspaceAiMode`.
- R4 (8781cfa5): the three public exam workspace route modules drop `from __future__ import annotations` (OpenAPI-safe typing).
- R5 (aeaaa707): exam workspace component specs get the store and sign-in injections from one typed `examWorkspaceProvidersPlugin`.
- Domain suite 2026-10-19 at bff9843c: backend 1 failed (fixed by R4), 3064 passed; frontend 51 failed in 9 specs (fixed by R5). Reruns of the failed and touched files pass (backend 82, frontend 320).
- Independent review da90f12c at 87dbf8ee: changes_requested (`evidence/reviews/da90f12c-9823-4ac1-85e4-0c833b656ee6.md` in the retained root). Repaired as fresh junior units (lead 2, 2026-10-19), each with a test that failed before the fix: F1 one uvicorn trusted-proxy chain (no wildcard; `FORWARDED_ALLOW_IPS` from `TRUSTED_PROXY_CIDRS`; the app reads the resolved peer only); F2+F3 conditional `replaceIf`/`clearIf` browser writes and a snapshot-keyed handoff; F4 sign-in departure settles the autosave first; F7 the handoff runs inside the store's compensated transaction; F8 one typed export-blockers base model and no Any in the route tests; F9 files split under 500 lines. The repaired high findings go back to da90f12c for rereview.
- Deploy steps (F1) for Hemma:
  1. Read the nginx-proxy address: `docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' nginx-proxy`.
  2. Set `TRUSTED_PROXY_CIDRS=<nginx-proxy IP>/32` in the deployment `.env`. Compose passes it to uvicorn as `FORWARDED_ALLOW_IPS`.
  3. Rebuild and restart the web service. Without step 2, uvicorn trusts only loopback, every guest shares the proxy address as one caller key, and the app logs the proxy-trust warning.
- Lint: `pdm run lint` fails only on `compose.prod.yaml`, whose YAML line-length errors predate this task: 39 on origin/main dcad0217 and 32 at this branch head after the semantic-free fixes. The orchestrator routes that debt as a separate repair; this task adds no yamllint config.
- Blocked: F5 (the guest QTI start) waits for TASK-SKRIPT-41-02-01 on main. F6 (a print PDF separate from the Exam.net fallback PDF) waits for TASK-SKRIPT-40-04-07, which owns the student print PDF. When each one lands, the lead merges main and integrates it here.
- Domain suite 2026-10-19 at f0bc8d14: backend 3092 passed, 0 failed; frontend 439 files, 3016 passed.
- U7: the app logs `public_guest_limiter_proxy_untrusted` once per process at guest admission when uvicorn did not trust the proxy hop, and `public_guest_limiter_proxy_trust_loopback_only` at production startup when FORWARDED_ALLOW_IPS is loopback-only. Neither log line contains an IP.
- Rereview da90f12c cleared F1-F3 at 31f7d966 and kept F4 open: text typed during the departure write was lost. R9 fix: `useExamWorkspaceHistory.settleForDeparture` runs the settle flush inside the `replaceCopy` editing lock and resolves true only when the flush stored and no edit is pending. Departure resolves false while an undo, redo or server command holds the copy. Before the fix, the new departure spec failed (2 of 4 tests); after it, 48 focused tests pass and fe-type-check passes.
- Next: full Vitest on the R9 commit after the orchestrator assigns a slot, then F4 goes back to review da90f12c.
- Open findings:
  - B3 does not refuse a title that is already used in Mina filer, so a handoff can create a second exam with the same title. This is a product decision for the user.
  - The caller key is an unsalted sha256 of the client IP; rows are pruned after about 2 hours.
  - `ExamConverterPublicView.vue` stays until 41-02-03.
- User gate (G3): the six `PUBLIC_GUEST_*_PER_HOUR` settings in `config.py` hold provisional values (import 10/200, export 30/300, edit 600/6000 per caller/pool per hour). The user must confirm them before merge. Local render timing for an 8-question exam: QTI 3 ms, PDF about 0.11 s, DOCX about 0.05 s; it has not been measured on Hemma.
