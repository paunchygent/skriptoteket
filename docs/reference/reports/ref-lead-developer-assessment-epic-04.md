---
type: reference
id: REF-lead-developer-assessment-epic-04
title: "Lead Developer Assessment: EPIC-04 Architect Review"
status: active
owners: "agents"
created: 2025-12-14
topic: "scripting"
---

# Lead Developer Assessment: EPIC-04 Architect Review

This document records the adopted/adapted/rejected recommendations from the EPIC-04 pre-implementation architecture
review and maps them to the docs-as-code sources of truth (stories, reference specs, ADRs).

## Foundation Fixes (ST-04-01)

### Hash semantics

- **Decision:** Adopt
- **Why:** `entrypoint` is part of the runnable identity; `content_hash` must reflect it to keep deduplication
  meaningful.
- **Docs:** `REF-dynamic-tool-scripts` and `ST-04-01` define `content_hash` as `sha256("{entrypoint}\\n{source_code}")`.

### Version number race

- **Decision:** Adapt (no silent retry)
- **Why:** The UX already relies on explicit conflict signaling (e.g. `expected_parent_version_id`). Auto-retrying can
  create surprising version forks; for v0.1 we prefer a clear `CONFLICT` requiring reload.
- **Docs:** Concurrency/backpressure is defined in ADR-0016; conflict behavior for editor flows is handled via contract +
  story-level conflict rules (see ST-04-03 technical notes).

### Repository update behavior

- **Decision:** Adopt (do not mask missing rows)
- **Why:** Returning the input object on a missing row can hide data-integrity issues and breaks the two-transaction run
  lifecycle (create RUNNING, later finish).
- **Docs:** Treated as an implementation invariant; control-plane failures surface as `DomainError(NOT_FOUND)` per error
  handling rules.

### Router `from __future__ import annotations`

- **Decision:** Adopt (remove from router modules)
- **Why:** Forbidden by rule `040-fastapi-blueprint` to prevent OpenAPI/ForwardRef issues.
- **Docs:** Rule `040-fastapi-blueprint` is the source of truth.

## ST-04-02: Docker Runner

### Protocol boundary

- **Decision:** Adopt
- **Why:** Protocol-first DI is required; it cleanly separates app handlers from Docker SDK specifics and keeps a seam
  for a future dedicated runner service.
- **Docs:** ST-04-02 scope explicitly requires a protocol boundary.

### Async strategy (thread offload + semaphore)

- **Decision:** Adopt
- **Why:** Docker SDK is synchronous; event-loop blocking is unacceptable.
- **Docs:** ADR-0016 defines the v0.1 global concurrency cap and backpressure behavior.

### Runner contract and compatibility

- **Decision:** Adopt
- **Docs:** ADR-0015 defines `result.json` schema, contract versioning, truncation expectations, and artifact path safety
  rules.

## ST-04-04: Governance

### Policy layer

- **Decision:** Adopt
- **Why:** Avoid duplicated authorization logic; combine coarse role guards with scripting-domain policy functions for
  ownership/state constraints.
- **Docs:** ST-04-04 explicitly requires `domain/scripting/policies.py`.

## Contracts & ADRs

### Request Changes endpoint

- **Decision:** Update the contract now (avoid spec/implementation drift)
- **Docs:** `REF-scripting-api-contracts` defines `POST /admin/tool-versions/{version_id}/request-changes`.

### New ADRs

- ADR-0015: Runner contract and compatibility
- ADR-0016: Execution concurrency and backpressure (v0.1: cap + reject, no queue)

## Implementation sequencing

Recommended order remains:

1. ST-04-02 (runner + artifacts + caps + DI + security profile)
2. ST-04-03 (admin editor + sandbox execution)
3. ST-04-04 (publish path at minimum so ACTIVE + `tools.active_version_id` is end-to-end)
4. ST-04-05 (user execution + my-runs)

