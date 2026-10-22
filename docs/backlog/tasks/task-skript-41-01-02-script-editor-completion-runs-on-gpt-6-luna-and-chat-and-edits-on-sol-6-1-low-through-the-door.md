---
type: task
id: TASK-SKRIPT-41-01-02
title: Script-editor completion runs on GPT-6 Luna and chat and edits on Sol 6.1 low through the door
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-18'
status: done
closeout_review:
  record: inline
  status: approved
  reviewer: user
  decided_at: '2026-10-22'
  approval_protocol: agent-planning:user-closure-gate
  approval_evidence: 'One review in retained root 01a16352-c1aa-7200-beac-cdd64393cb32 (evidence/reviews/task-skript-41-01-02-365bbae9a-review.md): F1-F6 repaired on fail-first proof (ab453737f), no rereview per the user rule "Now it''s enough."; merged 1bab3a4f4; staging compose flag fix 400c88156. Mac staging walk at e1fbb32a4 passed ghost text, chat stream, cancel then new chat and profile, and found two defects, repaired on fail-first proof in 5f23f6501; Mac re-walk at 8569092ba passed both (Mac .artifacts/staging-walk-rewalk-8569092ba/walk-record.md). The door logs carry no per-call user id or model, so those rest on the transport test of 365bbae9a. The PR-0254 and TASK-0376 browser proofs keep no CSRF-refusal probe after S3 removed their consent PATCH; unit tests own CSRF refusal (orchestrator decision 2026-10-22). Deployed to production at 8569092ba by user decision 2026-10-22.'
task_kind: story
acceptance_criteria:
  - Script-editor inline completion calls GPT-6 Luna through the LLM provider door with the user's id, on the small-model pool; chat, chat ops and edit call OpenAI Sol 6.1 low through the door with the user's id, on the full-model pool
  - The local Devstral endpoint settings and the in-process failover to it are removed
story: ST-SKRIPT-41-01
backlog_document_profile: contract-derived
---

## Implementation Contract

The script editor's providers (`openai/chat_stream_provider.py`, `chat_ops_provider.py`, `inline_completion_provider.py`) point at a local Devstral endpoint (`host.docker.internal:8082`) that is down and are not metered. This task moves them through the door client of TASK-SKRIPT-41-01-03 with the user's id (B1, B3, B4). Inline completion runs on GPT-6 Luna and meets the small-model pool and its share. Chat, chat ops and edit run on OpenAI Sol 6.1 at low reasoning, streaming chat included, and meet the full-model pool and its share. A completion call sends up to 4k tokens and fires while the contributor types, so on Sol a 1% share would last only 2-3 completions (user decision 2026-10-22). The shares themselves are HuleEdu door policy, set in ST-SKRIPT-41-03. The REP-0044 admin gate stays.

## Contract Inputs

- ST-SKRIPT-41-01 B1, B3, B4; TASK-SKRIPT-41-01-03 (the door client); User grilling 2026-10-18 in the Mac orchestration session (retained root 01a14ee0-903e-7423-b969-30e3661e9006), with explorer maps of Skriptoteket's paid AI call sites and capacity and of the HuleEdu LLM provider service the same day.
- `config.py:248-323`, `di/llm.py`, `infrastructure/llm/chat_failover_router.py`, `infrastructure/llm/chat_inflight_guard.py`.

## Core Vertical And Performance

The vertical is one editor chat request streamed through the door and relayed to the SPA. Streaming holds a connection for the whole answer; TASK-SKRIPT-41-01-04 sizes pools for it.

## Validation

- Focused tests: inline completion sends through the door client on GPT-6 Luna, and chat, chat ops and edit on Sol 6.1 low, each with the user id; a limit 429 gives the B4 note; streaming relays to the end.
- Lint and typecheck for touched domains.

## Stop Conditions

Stop and report if Sol 6.1 cannot serve chat, chat ops or edit, or GPT-6 Luna cannot serve inline completion at a usable latency.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| S1  | Chat, chat ops and edit use OpenAI Sol 6.1 at low reasoning through the door; the local endpoint settings and the in-process chat failover are removed.                                                                                                                                                                                                                                                                                                                                                                                                                               |
| S2  | Inline completion uses GPT-6 Luna through the door on the small-model pool (user decision 2026-10-22).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| S3  | Under S1 the remote-provider consent goes too: both `allow_remote_fallback` columns (one migration), `AI_REMOTE_PROVIDERS_ENABLED`, `AI_DEFAULT_ALLOW_REMOTE_FALLBACK`, the local/external inline-completion preference, the profile AI-settings controls and `PATCH /profile/ai-settings`, `ai_policy` in `/profile/app-continuation`, and the remote-fallback notices. With no local endpoint and no failover the consent governs nothing, and exam AI never had it (orchestrator decision 2026-10-22).                                                                             |
| S4  | Chat, chat ops and edit default to the model id `gpt-6.1-sol`; the HuleEdu door prices it once its manifest has the entry, which the staging walk needs first (orchestrator decision 2026-10-22).                                                                                                                                                                                                                                                                                                                                                                                     |
| S5  | Editor AI meets a door limit as the exam AI does: HTTP 429 `AI_DAILY_LIMIT_REACHED` with the B4 note and `details.limit`, shown inline with no toast: for chat and edit in the composer's blocked-note slot, which disables send; for inline completion as a note on the editor canvas, with ghost text stopped. Chat refuses before its first SSE event. A refusal blocks only the allowance that was refused: chat and edit-ops share the full-model allowance, inline completion and exam AI the small-model one, and a `usd_ceiling` refusal blocks both (review F3, 2026-10-22). |
| S6  | Editor AI shares TASK-SKRIPT-41-01-04's door bounds: a chat stream holds its door slots until it closes and retries a capacity 429 on open, all editor calls use the door client's sized pool, and a busy door ends completion, chat and edit with HTTP 429 `AI_TRY_AGAIN` and the try-again note, chat before its first SSE event. One shared in-flight bound serves streams and other calls (41-01-04 review F5; orchestrator decision 2026-10-22).                                                                                                                                 |
