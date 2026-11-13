---
type: task
id: TASK-SKRIPT-41-03-01
title: Every signed-in teacher uses exam and script-editor AI within the daily budget
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-22'
status: done
closeout_review:
  record: inline
  status: approved
  reviewer: user
  decided_at: '2026-10-22'
  approval_protocol: agent-planning:user-closure-gate
  approval_evidence: 'One review (D7) by the Pi ruthless-reviewer, changes_requested with one medium finding (edit-ops test module over 500 lines), repaired in 5d924da2d with no rereview; pre-push fixture leak repaired on fail-first proof in 78765d330 (retained root 01a163e6-36e6-7bdf-8c46-7fdd1ce94cf1, evidence/implementation/TASK-SKRIPT-41-03-01/closeout-evidence.md). Eval mode keeps its admin-only guard on the completion and edit-ops routes (orchestrator decision 2026-10-22; not an AI gate). HuleEdu door policy 4e5b010c2. Mac staging walk at 78765d330 as skriptoteket-proof-user and skriptoteket-proof-contributor passed checks 1-5 (Mac .artifacts/staging-walk-41-03-01-78765d330/walk-record.md).'
task_kind: story
acceptance_criteria:
  - A non-admin teacher uses exam and script-editor AI on staging; the admin-only check and its note are gone; the door policy gives Skriptoteket 20% small and 10% full share with no USD ceiling
story: ST-SKRIPT-41-03
backlog_document_profile: contract-derived
---

## Implementation Contract

Every signed-in teacher uses the AI of the screens their role opens, within the HuleEdu door's
daily pools (D1).

- Today `require_app_ai_api` (TASK-SKRIPT-REP-0044) admits only admins and superusers to exam AI
  and script-editor AI, and the SPA shows everyone else "AI-funktionerna är tillfälligt bara
  tillgängliga för administratörer."
- After this task the check, `useAiAccess` and the note are gone. Each AI route keeps only the
  sign-in and role check its screen already has (D2).
- The HuleEdu door gives each Skriptoteket teacher 20% of the small pool and 10% of the full pool
  per UTC day, with no USD ceiling. The USD 1 per-job overage cap stays (D3).
- A limit shows only the existing ST-SKRIPT-41-01 limit notes (D4).
- Non-goals: a remaining-today indicator, a school-domain check, an AI grant role, model changes.

## Contract Inputs

- ST-SKRIPT-41-03 S1-S6 (user decisions 2026-10-22).
- Backend: `src/skriptoteket/web/auth/huleedu_app_projection.py` `require_app_ai_api`, used by
  `web/api/v1/editor/completions.py`, `editor/chat.py`, `editor/edit_ops.py`,
  `apps_conversion_hub_exam_workspace.py` and `apps_conversion_hub_exam_workspace_enrichment.py`;
  tests in `tests/unit/web/test_ai_route_gate_*.py`, `ai_route_gate_policy.py` and
  `tests/integration/test_ai_routes_hold_no_connection.py`.
- Frontend: `frontend/apps/skriptoteket/src/composables/useAiAccess.ts` and its users in the
  editor panels and the exam-workspace import, enrichment and export-blocker code.
- HuleEdu: `services/llm_provider_service/config_routing.py` `OPENAI_DOOR_CALLERS` default
  (today 0.10, 0.01, USD 1.0). No HuleEdu `.env` overrides it.

## Core Vertical And Performance

The core vertical: a signed-in non-admin teacher imports a Word exam with AI on staging, and a
non-admin contributor uses script-editor completion and chat, all through the door. No
performance change.

Units, one junior each (D5):

1. HuleEdu door policy and its settings test, on HuleEdu main through a HuleEdu worktree.
2. Delete the backend check; the AI route tests prove a signed-in non-admin is served.
3. Delete the frontend check and note; the specs prove a non-admin sees the AI controls.

## Validation

- HuleEdu: the door settings test for the new `skriptoteket` policy.
- Skriptoteket: the AI route tests serving a signed-in non-admin, and the specs of the changed
  editor and exam-workspace components.
- A Mac staging walk as a non-admin teacher and a non-admin contributor (D6).

## Stop Conditions

- An AI route turns out to rely on the admin check for a guard other than AI access.
- The door policy needs an env override in HuleEdu staging or production.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                                                              |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| D1  | Every signed-in account uses the AI of the screens its role opens: exam AI for every user, script-editor AI for everyone who opens the script editor. No school-domain check.                                                                                      |
| D2  | `require_app_ai_api`, `useAiAccess` and `AI_ADMIN_ONLY_NOTE` are deleted with every use; each AI route keeps only its existing sign-in and role check. Admin-only refusal tests become tests that a signed-in non-admin is served.                                 |
| D3  | HuleEdu `OPENAI_DOOR_CALLERS` default for `skriptoteket`: small share 0.20, full share 0.10, no USD ceiling. The USD 1 per-job overage cap stays.                                                                                                                  |
| D4  | A limit shows only the ST-SKRIPT-41-01 B4 notes; no remaining-today indicator.                                                                                                                                                                                     |
| D5  | Three units, one junior each: the HuleEdu door policy, the backend check deletion, the frontend check and note deletion.                                                                                                                                           |
| D6  | Proof: focused tests for the door policy and for each AI route serving a signed-in non-admin; a Mac staging walk as a non-admin teacher (Word import with AI) and a non-admin contributor (completion and chat). Production follows at the next production deploy. |
| D7  | One independent review at most; repairs are admitted on focused fail-first proof, with no rereview.                                                                                                                                                                |

D1-D4 and D6 are the user's decisions (ST-SKRIPT-41-03 S1-S6, 2026-10-22;
agent-planning:user-closure-gate). D5 and D7 are orchestrator decisions under the user's
delegation. All come from the retained plan in root `01a163e6-36e6-7bdf-8c46-7fdd1ce94cf1`.
