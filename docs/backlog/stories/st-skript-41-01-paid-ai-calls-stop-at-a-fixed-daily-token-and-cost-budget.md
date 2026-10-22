---
type: story
id: ST-SKRIPT-41-01
title: Paid AI calls stop at a fixed daily token and cost budget
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-18'
status: ready
closeout_review:
  record: inline
  status: not_started
epic: EPIC-SKRIPT-41
acceptance_criteria:
  - Every paid AI call goes through the LLM provider door, and a teacher past a limit sees the limit note with no provider call
  - Skriptoteket's token ledger, OpenAI key and GLM failover are gone; exam AI runs on GPT-6 Luna low and the script editor on Sol 6.1 low
  - 1,000 concurrent AI calls complete or get a try-again answer, proven against the door's mock mode
links:
  decisions: []
backlog_document_profile: contract-derived
---

## Slice Contract

Today Skriptoteket calls OpenAI directly from six exam call sites (answer keys, DOCX conversion, the item-type labeler, the content-tag classifier) and meters them in its own PostgreSQL token lease, which serializes every reservation under one advisory lock per UTC day; the OpenRouter GLM failover takes a second reservation, and the three script-editor providers point at a local endpoint that is down. Skriptoteket runs one web process and one worker that handles one job at a time, with unbounded fan-out inside DOCX jobs and no try-again path to the SPA.

This story moves every paid call onto the LLM provider door of ST-HULE-14-03 (B1-B6) and gives Skriptoteket the capacity for 1,000 concurrent calls (B7).

## Contract Inputs

- User grilling 2026-10-18 in the Mac orchestration session (retained root 01a14ee0-903e-7423-b969-30e3661e9006), with explorer maps of Skriptoteket's paid AI call sites and capacity and of the HuleEdu LLM provider service the same day.
- ST-HULE-14-03 D1-D7 (the door, its reservation and its 429 answers).
- `infrastructure/repositories/exam_answer_key_token_leases.py`, `infrastructure/llm/openai/*`, `infrastructure/llm/openrouter/*`, `di/llm.py`, `di/exam_answer_key.py`, `di/exam_workspace.py`, `di/docx_conversion.py`, `workers/execution_queue_worker.py`, `config.py:248-360`.

## Tasks

| Task                 | Delivers                                                                                                                               | Depends on           |
| -------------------- | -------------------------------------------------------------------------------------------------------------------------------------- | -------------------- |
| TASK-SKRIPT-41-01-03 | Walking skeleton: every exam AI call through the door, ledger, key and GLM failover removed, Luna 6 low, the limit note, staging proof | TASK-HULE-14-03-01   |
| TASK-SKRIPT-41-01-02 | Script-editor completion, chat, chat ops and edit on Sol 6.1 low through the door                                                      | TASK-SKRIPT-41-01-03 |
| TASK-SKRIPT-41-01-04 | Capacity for 1,000 concurrent calls and the try-again answer                                                                           | TASK-SKRIPT-41-01-03 |

## Verification

Focused tests per task; a staging walk in which a signed-in teacher's answer-key suggestion goes through the door and a teacher past their share sees the limit note; the mock-mode load proof of TASK-SKRIPT-41-01-04.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                                                                                                                                                               |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| B1  | Every paid AI call goes through the LLM provider door with Skriptoteket's internal key and the teacher's user id; the request bodies and schemas stay in Skriptoteket.                                                                                                                                                                                              |
| B2  | The PostgreSQL token lease, Skriptoteket's OpenAI key settings and the OpenRouter GLM failover are removed; no local budget check remains.                                                                                                                                                                                                                          |
| B3  | Exam AI (answer keys, DOCX conversion, labeling, content tags) runs on GPT-6 Luna at low reasoning; script-editor inline completion runs on GPT-6 Luna on the small-model pool, and chat, chat ops and edit run on OpenAI Sol 6.1 at low reasoning on the full-model pool (user decision 2026-10-22); the local Devstral endpoint settings are removed.                                                                                                                                                |
| B4  | A door 429 disables the AI control with an inline note and no toast. The note follows the 429's `error.limit`: `user_share` shows "Du har nått din gräns för AI-hjälp i dag. Försök igen i morgon."; `pool` or `usd_ceiling` shows "Appens AI-hjälp har nått dagens gräns. Försök igen i morgon." (user decision 2026-10-22, amending the single note). The limit stops only new AI jobs: a job that started before the limit runs on as paid overage, up to USD 1 of overage per job, and is stopped past that (user decision 2026-10-22).             |
| B5  | Admin and staging test users are sent as exempt users and meet only the pools; past an exhausted pool a call proceeds only with a paid-overage override that agent-run tooling (live scripts, staging proof runs) sets for one run after the user approves it in the conversation; no app user, admin included, has an override control (user decision 2026-10-22). |
| B6  | Deterministic fixture and corpus runs replay recordings and never call the door; a guard test fails when a paid call can reach OpenAI or the door outside the door client.                                                                                                                                                                                          |
| B7  | Skriptoteket serves 1,000 concurrent AI calls: several web processes, workers running jobs concurrently with bounded fan-out inside a job, HTTP and database pools sized for it, and a door 429 for capacity shown as a try-again answer.                                                                                                                           |
