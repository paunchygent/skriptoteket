---
type: task
id: TASK-SKRIPT-41-01-04
title: Skriptoteket serves a thousand concurrent AI calls with bounded fan-out and
  a try-again message
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
- Web runs several processes and workers run jobs concurrently with bounded fan-out inside a job
- HTTP and database pools are sized for 1,000 concurrent AI calls, streaming included
- A door capacity 429 or Retry-After reaches the SPA as a try-again answer
- A load proof against the door's mock mode holds 1,000 concurrent AI calls with no paid call
story: ST-SKRIPT-41-01
backlog_document_profile: contract-derived
---

## Implementation Contract

Give Skriptoteket the capacity of ST-SKRIPT-41-01 B7. Today web is one uvicorn process (`pyproject.toml` `serve`), the worker handles one job at a time (`workers/execution_queue_worker.py:98-166`, `RUNNER_MAX_CONCURRENCY=1`), DOCX jobs fan out without limit (`exam_workspace_docx_pipeline.py:225-240`, `item_type_labeling.py:141`), the shared httpx client uses default limits (100 connections) and the database pool is 5 plus 10 per process. Use the existing patterns (the `FOR UPDATE SKIP LOCKED` job claim, the shared client, the error mapping in `web/error_mapping.py`).

Reuse before writing (user 2026-10-18): HuleEdu's `libs/huleedu_service_libs/src/huleedu_service_libs/http_client/httpx_policy.py` (bounded httpx limits with contextual errors) is the pattern for the door client's limits; the lessons of TASK-HULE-23-05-05 apply here too: connection limits and concurrency limits are separate and both sized, retries on a door 429 back off with its `Retry-After` instead of adding pressure, and the load proof counts active calls, not configured ones. The load proof drives the door's D8 mock (ST-HULE-14-03) and may reuse HuleEdu's pressure runner probes.

Non-goals: door internals (TASK-HULE-14-03-01).

## Contract Inputs

- ST-SKRIPT-41-01 B7; ST-HULE-14-03 D6; User grilling 2026-10-18 in the Mac orchestration session (retained root 01a14ee0-903e-7423-b969-30e3661e9006), with explorer maps of Skriptoteket's paid AI call sites and capacity and of the HuleEdu LLM provider service the same day.
- `Dockerfile:174`, `pyproject.toml:448`, `compose.prod.yaml:120-175`, `di/llm.py:98-102`, `di/infrastructure/db.py:33-37`, `config.py:104-110,218,262`, `web/error_mapping.py:20-24`.

## Core Vertical And Performance

Performance is the subject: 1,000 concurrent AI calls across web requests (editor streaming) and worker jobs (answer keys, DOCX), mostly small. The bound inside a job keeps one large DOCX from taking the whole capacity.

Units: 1. web processes and pool settings; 2. concurrent job execution with a per-job fan-out bound; 3. try-again mapping to the SPA; 4. mock-mode load proof.

## Validation

- Focused tests: concurrent job claims never run one job twice; the fan-out bound holds; a door capacity 429 becomes the try-again answer.
- Load proof: 1,000 concurrent AI calls against the door's mock mode complete or receive the try-again answer, with no paid call.
- Lint and typecheck for touched domains.

## Stop Conditions

Stop and report if the Hemma host cannot hold the process and pool sizes, with the measured limit.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| K1  | ST-SKRIPT-41-01 B7 applies as written; process, worker and pool numbers are settings. |

## Progress

2026-10-22, implementation lead: units 1-4 are built on `codex/task-skript-41-01-04` (`58e8d6c1a`, `686903632`). Review and the staging walk have not happened yet. Evidence is in the lead's retained root `01a16352-bf56-71d9-a928-c0ca618d1203`, under `evidence/`.

- Unit 1, processes and pools: uvicorn reads `WEB_CONCURRENCY` (production 4, staging 2). The engine pool comes from `DATABASE_POOL_SIZE`, `DATABASE_MAX_OVERFLOW` and `DATABASE_POOL_TIMEOUT_SECONDS`. Production keeps web 4 x (4 + 4) plus worker 4 + 4 = 40 connections, because shared-postgres allows 100 for every Hemma app. The door client has its own httpx pool (`LLM_DOOR_MAX_CONNECTIONS`) and a separate in-flight bound (`LLM_DOOR_MAX_IN_FLIGHT`, production web 240 and worker 64 per process). A wait longer than `LLM_DOOR_SLOT_WAIT_SECONDS` for a slot, or an httpx pool timeout, ends as try-again.
- Unit 2, worker and fan-out: the worker runs `LLM_WORKER_JOB_CONCURRENCY` (8) answer-key and DOCX jobs as slots, each with its own worker id, and tool runs stay one at a time. Each AI action (`AiDoorCaller`) has at most `LLM_JOB_MAX_IN_FLIGHT` (8) door calls in flight. The bound is enforced in the door client, so the uncapped second-pass gather is bounded too.
- Unit 3, try-again: the client retries a door capacity 429 after its `Retry-After`, capped at `LLM_DOOR_RETRY_AFTER_MAX_SECONDS`, up to `LLM_DOOR_CAPACITY_RETRIES` times, with no slot held while it waits. After that it raises `AiDoorBusy`. Synchronous routes answer 429 `AI_TRY_AGAIN` with a `Retry-After` header. Worker jobs fail with the try-again note "AI-hjälpen har många förfrågningar just nu. Försök igen om en stund." The SPA shows the note and leaves the AI controls enabled.
- Unit 4, load proof: with 1,120 calls from 5 processes against the door's mock mode, the door served a peak of 1,000 active calls and every call completed. With the door window at 300, 747 calls completed and 373 got the try-again answer. No call reached OpenAI in either run. The first run failed on the door's default hypercorn backlog of 100 (1,434 listen overflows, 146 `ReadError`). That fix belongs to the HuleEdu door; the later runs used `--backlog 2048` on the disposable mock door.
- Proof: `pdm run lint` and `pdm run typecheck` pass. 2,476 focused unit tests pass. 18 Docker integration tests pass: AI routes hold no DB connection during the provider call, concurrent claims run each job once, and DOCX background replay. Five frontend specs (49 tests) pass in Vitest.
- Residual: the in-memory public-helper throttle (anonymous classroom-planner helper routes, 5 requests per 60 s per key) becomes per process, so the effective limit is 5 x `WEB_CONCURRENCY`. The orchestrator accepted this, 2026-10-22.
