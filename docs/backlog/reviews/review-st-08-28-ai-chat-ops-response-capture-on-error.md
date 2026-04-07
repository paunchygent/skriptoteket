---
type: review
id: REV-ST-08-28
title: "Review: ST-08-28 AI chat ops response capture on error"
status: approved
owners: "agents"
created: 2026-01-11
updated: 2026-04-06
reviewer: "lead-developer"
adrs:
  - ADR-0051
stories:
  - ST-08-28
links:
  - EPIC-08
---

## TL;DR

We introduce a controlled, OFF-by-default debug capture mechanism that stores full upstream model responses on disk when
edit-ops generation or preview fails. Normal observability remains metadata-only; captures are retrievable only via
server filesystem access (SSH) and are intended for platform debugging during alpha. This record was migrated from the
legacy `REV-EPIC-08` archive and now anchors the retained story review surface on `ST-08-28`.

## Problem Statement

Edit-ops failures (parse/invalid ops/truncation) and preview failures (patch apply mismatches) are hard to diagnose with
metadata-only logs. We need a platform-only mechanism to inspect the full response content without exposing it to tool
developers.

## Proposed Solution

- Option A: store captures under `ARTIFACTS_ROOT/llm-captures/` with TTL cleanup.
- Gate with `LLM_CAPTURE_ON_ERROR_ENABLED` (default OFF).
- Capture id is the request correlation id.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/stories/story-08-28-ai-chat-ops-response-capture-on-error.md` | Acceptance criteria + capture flow | 5 min |
| `docs/adr/adr-0051-chat-first-ai-editing.md` | Error capture and correlation contract | 5 min |
| `src/skriptoteket/infrastructure/llm/capture_store.py` | Capture storage implementation | 10 min |
| `src/skriptoteket/application/editor/edit_ops_preview_handler.py` | Error-path integration | 10 min |

**Total estimated time:** ~30 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Capture on error for all users when enabled | Data collection for alpha debugging | ✅ |
| Store captures on disk (artifact storage) | Simple, low-risk, no DB migration | ✅ |
| No API/UI retrieval | Prevent tool developer access; keep surface area minimal | ✅ |
| Correlation id is the capture id | Stable id already propagated to clients/logs | ✅ |

## Review Checklist

- [x] Capture on error is off by default and only enabled intentionally
- [x] Capture ids track the correlation id end-to-end
- [x] No API/UI retrieval path is exposed
- [x] Retention/TTL behavior is explicitly documented

---

## Review Feedback

**Reviewer:** @user-lead
**Date:** 2026-01-11
**Verdict:** approved

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | Review record | Migrated from the legacy epic-ledger `REV-EPIC-08` archive to the canonical `REV-ST-08-28` target-based story review record. |
