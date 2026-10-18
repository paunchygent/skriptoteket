---
type: task
id: TASK-SKRIPT-41-01-02
title: The script editor's AI runs on Sol 6.1 low through the Sol pool
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
- Script-editor completion, chat, chat ops and edit call OpenAI Sol 6.1 low through the LLM provider door with the user's id, on the full-model pool
- The local Devstral endpoint settings and the in-process failover to it are removed
story: ST-SKRIPT-41-01
backlog_document_profile: contract-derived
---

## Implementation Contract

The script editor's providers (`openai/chat_stream_provider.py`, `chat_ops_provider.py`, `inline_completion_provider.py`) point at a local Devstral endpoint (`host.docker.internal:8082`) that is down and are not metered. This task moves them to OpenAI Sol 6.1 at low reasoning through the door client of TASK-SKRIPT-41-01-03, streaming chat included, so each call meets the full-model pool and the user's 1% share (B1, B3, B4). The REP-0044 admin gate stays.

## Contract Inputs

- ST-SKRIPT-41-01 B1, B3, B4; TASK-SKRIPT-41-01-03 (the door client); User grilling 2026-10-18 in the Mac orchestration session (retained root 01a14ee0-903e-7423-b969-30e3661e9006), with explorer maps of Skriptoteket's paid AI call sites and capacity and of the HuleEdu LLM provider service the same day.
- `config.py:248-323`, `di/llm.py`, `infrastructure/llm/chat_failover_router.py`, `infrastructure/llm/chat_inflight_guard.py`.

## Core Vertical And Performance

The vertical is one editor chat request streamed through the door and relayed to the SPA. Streaming holds a connection for the whole answer; TASK-SKRIPT-41-01-04 sizes pools for it.

## Validation

- Focused tests: each editor provider sends through the door client on Sol 6.1 low with the user id; a limit 429 gives the B4 note; streaming relays to the end.
- Lint and typecheck for touched domains.

## Stop Conditions

Stop and report if Sol 6.1 cannot serve a feature the editor needs (for example inline completion latency).

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| S1  | Completion, chat, chat ops and edit use OpenAI Sol 6.1 at low reasoning through the door; the local endpoint settings and the in-process chat failover are removed. |
