---
type: adr
id: ADR-SKRIPT-0077
title: Same-shell transition continuity for selector-driven workspaces
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: accepted
links:
  governing:
  - ADR-SKRIPT-0027
  - ADR-SKRIPT-0037
  - ADR-SKRIPT-0072
  - EPIC-SKRIPT-29
  - REF-SKRIPT-RESEARCH-frontend-transition-continuity-pattern-and-adoption-inventory-v1
  - REF-SKRIPT-PLAN-frontend-design-system-codemap-spa-planner-editor
  - REF-SKRIPT-GENERAL-klassrumskartan-workspace-ui-doctrine-2026-03-28
deciders:
- lead-developer
retired_ids:
- ADR-0077
---

## Context

### Source: Context

Skriptoteket now has several dense SPA surfaces where one persistent shell hosts multiple mutually
exclusive work areas:

- Klassrumskartan switches between `Översikt`, `Grupper`, `Sittplatser`, and `Regler`
- the code editor switches between `Kod`, `Metadata`, `Test`, and `Diff`
- smaller selector-driven shells exist in file pickers, vault panels, and local workspace subrails

The recent Klassrumskartan transition fix showed a clear product truth:

- a visible `fade out -> blank gap -> fade in` feels broken even when the total animation is short
- temporary fallback copy in a stable shell reads as a jump cut
- tearing down the old surface before the new one is ready is worse than a short delay

Teacher-facing workspaces should instead feel as if the current surface stays coherent until the
next one is genuinely ready to take over.

## Decision

### Source: Decision

### 1. Same-shell selector transitions must preserve continuity

When one route, modal shell, or persistent workspace frame hosts multiple mutually exclusive
surfaces, switching between them must preserve perceived continuity.

That means:

- keep the shared shell stable
- avoid blank intermediate states
- avoid title/status/context flashes from fallback state
- swap only when the incoming surface is ready enough to render coherently

This applies to segmented toggles, rail switches, local workspace selectors, and similar
same-context mode changes.

### 2. The canonical technique is a retained outgoing surface plus overlap crossfade

The required transition model is:

- keep the outgoing surface visible while the incoming surface prepares
- if needed, snapshot shell labels/status so they do not temporarily fall back
- mount the incoming surface into the same shell
- use a short opacity-only overlap crossfade
- allow the leaving surface to sit absolutely on top during its fade-out so the UI never goes blank

For the qualifying surfaces in this ADR, `mode="out-in"` is not an allowed default because it
creates or strongly risks a visible empty phase.

### 3. Transition staging is more important than raw speed

If the incoming surface needs async preparation, state derivation, or local shell hydration, the
current surface should remain in place until the transition can complete cleanly.

Allowed:

- a small transition label inside the existing shell
- a brief readiness delay before the crossfade begins
- temporarily hiding workspace-local secondary chrome while the shell stays stable

Not allowed:

- clearing the workspace to an empty frame while waiting
- dropping shared shell text to generic fallback copy such as a route default
- fading out first and hoping the next surface appears in time

### 4. This is a shared frontend standard, not a planner-only trick

The Klassrumskartan shell fix is the proving reference, but the rule is repo-wide for comparable
SPA surfaces.

The first adoption target after this planning package is the code editor workspace mode selector.
Additional targets are tracked in `REF-SKRIPT-RESEARCH-frontend-transition-continuity-pattern-and-adoption-inventory-v1`.

### 5. Scope boundaries stay explicit

This ADR governs:

- same-route workspace switches
- same-shell selector swaps
- subrail or local work-surface switches where the surrounding shell persists

This ADR does not automatically govern:

- route-to-route page transitions
- modal open/close animations
- generic popover/dropdown motion
- tiny inline content swaps where no shell continuity expectation exists

Those surfaces may still need animation guidance, but they are not justified by this continuity
rule alone.

## Non-Decisions

The source records no separate non-decision section; adjacent boundaries remain part of the selected decision.

## Consequences

### Source: Consequences

- Skriptoteket gets one canonical same-shell transition pattern instead of per-surface improvisation.
- New selector-driven workspace work must use the retained-surface overlap-crossfade model rather
  than `out-in` blanking.
- Existing qualifying surfaces must be inventoried and adopted in paced slices under `EPIC-30`.
- The planner shell transition fix becomes the baseline reference implementation for future work.
- Review approval is required before `ADR-SKRIPT-0077` moves from `proposed` to `accepted` and before the
  broader rollout begins.
