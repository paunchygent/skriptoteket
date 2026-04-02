---
type: review
id: REV-EPIC-31
title: "Review: Flappy Birds as a bespoke curated app"
status: pending
owners: "agents"
created: 2026-04-01
reviewer: "lead-developer"
epic: EPIC-31
adrs:
  - ADR-0023
  - ADR-0027
  - ADR-0073
stories: []
---

## TL;DR

This review proposes a new implementation epic to ship `games.flappy_birds`
as the next competitive curated app inside Skriptoteket. The plan preserves
Flappy Birds gameplay semantics, rebuilds shell/runtime integration on the
accepted bespoke curated-app pattern, and keeps leaderboard support lightweight
and fun.

## Problem Statement

We now have a clear product decision for Flappy Birds, but not yet a canonical
implementation epic that places the work in the reviewed backlog. Without that
epic, the repo lacks an approved planning home for the app-specific route,
runtime, shell, and simplified leaderboard scope.

## Proposed Solution

Create a new proposed epic dedicated to `games.flappy_birds` as a first-class
bespoke curated app. Reuse the accepted competitive-games boundary
(browser-owned simulation, backend-owned competition state), preserve donor
gameplay semantics rather than the donor DOM shell, and explicitly narrow the
leaderboard model to a light leisure feature with simple server-owned
submission and leaderboard state.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/adr/adr-0023-curated-apps-registry-and-execution.md` | Curated-app platform boundary | 5 min |
| `docs/adr/adr-0027-full-vue-vite-spa.md` | SPA host and route ownership | 4 min |
| `docs/adr/adr-0073-competitive-games-and-official-high-scores.md` | Existing competitive-games baseline and where the new epic intentionally simplifies scope | 8 min |
| `docs/reference/ref-competitive-games-cross-cutting-programme.md` | Family sequencing and shared-workstream framing | 5 min |
| `docs/reference/ref-curated-app-flunk-out-frenzy-architecture-and-foundational-code.md` | First-consumer analogue and code-map precedent | 6 min |
| `docs/backlog/epics/epic-25-competitive-games-and-flunk-out-frenzy.md` | Existing family implementation precedent | 4 min |
| `docs/backlog/epics/epic-31-flappy-birds-curated-app.md` | Proposed Flappy Birds implementation scope | 6 min |

**Total estimated time:** ~38 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Flappy Birds ships as `games.flappy_birds` from day one | Keeps the product aligned with the curated-app model instead of treating the app as an experiment | [ ] |
| Preserve gameplay semantics, not the donor shell | Avoids fighting the bespoke route/bootstrap/runtime boundaries already established in Skriptoteket | [ ] |
| Reuse the competitive-game shell pattern but keep the runtime library choice app-specific | Supports shared app-host discipline without forcing pinball-specific simulation choices onto Flappy Birds | [ ] |
| Leaderboards stay lightweight and fun | Matches the stated product value of casual teacher competition and reduces overengineering risk | [ ] |

## Review Checklist

- [ ] Epic scope is appropriate for a second competitive curated game
- [ ] The proposed boundaries still align with the accepted curated-app and SPA architecture
- [ ] The simplified leaderboard stance is explicit enough to guide future story scaffolding
- [ ] Risks are identified with reasonable mitigations
- [ ] The epic is ready for story decomposition after approval

---

## Review Feedback

**Reviewer:** @lead-developer
**Date:** YYYY-MM-DD
**Verdict:** pending

### Required Changes

- Pending review.

### Suggestions (Optional)

- Pending review.

### Decision Approvals

- [ ] Flappy Birds ships as `games.flappy_birds` from day one
- [ ] Preserve gameplay semantics, not the donor shell
- [ ] Reuse the competitive-game shell pattern with app-specific runtime choices
- [ ] Leaderboards stay lightweight and fun

---

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `EPIC-31` | Added the proposed Flappy Birds implementation epic with bespoke-app-first scope and lightweight leaderboard direction |
| 2 | `REV-EPIC-31` | Added the required review surface before implementation or story scaffolding begins |
