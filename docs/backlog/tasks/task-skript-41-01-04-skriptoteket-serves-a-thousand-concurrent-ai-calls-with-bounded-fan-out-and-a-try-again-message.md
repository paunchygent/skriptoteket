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
