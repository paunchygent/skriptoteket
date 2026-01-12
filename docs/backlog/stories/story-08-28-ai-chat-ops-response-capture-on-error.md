---
type: story
id: ST-08-28
title: "AI: platform-only full model response capture on edit-ops/preview failures (Option A)"
status: done
owners: "agents"
created: 2026-01-11
updated: 2026-01-11
epic: "EPIC-08"
acceptance_criteria:
  - "Given `LLM_CAPTURE_ON_ERROR_ENABLED=true`, when `POST /api/v1/editor/edit-ops` fails (timeout/over-budget/truncated/parse_failed/invalid_ops/error), then the backend writes a capture under `ARTIFACTS_ROOT/llm-captures/` keyed by the request correlation id."
  - "Given `LLM_CAPTURE_ON_ERROR_ENABLED=true`, when `POST /api/v1/editor/edit-ops/preview` returns ok=false, then the backend writes a capture under `ARTIFACTS_ROOT/llm-captures/` keyed by the request correlation id."
  - "Given captures are enabled, then no raw prompt/code/model output content is emitted to normal structured logs; logs remain metadata-only."
  - "Given capture writing fails (missing dir, permissions, disk full), then the request still succeeds/fails normally and the backend logs a metadata-only `llm_capture_write_failed` event."
  - "Given captures exist, then a platform developer can retrieve them via filesystem/SSH; no HTTP endpoint exposes capture contents."
  - "Given capture directories are older than retention, when the artifacts prune job runs, then capture directories are removed."
ui_impact: "No"
data_impact: "Yes (stores sensitive debug captures on disk when enabled)"
---

## Context

We need a production-configurable (OFF by default) “god mode” debug mechanism to diagnose model behavior when edit-ops
generation or preview fails, without leaking prompt/code/output content into normal observability logs or tool developer
surfaces.

## Notes

- Option A: captures are stored in artifact storage and retrieved via server filesystem access (SSH).
- Capture id is the request correlation id (stable, already propagated).

## Implementation (done)

- Config: `LLM_CAPTURE_ON_ERROR_ENABLED` (default OFF).
- Capture location: `${ARTIFACTS_ROOT}/llm-captures/<kind>/<correlation_id>/capture.json`.
- Pruning: `pdm run python -m skriptoteket.cli prune-artifacts` (includes `llm-captures/`).
