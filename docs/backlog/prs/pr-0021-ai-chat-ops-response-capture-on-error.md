---
type: pr
id: PR-0021
title: "AI editor: platform-only full model response capture on failures (ST-08-28)"
status: done
owners: "agents"
created: 2026-01-11
updated: 2026-01-11
stories:
  - "ST-08-28"
adrs:
  - "ADR-0051"
tags: ["backend", "editor", "ai", "observability", "security"]
acceptance_criteria:
  - "`LLM_CAPTURE_ON_ERROR_ENABLED` gates capture behavior; default is OFF and production-safe."
  - "On edit-ops generation failure, backend writes a capture file under `ARTIFACTS_ROOT/llm-captures/` keyed by correlation id."
  - "On preview failure, backend writes a capture file under `ARTIFACTS_ROOT/llm-captures/` keyed by correlation id."
  - "Normal logs remain metadata-only; no prompt/code/model output is logged."
  - "Capture retention is enforced by the artifacts prune workflow."
---

## Problem

When edit-ops or preview fails, metadata-only logs are often insufficient to diagnose upstream model behavior and parsing
edge cases. We need full response capture for platform debugging without exposing content to tool developers.

## Goal

Implement Option A: filesystem/SSH-retrievable captures written under `ARTIFACTS_ROOT`, gated by config and OFF by
default in production.

## Non-goals

- No tool-developer-facing “view capture” UI.
- No database storage or encryption-at-rest system (follow-up if needed).

## Implementation plan

1) Add a capture store implementation that writes JSON captures under `ARTIFACTS_ROOT/llm-captures/`.
2) Gate capture with `LLM_CAPTURE_ON_ERROR_ENABLED` (default OFF).
3) Capture on:
   - edit-ops generation failures (including parse/schema incompatibility)
   - preview failures (ok=false)
4) Extend artifact pruning to include capture directories.

## Test plan

- Targeted unit tests around capture gating + non-fatal write failures (if existing test patterns fit).
- Manual smoke:
  - Call edit-ops while disabled to force a failure outcome and verify a capture folder is created.
  - Tail logs and ensure no content is emitted.

## Rollback plan

Disable `LLM_CAPTURE_ON_ERROR_ENABLED` and prune captured folders. Removing the capture code does not require a DB
migration.
