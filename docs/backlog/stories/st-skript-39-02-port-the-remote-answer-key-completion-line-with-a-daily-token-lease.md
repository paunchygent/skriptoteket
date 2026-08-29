---
type: story
id: ST-SKRIPT-39-02
title: Port the remote answer-key completion line with a daily token lease
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-08-29'
status: proposed
closeout_review:
  record: inline
  status: not_started
epic: EPIC-SKRIPT-39
acceptance_criteria:
  - An overlay-free DigiExam exam converted through the in-process lane receives machine-proposed answer keys from the GPT-5.6 Luna low-effort remote profile with GLM-5.3-flash failover, executed as an execution-worker job under a Postgres-backed non-refundable daily token lease that fail-closes with operator-visible status, with target-readiness behavior matching the Sir Convert lane and focused tests plus a live functional check recorded in handoff.md
links:
  decisions:
    - ADR-SKRIPT-0090
backlog_document_profile: contract-derived
---

## Slice Contract

Port the remote answer-key completion line from sir-convert-a-lot into the
Skriptoteket in-process exam-conversion lane, so an overlay-free `.dxe`
receives machine-proposed answer keys without leaving the product backend.

- Ported behavior derives from sir-convert-a-lot `main` at `76983339`
  (TASK-SIRCON-08-01-07 closed): the structured-LLM provider harness, the
  GPT-5.6 Luna low-reasoning-effort default profile, the GLM-5.3-flash
  OpenRouter failover-only backup, and the non-refundable daily token-lease
  semantics. Model identifiers are re-verified against current provider
  docs at implementation time.
- Skriptoteket-native design replaces sircon plumbing: the lease counter is
  a Postgres table owned through the Unit of Work (reserve before each
  call, no refunds, UTC-day partitioning as the structural midnight reset);
  enrichment executes as an execution-worker job per the existing
  curated-app job pattern, never inside the web request; provider adapters
  land behind protocol seams in infrastructure.
- Proposed keys enter the conversion as the existing teacher-overlay
  semantics: machine-proposed keys are a proposal surface, teacher review
  semantics are unchanged, and target-readiness gating for source-keyed,
  overlay-keyed, and unkeyed exams matches the Sir Convert lane.
- Data boundary unchanged from ADR-SIRCON-0014: teacher exam content and
  proposed answer keys only; no student data flows through this lane.
- Out of this slice: Word/PDF ingestion, QTI import, lane cutover, Sir
  Convert exam-lane or Qwen sidecar retirement, public-lane changes, and
  teacher-facing UI beyond the existing surfaces.

## Contract Inputs

- EPIC-SKRIPT-39 capability contract; ADR-SKRIPT-0090 boundary;
  sir-convert-a-lot ADR-SIRCON-0014 (accepted remote-first policy with the
  lease design) and TASK-SIRCON-08-01-07 decided terms D9-D14.
- Source modules in sir-convert-a-lot: `structured_llm_contracts.py`,
  `infrastructure/structured_llm_provider.py`, `structured_llm_config.py`,
  `structured_llm_hot_settings_runtime.py`,
  `infrastructure/answer_key_openai_model_profiles.py`, and the lease
  counter with its tests.
- Skriptoteket surfaces: the ST-SKRIPT-39-01 exam-conversion modules, the
  execution-worker pattern, migrations under `migrations/versions/`,
  config (`src/skriptoteket/config.py`), DI (`di/curated_apps.py`).
- Third-party API facts (OpenAI Responses/Chat API for Luna, OpenRouter
  chat completions) are fetched through the sanctioned docs tooling before
  code changes.

## Tasks

1. TASK-SKRIPT-39-02-01: the core vertical — one worker-job completion
   through the Luna profile with the Postgres lease reserved, live-proven.
2. TASK-SKRIPT-39-02-02: failover, exhaustion fail-close with
   operator-visible status, and the operator lease-balance surface.

## Verification

- Focused tests for provider profiles, lease reserve/no-refund/UTC-reset,
  worker-job lifecycle, and readiness parity pass under `pdm run` gates
  per `AGENTS.md`.
- Recorded live proofs: one Luna completion, one forced failover, one
  forced exhaustion with zero provider calls, each in `handoff.md`.
- Deterministic conversion continues unaffected in every failure proof.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                                      |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| S1  | The lease counter is Postgres-backed and owned through the Unit of Work; UTC-day partitioning is the reset; leases are never refunded; exhaustion fail-closes.                                                                             |
| S2  | Enrichment executes as an execution-worker job, never inside the web request.                                                                                                                                                              |
| S3  | The provider configuration carries over from sircon D9-D14: Luna low-effort default, GLM-5.3-flash failover-only from the same lease, a configurable 5,000,000 token/day sub-allocation, identifiers re-verified in current provider docs. |
| S4  | Teacher-review and target-readiness semantics are unchanged; machine keys are proposals under the existing overlay semantics.                                                                                                              |
| S5  | Cutover and every retirement stay outside this slice.                                                                                                                                                                                      |
