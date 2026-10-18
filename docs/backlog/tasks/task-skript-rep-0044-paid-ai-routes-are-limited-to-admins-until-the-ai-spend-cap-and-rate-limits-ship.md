---
type: task
id: TASK-SKRIPT-REP-0044
title: Paid AI routes are limited to admins until the AI spend cap and rate limits
  ship
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-18'
status: done
closeout_review:
  record: inline
  status: approved
  reviewer: ruthless-reviewer
  decided_at: '2026-10-18'
  approval_protocol: agent-overseer:approved-review-closeout
  approval_evidence: Independent ruthless-reviewer a262cc37 review changes_requested (F1 high, F2-F6 medium; root 01a14efe evidence/reviews/a262cc37-8bf9-4eb6-9137-4793d6507e86.md); F2-F6 repaired and admitted on focused proof; F1 re-review approved at 39e15eac (same dir, -rereview.md), ItemTypeLabelerProtocol accepted as a paid root; unit 6415 passed, Vitest and fe-build ok on Hemma; merged into main.
task_kind: repository
acceptance_criteria:
  - A signed-in user or contributor who calls any route that can start a paid LLM call gets 403 and no LLM call is made and no token lease is drawn
  - Admins and superusers keep every AI feature
  - Non-admin users see the AI-triggering controls disabled with one short Swedish note instead of an error
backlog_document_profile: contract-derived
---

## Implementation Contract

Production has every paid AI switch on (`LLM_ANSWER_KEY_ENABLED`, `LLM_COMPLETION_ENABLED`, `LLM_CHAT_ENABLED`, `LLM_CHAT_OPS_ENABLED`, `LLM_EDIT_ENABLED`). Any signed-in app user reaches answer-key suggestions, the AI DOCX conversion and the item-type labeler (`require_app_user_api`), and contributors reach script-editor completion, chat, chat ops and edit ops (`require_app_contributor_api`). The only cap is one global 5,000,000-token daily lease shared by the answer-key, DOCX-conversion and labeler calls; there is no per-user quota and no cost cap. The user pays these costs personally and ruled on 2026-10-18 that paid AI is limited to admins until the AI spend cap and rate limits ship (L1-L5).

This task puts every route that can start a paid LLM call behind one shared admin-or-superuser dependency at the web boundary and disables the matching controls for other users. No public route reaches an LLM today; that stays true (L4).

Non-goals: the AI spend cap, per-user quotas, pooled rate limits and the public workspace (planned separately); changing production switches; changing the LLM features themselves.

## Contract Inputs

- User ruling 2026-10-18 in the orchestration session: admin-only gate, AI stays on meanwhile.
- `src/skriptoteket/web/auth/huleedu_app_projection.py` (`require_app_admin_api` at :68), `web/auth/ai_preferences.py`.
- AI routes: `web/api/v1/editor/completions.py`, `chat.py`, `edit_ops.py`; `web/api/v1/apps_conversion_hub_exam_workspace_enrichment.py`; the DOCX-import and suggestion routes in `web/api/v1/apps_conversion_hub_exam_workspace*.py`.
- `src/skriptoteket/config.py:248-360` (switches and the shared daily lease).

## Core Vertical And Performance

The core vertical is one web-boundary dependency, `require_app_ai_api`, which requires admin or superuser and is the only role check on every AI route. The frontend reads the same rule from the signed-in user's role and disables the AI-triggering controls. No performance concern.

Units:

1. Backend: the shared dependency on every route that can start a paid LLM call, found by tracing each LLM client in `di/` back to its routes; a test that fails when a route reaches an LLM client without it.
2. Frontend: AI-triggering controls (answer-key suggestions, DOCX import in Öppna, script-editor completion, chat and edit ops) disabled for non-admins with the L3 note.

## Validation

- Focused backend tests: each AI route returns 403 for a user and a contributor with no LLM client call and no lease draw, and is reachable for an admin; the route-coverage guard.
- Vitest for the disabled controls and the note.
- Lint and typecheck for the touched backend and frontend domains.
- No staging walk; review and unit tests close it.

## Stop Conditions

Stop and report to the parent if an AI call starts from a path with no web route (a scheduled or queued job created without a gated route), or if gating DOCX import breaks a non-AI import (DigiExam, PDF).

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| L1  | Every route that can start a paid LLM call (answer-key suggestions, AI DOCX conversion and item labelling, script-editor completion, chat, chat ops and edit ops) requires the admin or superuser role; any other signed-in user gets 403 before any LLM call or lease draw. |
| L2  | One shared web-boundary dependency owns the rule and is the only AI role check; a test fails when a route reaching an LLM client lacks it. |
| L3  | Non-admin users see AI-triggering controls disabled with the inline note "AI-funktionerna är tillfälligt bara tillgängliga för administratörer."; DOCX import in Öppna counts as an AI control; DigiExam import stays open. |
| L4  | No unauthenticated route reaches an LLM; production switches stay unchanged. |
| L5  | The gate is temporary and carries no setting; the AI spend cap and rate-limit work replaces it. |
