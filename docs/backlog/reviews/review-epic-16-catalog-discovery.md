---
type: review
id: REV-EPIC-16
title: "Review: Catalog Discovery and Personalization"
status: pending
owners: "agents"
created: 2025-12-26
reviewer: "lead-developer"
epic: EPIC-16
adrs:
  - ADR-0041
  - ADR-0042
stories:
  - ST-16-01
  - ST-16-02
  - ST-16-03
  - ST-16-04
  - ST-16-05
  - ST-16-06
  - ST-16-07
---

## TL;DR

We're proposing to redesign how teachers find tools in Skriptoteket. Instead of the current 3-click hierarchical navigation (Profession → Category → Tools), we want a **flat catalog view** where all tools are visible immediately with **filters**, **search**, and **favorites**.

## Problem Statement

Teachers using Skriptoteket today must:

1. Click a profession ("Lärare")
2. Click a category ("Svenska")
3. Finally see the tools

This is slow for users who:

- Don't know which category contains their tool
- Want to browse across categories
- Return frequently to the same tools

There's also **no way to bookmark tools** — every session starts fresh.

## Proposed Solution

### 1. Flat Catalog View (ADR-0042)

`/browse` becomes a single page showing ALL published tools with:

- **Filter sidebar**: Checkboxes for professions and categories
- **OR logic**: Selecting "Svenska" + "Matematik" shows tools with *either* tag
- **Search**: Simple ILIKE on title/summary
- **URL sync**: Filters reflected in query params (shareable, bookmarkable)

### 2. User Favorites (ADR-0041)

- Server-side storage (PostgreSQL, not localStorage)
- Simple star toggle on tool cards
- Cross-device sync via existing auth
- New `user_favorites` table with cascade deletes

### 3. Recently Used Tools

- Leverage existing `tool_runs` table
- No new tables needed
- Show on home page for quick access

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/adr/adr-0041-user-favorites-and-tool-bookmarking.md` | API contract, table design, invariants | 5 min |
| `docs/adr/adr-0042-flat-catalog-with-label-filtering.md` | Filter logic, query params, search approach | 5 min |
| `docs/backlog/epics/epic-16-catalog-discovery-and-personalization.md` | Scope in/out, risks | 3 min |
| `docs/backlog/stories/story-16-*.md` | Acceptance criteria, file paths | 10 min |

**Total estimated time:** ~25 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Filter semantics (OR within facet, AND across facets) | Keeps discovery broad while still allowing narrowing | [x] |
| Server-side favorites (not localStorage) | Cross-device sync via existing auth | [x] |
| ILIKE search (not full-text) | Simple, sufficient for ~100 tools | [x] |
| Flat view as default `/browse` | Faster discovery than 3-click hierarchy | [ ] |
| Curated apps remain hierarchical-only | Keeps flat browse about tools; curated apps stay discoverable via `/browse/professions/...` | [ ] |
| Hide empty sections on home | Less clutter when user has no favorites/recent | [x] |

## Review Checklist

- [x] ADR-0041 defines clear API contract for favorites
- [x] ADR-0042 defines clear filter/search behavior
- [x] EPIC-16 scope is appropriate (not too broad)
- [x] Stories have testable acceptance criteria
- [x] Implementation aligns with codebase patterns (DDD, Clean Architecture)
- [x] File paths in stories match existing conventions
- [x] Risks are identified with reasonable mitigations
- [ ] Curated apps definition + scope is agreed

---

## Review Feedback

**Reviewer:** @lead-developer
**Date:** 2025-12-27
**Verdict:** pending

### Required Changes

All required doc-level changes have been addressed (see **Changes Made** below).

Remaining open item to confirm before final approval:

1. Confirm the definition/scope of **curated apps**, and whether EPIC-16 should keep them hierarchical-only (as drafted)
   or include them in flat browse/recent/favorites.

### Suggestions (Optional)

- Consider returning taxonomy (professions/categories) from a separate endpoint or caching it client-side to
  avoid re-sending it on every filter change; current approach is fine at today’s scale.
- Add a small “Browse by profession →” link on the flat browse view (even if hierarchical is secondary) to
  preserve alternative navigation.
- Add/expand EPIC risks: curated-app discoverability regression; breadcrumbs confusion after route swap.

### Decision Approvals

- [x] Filter semantics (OR within facet, AND across facets)
- [x] Server-side favorites
- [x] ILIKE search
- [ ] Flat view as default (approve once hierarchical entrypoint + breadcrumbs/curated-app plan is confirmed)
- [ ] Curated apps remain hierarchical-only
- [x] Hide empty sections

---

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| Clarified filter semantics | `docs/adr/adr-0042-flat-catalog-with-label-filtering.md` | Defined OR-within-facet + AND-across-facets, added unknown-slug behavior, added explicit hierarchical entrypoint route + link requirement |
| Reconciled flat catalog story | `docs/backlog/stories/story-16-03-flat-catalog-api-with-filtering.md` | Fixed cross-facet AC, clarified unknown-slug behavior, removed bearer-token language |
| Reconciled favorites ADR to repo patterns | `docs/adr/adr-0041-user-favorites-and-tool-bookmarking.md` | Switched to Pydantic domain model, documented CSRF + `limit` for listing favorites, narrowed `is_favorite` scope to in-epic endpoints |
| Reconciled favorites API story | `docs/backlog/stories/story-16-02-favorites-api-endpoints.md` | Added CSRF expectations, added `limit` support, clarified “published only” listings |
| Clarified recent-tools scope + typing | `docs/backlog/stories/story-16-04-recently-used-tools-api.md` | Explicitly excluded curated apps; fixed repo method to return `(tool_id, last_used_at)` |
| Preserved hierarchical discoverability | `docs/backlog/stories/story-16-05-flat-catalog-vue-view.md` | Added `/browse/professions` entrypoint + breadcrumb update requirement; added “browse by profession” link + `favorites=true` UI-only filter AC |
| Corrected HomeView story | `docs/backlog/stories/story-16-07-home-view-favorites-and-recent.md` | Fixed tool-run route, clarified integration into existing role-based dashboard, resolved “Visa alla” as `/browse?favorites=true` |
