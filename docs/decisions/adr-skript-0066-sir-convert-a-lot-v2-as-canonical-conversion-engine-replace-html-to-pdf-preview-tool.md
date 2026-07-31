---
type: adr
id: ADR-SKRIPT-0066
title: Sir Convert-a-Lot v2 as canonical conversion engine (replace html-to-pdf-preview
  tool)
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: proposed
deciders:
- user-lead
retired_ids:
- ADR-0066
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
- Conversion Hub owns a **local job ledger** in Skriptoteket:
  - users submit conversion work to Skriptoteket,
  - Skriptoteket creates a local conversion-job record and maps it to the upstream Sir Convert job,
  - and status/download access is authorized through the local job identity rather than exposing
    raw upstream job ids as the primary product contract.
- Batch conversion is supported via the curated app UI (multiple inputs; per-file results).
- Preview is a UX concept only: a "preview" is implemented as a **normal v2 conversion job** that
  produces a normal PDF artifact (no separate preview engine/tool).
- Conversion Hub artifact delivery remains **proxied through Skriptoteket** after local
  authorization; it does not mint redirect/download URLs that expose Sir Convert as the primary
  artifact boundary.
- The legacy `html-to-pdf-preview` tool script is removed from the production strategy and will be
  retired from prod seeding (and later deleted when no longer needed by tests).
- Same-host transport between Skriptoteket and Sir Convert uses a **Unix domain socket when
  configured**, with `127.0.0.1` HTTP as the fallback for local development and non-socket
  deployments.
- Internal HTTPS between co-located Skriptoteket and Sir Convert services is not the preferred
  Conversion Hub transport shape.
- This ADR governs **Conversion Hub** and other general conversion surfaces. It does not require
  curated app-owned export artifacts such as Klassrumskartan PDFs to route through Sir Convert;
  that boundary is locked separately in `ADR-SKRIPT-0075`.

## Non-Decisions

No separate non-decisions is stated in the source.

## Consequences


- Skriptoteket gains a stable, bespoke conversion UI surface under `/apps/:appId` that can evolve
  without abusing the dynamic tool-script lane.
- Conversion security and sandboxing become the responsibility of Sir Convert-a-Lot v2 (as the
  conversion engine) rather than ad hoc script code.
- Skriptoteket must own a typed client + local job orchestration layer and the persistence required
  to enforce ownership, status, and artifact access without treating raw upstream job ids as the
  user-facing boundary.
- Same-host operational config must support a Unix-socket transport shape cleanly, with loopback
  HTTP remaining as the fallback transport rather than the primary trusted-network contract.
- Existing E2E and unit tests that depend on `/tools/html-to-pdf-preview/run` must migrate to the
  curated app surface.
