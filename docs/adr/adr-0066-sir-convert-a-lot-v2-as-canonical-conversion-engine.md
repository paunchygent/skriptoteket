---
type: adr
id: ADR-0066
title: "Sir Convert-a-Lot v2 as canonical conversion engine (replace html-to-pdf-preview tool)"
status: proposed
owners: "agents"
deciders: ["user-lead"]
created: 2026-03-01
---

## Context

Skriptoteket currently ships a production tool script `html-to-pdf-preview` (script bank entry
`src/skriptoteket/script_bank/bank.py`) which:

- duplicates conversion behavior (HTML -> PDF) that is now canonically provided by the dedicated
  Sir Convert-a-Lot service (v2),
- hardcodes an interactive 2-step "preview -> convert" flow with next_actions + state coupling,
- is coupled to runner/container implementation details (for example `/work/input/...` paths),
- makes downstream product strategy ambiguous (a tool script is not the long-term conversion hub).

We want a single, hardened, well-maintained conversion engine that downstream products treat as
canonical: Sir Convert-a-Lot v2.

## Decision

- Skriptoteket will implement a **first-class curated app** that provides a complete conversion
  UI and routes conversion execution to **Sir Convert-a-Lot v2**.
- Batch conversion is supported via the curated app UI (multiple inputs; per-file results).
- Preview is a UX concept only: a "preview" is implemented as a **normal v2 conversion job** that
  produces a normal PDF artifact (no separate preview engine/tool).
- The legacy `html-to-pdf-preview` tool script is removed from the production strategy and will be
  retired from prod seeding (and later deleted when no longer needed by tests).

## Consequences

- Skriptoteket gains a stable, bespoke conversion UI surface under `/apps/:appId` that can evolve
  without abusing the dynamic tool-script lane.
- Conversion security and sandboxing become the responsibility of Sir Convert-a-Lot v2 (as the
  conversion engine) rather than ad hoc script code.
- Skriptoteket must own a small, typed client + job orchestration layer (submit/poll/download) and
  operational config (base URL, auth, timeouts) for Sir Convert-a-Lot v2.
- Existing E2E and unit tests that depend on `/tools/html-to-pdf-preview/run` must migrate to the
  curated app surface.
