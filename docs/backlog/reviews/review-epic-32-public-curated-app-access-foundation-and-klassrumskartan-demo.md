---
type: review
id: REV-EPIC-32
title: "Review: Public curated-app access foundation and Klassrumskartan demo"
status: approved
owners: "agents"
created: 2026-04-03
updated: 2026-04-03
reviewer: "lead-developer"
epic: EPIC-32
adrs:
  - ADR-0079
stories:
  - ST-32-01
  - ST-32-02
  - ST-32-03
  - ST-32-04
  - ST-32-05
  - ST-32-06
---

## TL;DR

EPIC-32 proposes a reusable public curated-app access model for Skriptoteket so
Klassrumskartan can ship a non-auth demo without weakening the existing
authenticated curated-app host or owner-scoped APIs. The package introduces
explicit per-app public access profiles, parallel public/authenticated seams,
browser-owned guest-state rules, authenticated upgrade boundaries, and an
initial app matrix that keeps Conversion Hub authenticated-only while making
Klassrumskartan the first `public_browser_workspace_with_upgrade` consumer.

## Problem Statement

Today Skriptoteket's curated apps are effectively auth-gated even when
`min_role=user` because the SPA host route and app-specific APIs all depend on
authenticated session state. Klassrumskartan now needs a guest/demo lane, but
solving that as an optional-auth exception inside the existing `/apps/:appId`
or `/api/v1/apps/{app_id}` seams would create review and security ambiguity.

At the same time, not all curated apps should be opened the same way. Browser
runtime games, stateless compute apps, teacher workspace planners, document
conversion, and dev/demo surfaces have different privacy, abuse, persistence,
and migration needs. We need one explicit platform decision instead of a series
of one-off guest holes.

## Proposed Solution

Create one proposed ADR plus one proposed epic and story package that:

- separates public curated-app access from authenticated role gates
- introduces explicit per-app access profiles
- keeps the authenticated curated-app host and current app-specific APIs
  unchanged
- requires public apps to use parallel public entry/API seams
- makes browser-owned guest state authoritative for public browser profiles
- limits guest export to direct-download/no-Vault behavior
- defines explicit authenticated upgrade/import rules for apps such as
  Klassrumskartan
- records the initial current-app classification matrix so future app openings
  can reuse the same platform model

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/adr/adr-0079-public-curated-app-access-profiles-and-guest-state-boundaries.md` | Platform boundary, access profiles, current app matrix | 10 min |
| `docs/backlog/epics/epic-32-public-curated-app-access-foundation-and-klassrumskartan-demo.md` | Scope, out-of-scope, sequence | 8 min |
| `docs/backlog/stories/story-32-01-curated-app-public-access-profiles-and-current-app-matrix.md` | Per-app classification and default posture | 5 min |
| `docs/backlog/stories/story-32-02-dedicated-public-curated-app-host-and-bootstrap-boundary.md` | Public route/bootstrap seam | 5 min |
| `docs/backlog/stories/story-32-03-public-curated-app-api-namespace-and-anonymous-abuse-controls.md` | Public API boundary and abuse controls | 6 min |
| `docs/backlog/stories/story-32-04-browser-owned-guest-state-profiles-and-snapshot-contracts.md` | Browser-authoritative guest-state rules | 6 min |
| `docs/backlog/stories/story-32-05-authenticated-upgrade-orchestration-and-idempotent-import-policy.md` | Upgrade/import policy and conflict handling | 6 min |
| `docs/backlog/stories/story-32-06-klassrumskartan-demo-adoption-on-the-public-browser-workspace-profile.md` | Klassrumskartan first-consumer scope and regression boundaries | 6 min |

**Total estimated time:** ~52 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Public curated-app access is governed by explicit access profiles, not by `min_role` alone | Prevents “`Role.USER` means anonymous” drift and keeps public posture opt-in | [ ] |
| Keep `/apps/:appId`, `GET /api/v1/apps/{app_id}`, and existing `/api/v1/apps/{app_id}/...` seams authenticated | Avoids mixed privilege rules inside owner-scoped handlers and makes review clearer | [ ] |
| Public curated apps must use parallel public entry and API seams | Preserves a clean privilege boundary and reduces auth-bypass risk | [ ] |
| Browser-owned guest state is authoritative for public browser profiles | Matches Klassrumskartan's requirements and avoids guest PII in durable account tables | [ ] |
| Guest export stays direct-download and Vault/MyFiles-free | Keeps guest history/export honest without leaking authenticated artifact semantics into public mode | [ ] |
| Guest-to-account migration is prompt-based on first authenticated session, not automatic on registration | Aligns with the current no-cookie registration model and avoids hidden state re-homing | [ ] |
| Conversion Hub remains authenticated-only in the initial matrix | Anonymous upload/conversion abuse and cost make it a bad first public candidate | [ ] |

## Review Checklist

- [ ] ADR-0079 defines clear public/authenticated boundaries
- [ ] The profile matrix keeps public access opt-in and fail-closed by default
- [ ] The package keeps existing authenticated curated-app seams stable
- [ ] Stories have testable acceptance criteria
- [ ] Klassrumskartan is scoped as the first consumer, not as a special-case platform bypass
- [ ] Privacy, abuse, idempotency, and support risks are explicit

## Review Feedback

**Reviewer:** @independent-reviewer
**Date:** 2026-04-03
**Verdict:** approved

### Required Changes

- None.

### Suggestions (Optional)

- None.

### Decision Approvals

- [x] Public access profiles are the right platform model
- [x] Authenticated host/API seams stay unchanged
- [x] Browser-owned guest state is authoritative for public browser profiles
- [x] Guest export stays Vault/MyFiles-free
- [x] Guest migration is first-auth-session prompt-based
- [x] Conversion Hub remains authenticated-only initially

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | ADR-0079 | Defined reusable public curated-app access profiles, boundary rules, and initial app matrix |
| 2 | EPIC-32 | Scoped the platform foundation plus Klassrumskartan-first-adopter outcome |
| 3 | ST-32-01..06 | Drafted the story package for app matrix, public seams, guest state, upgrade policy, and Klassrumskartan adoption |
| 4 | ADR-0079, ST-32-01, EPIC-32 | Split current vs future app classification and locked the registry as canonical public-profile source of truth |
| 5 | ST-32-03 | Added the cookie-agnostic guest authority model and split `public_helper_*` vs `authenticated_upgrade_*` observability families |
| 6 | ST-32-04, ST-32-05 | Added snapshot schema/id/fingerprint requirements plus explicit draft/checkpoint conflict rules |
| 7 | ST-32-06 | Promoted smart rules to an explicit guest capability with persistence and upgrade semantics |

## Approval Notes

- 2026-04-03 external re-review approved the package after the matrix,
  source-of-truth, cookie-agnostic public-helper, snapshot-identity,
  draft/checkpoint conflict, and smart-rule scope fixes landed.
- `REV-EPIC-32` is now approved, `ADR-0079` may move to `accepted`, and
  `EPIC-32` may move to `active` while `ST-32-01` through `ST-32-06` remain
  `ready`.
