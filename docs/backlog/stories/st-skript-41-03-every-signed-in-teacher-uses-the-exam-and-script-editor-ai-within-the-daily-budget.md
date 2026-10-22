---
type: story
id: ST-SKRIPT-41-03
title: Every signed-in teacher uses the exam and script-editor AI within the daily
  budget
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-22'
status: ready
closeout_review:
  record: inline
  status: not_started
epic: EPIC-SKRIPT-41
acceptance_criteria:
- A signed-in teacher who is not an admin uses the AI features on staging within the
  daily budget
links:
  decisions: []
backlog_document_profile: contract-derived
---

## Slice Contract

Paid AI is admin-only today: one shared check (TASK-SKRIPT-REP-0044) lets only admins and superusers start exam AI (Word and PDF import, answer keys, question typing, content tags) and script-editor AI, and shows everyone else a note. This story lifts that gate for every signed-in teacher once ST-SKRIPT-41-01 routes every paid call through the HuleEdu LLM provider door, and sets the door's daily shares for Skriptoteket so that the door's pools are the only budget.

Anyone can register a HuleEdu account with a verified email of any domain, and the account reaches Skriptoteket as a user. This story adds no school-domain check; a later check is added only if misuse shows up. The pools cap the daily cost, so misuse can at most use up a day's pool for other teachers.

Non-goals: a remaining-today indicator; a school-domain allowlist for sign-up or for AI (ST-SKRIPT-02-06); an AI grant role.

## Contract Inputs

- User grilling 2026-10-22 in the Mac orchestration session (retained root 01a160e1-08de-706a-8728-3510b9547579, ledger G1-G9), with an explorer map of HuleEdu self-registration, email verification and Skriptoteket's default role the same day.
- ST-SKRIPT-41-01 B3-B5 (models, limit notes, exempt users) and EPIC-SKRIPT-41 E1-E4.
- TASK-SKRIPT-REP-0044 (the admin-only check `require_app_ai_api` in `web/auth/huleedu_app_projection.py`, used by the exam-workspace AI routes and the editor chat and edit-ops routes).
- HuleEdu `services/llm_provider_service/config_routing.py` (Skriptoteket's door policy: today 10% small share, 1% full share, USD 1 ceiling).

## Tasks

| Task                 | Delivers                                                                                                                                                                                                  | Depends on        |
| -------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------- |
| TASK-SKRIPT-41-03-01 | Walking skeleton: Skriptoteket's door policy at 20% small and 10% full share with no USD ceiling, the admin-only AI check and its note deleted, and a non-admin teacher using exam and script-editor AI on staging | ST-SKRIPT-41-01 done |
| TASK-SKRIPT-41-03-02 | Ghost text in the script editor appears within two seconds of the last keystroke | TASK-SKRIPT-41-03-01 |
| TASK-SKRIPT-41-03-03 | The script editor chat shows its answers as formatted text and code blocks | TASK-SKRIPT-41-03-01 |

## Verification

Focused tests for the door policy and for the AI routes accepting a non-admin user; a staging walk in which a signed-in teacher who is not an admin imports a Word exam with AI and a non-admin contributor uses script-editor completion and chat, both through the door.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| S1  | Every signed-in account that reaches Skriptoteket uses the AI of the screens its role opens: the exam AI for every user, the script-editor AI for everyone who opens the script editor. Signing in with a verified HuleEdu account is the only gate; there is no school-domain check (user decisions 2026-10-22). |
| S2  | The REP-0044 admin-only AI check and its admin-only note are deleted; no AI-specific role rule remains. |
| S3  | The door gives each Skriptoteket teacher 20% of the small-model pool (about 2M GPT-6 Luna tokens) and 10% of the full-model pool per UTC day. Exam AI and script-editor inline completion use the small share; script-editor chat, chat ops and edit ops use the full share (ST-SKRIPT-41-01 B3). |
| S4  | Skriptoteket's USD ceiling is removed from its door policy; the pools are the shared daily limit. The USD 1 overage cap per running job of ST-SKRIPT-41-01 B4 stays. |
| S5  | A limit shows the ST-SKRIPT-41-01 B4 notes only; teachers see no remaining-today indicator. |
| S6  | The work starts when ST-SKRIPT-41-01 is done, is proven by a staging walk as a non-admin teacher, and reaches production with the next production deploy. |
