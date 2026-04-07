---
type: adr
id: ADR-0080
title: "Klassrumskartan guest Smart parity and history-based Smart boundary"
status: accepted
owners: "agents"
deciders: ["user-lead"]
created: 2026-04-07
updated: 2026-04-07
links:
  [
    "PRD-group-seating-studio-v0.3",
    "ADR-0074",
    "ADR-0075",
    "ADR-0079",
    "EPIC-27",
    "EPIC-29",
    "EPIC-32",
    "ST-32-06",
  ]
---

## Context

`ADR-0079` already freezes the platform boundary for public curated apps:

- public access is opt-in and separate from authenticated authorization
- public lanes must use dedicated public SPA/API seams
- browser-owned guest state stays authoritative until a later authenticated
  upgrade
- guest export stays direct-download only

What remained blurry for Klassrumskartan specifically was not the platform
boundary, but the product boundary inside `Smart`.

`ST-32-06` and `PR-0223` established that guest mode should feel like the same
teacher workspace rather than a separate demo product. At the same time, the
older smart-assignment lane from `ADR-0074` includes both:

- solver-based Smart behavior
- history-based Smart behavior through `Use history`

Those are not the same kind of capability in guest mode. We therefore need one
small app-specific addendum that freezes exactly what guest parity means for
Klassrumskartan without reopening the broader platform decision in `ADR-0079`.

## Decision

### 1. Guest parity includes solver-based Smart runs

Klassrumskartan guest mode keeps solver-based Smart behavior as part of the
same teacher-facing product.

That means:

- guest mode includes roster-global smart-rule authoring
- guest mode includes solver-backed `Smart` runs for `Grupper` and
  `Sittplatser`
- accepted Smart results remain browser-owned guest state until a later
  authenticated upgrade

Solver-based guest Smart runs must use explicit public stateless helper seams
under the public namespace. They must not fall through to authenticated
owner-scoped `/api/v1/apps/...` routes.

### 2. `Regler` and the expandable Smart settings drawer are part of guest parity

Guest mode keeps the same Smart authoring shape as the authenticated planner at
the presentation level:

- `Regler` is a first-class guest workspace
- `Grupper` keeps an expandable Smart settings affordance
- `Sittplatser` keeps an expandable Smart settings affordance

The guest Smart settings drawer may expose:

- guest-valid Smart toggles
- guest-valid solver settings
- compact rule summaries
- links or affordances that route rule authoring into `Regler`

It must not become a separate guest-only editing model or a hidden fallback UI.

### 3. History-based Smart is account-only

History-based Smart behavior is not part of guest parity.

That means:

- `Use history` is account-only
- guest mode must not run solver behavior that depends on history-based Smart
  inputs
- guest mode must not read guest-local checkpoint descriptors or payloads as a
  Smart-history lane

If a Smart control would imply history-based behavior in guest mode, the guest
surface should omit that control or block it honestly rather than pretending
guest history parity exists.

### 4. Guest checkpoints are not a guest Smart-history seam

Guest direct-download export may still capture browser-owned checkpoint payloads
or descriptors when that is useful for later authenticated upgrade/import
continuity.

Those checkpoint payloads do not create a guest-side Smart-history contract.

Their role is limited to:

- browser-owned continuity or bookkeeping where explicitly approved
- later authenticated upgrade/import

They are not an allowed input to guest `Use history` behavior because guest
`Use history` does not exist.

### 5. Authenticated history and recovery remain separate

The following remain authenticated-only for Klassrumskartan:

- history-based Smart runs and `Use history`
- authenticated draft history drawers and recovery lanes
- server-owned run history or job recovery
- Vault / My Files recovery surfaces
- cross-device continuity

This addendum narrows the meaning of guest Smart parity. It does not weaken the
hard public/authenticated boundary from `ADR-0079`.

## Consequences

- `ST-32-06` follow-on work should treat guest Smart parity and authenticated
  history boundaries as separate implementation slices.
- Guest parity now explicitly includes:
  - `Regler`
  - expandable Smart settings drawers in `Grupper` and `Sittplatser`
  - solver-based Smart grouping and seating through public helper seams
- Guest parity now explicitly excludes:
  - `Use history`
  - history-based Smart runs
  - authenticated history/recovery/job/Vault surfaces
- Public Klassrumskartan verification must distinguish:
  - solver-based Smart parity that should work in guest mode
  - history-based Smart behavior that should remain account-only
