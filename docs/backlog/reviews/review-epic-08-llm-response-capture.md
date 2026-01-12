---
type: review
id: REV-EPIC-08
title: "Review: Platform-only full model response capture (Option A)"
status: approved
owners: "agents"
created: 2026-01-11
updated: 2026-01-11
reviewer: "lead-developer"
epic: EPIC-08
adrs:
  - ADR-0051
stories:
  - ST-08-28
---

## TL;DR

We introduce a controlled, OFF-by-default debug capture mechanism that stores full upstream model responses on disk when
edit-ops generation or preview fails. Normal observability remains metadata-only; captures are retrievable only via
server filesystem access (SSH) and are intended for platform debugging during alpha.

## Problem Statement

Edit-ops failures (parse/invalid ops/truncation) and preview failures (patch apply mismatches) are hard to diagnose with
metadata-only logs. We need a platform-only mechanism to inspect the full response content without exposing it to tool
developers.

## Proposed Solution

- Option A: store captures under `ARTIFACTS_ROOT/llm-captures/` with TTL cleanup.
- Gate with `LLM_CAPTURE_ON_ERROR_ENABLED` (default OFF).
- Capture id is the request correlation id.

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Capture on error for all users when enabled | Data collection for alpha debugging | ✅ |
| Store captures on disk (artifact storage) | Simple, low-risk, no DB migration | ✅ |
| No API/UI retrieval | Prevent tool developer access; keep surface area minimal | ✅ |
| Correlation id is the capture id | Stable id already propagated to clients/logs | ✅ |

---

## Review Feedback

**Reviewer:** @user-lead
**Date:** 2026-01-11
**Verdict:** approved
