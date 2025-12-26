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
| OR filter logic (not AND) | More discovery, less restrictive | [ ] |
| Server-side favorites (not localStorage) | Cross-device sync via existing auth | [ ] |
| ILIKE search (not full-text) | Simple, sufficient for ~100 tools | [ ] |
| Flat view as default `/browse` | Faster discovery than 3-click hierarchy | [ ] |
| Hide empty sections on home | Less clutter when user has no favorites/recent | [ ] |

## Review Checklist

- [ ] ADR-0041 defines clear API contract for favorites
- [ ] ADR-0042 defines clear filter/search behavior
- [ ] EPIC-16 scope is appropriate (not too broad)
- [ ] Stories have testable acceptance criteria
- [ ] Implementation aligns with codebase patterns (DDD, Clean Architecture)
- [ ] File paths in stories match existing conventions
- [ ] Risks are identified with reasonable mitigations

---

## Review Feedback

**Reviewer:** @lead-developer
**Date:** YYYY-MM-DD
**Verdict:** pending

### Required Changes

[To be filled by reviewer]

### Suggestions (Optional)

[To be filled by reviewer]

### Decision Approvals

- [ ] OR filter logic
- [ ] Server-side favorites
- [ ] ILIKE search
- [ ] Flat view as default
- [ ] Hide empty sections

---

## Changes Made

[To be filled by author after addressing feedback]

| Change | Artifact | Description |
|--------|----------|-------------|
| - | - | - |
