---
type: story
id: ST-SKRIPT-08-17
title: Tabby edit suggestions + prompt A/B evaluation
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: ready
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
epic: EPIC-SKRIPT-08
acceptance_criteria:
- Given LLM edit suggestions are enabled and provider=tabby, when an edit is requested,
  then the backend calls Tabby /v1/chat/completions and returns enabled=true with
  a raw replacement suggestion
- Given provider=llama (default), when an edit is requested, then behavior matches
  the ST-08-16 llama-only path (no regression)
- Given a configured prompt variant, when an edit is requested, then the selected
  prompt template is applied and the variant id is logged (metadata only)
- Given the A/B evaluation script is run, when it completes, then it writes a summary
  report (success/empty/truncated/latency) to .artifacts/ai-edit-ab/ without logging
  prompt or code content
retired_ids:
- ST-08-17
---

## Context

### Source: Context

ST-08-16 validates llama-server-only edit suggestions first. This follow-up adds an optional Tabby chat provider and
introduces prompt A/B evaluation so we can choose the most reliable prompt shape before expanding UI features.

## Epic Contract Slice

### Source: Scope

### Backend

- Add a Tabby chat provider for edit suggestions (OpenAI-compatible /v1/chat/completions).
- Add a provider switch for edit suggestions (e.g., llama vs tabby) without affecting inline completions.
- Keep failure behavior unchanged: return enabled=false + empty suggestion on timeout/truncation/unavailable provider.

### Prompt Variants (A/B)

- Define prompt variants in code/config with stable IDs.
- Add a selector (config or request header) to choose the variant per request for testing.
- Log only metadata: provider, model, latency, variant id, selection length, status.

### Evaluation Harness

- Add a script that runs a fixed fixture set against each prompt variant and writes a summary report to
  `.artifacts/ai-edit-ab/` (no prompt/code content stored).

## ADR Coverage

No separate ADR coverage was recorded in the source snapshot.

## Contract Inputs

No separate contract inputs were recorded in the source snapshot.

## Live Verification Plan

### Source: Testing

- Unit: prompt-variant selector uses the expected template and logs variant id.
- Unit: provider routing selects Tabby vs llama based on config.
- Integration: mock Tabby chat response returns raw replacement suggestion.
- Script run: A/B evaluation script emits a summary report without prompt/code content.

## Non-Goals

### Source: Out of Scope

- UI changes for edit suggestions (handled in ST-08-16).
- Streaming responses or structured JSON outputs.
- Tabby repository indexing or prompt_template tuning.

## Notes

No additional notes were recorded in the source snapshot.

## Decision And Assumption Ledger

The source snapshot is the governing record for the decisions and assumptions stated above.

## Plan Document Review

No separate plan document review was recorded in the source snapshot.

## Story Closeout Review

No separate closeout review was recorded in the source snapshot.
