---
type: review
id: REV-EPIC-35
title: "Review: Launch SEO and search indexing readiness"
status: pending
owners: "agents"
created: 2026-04-08
updated: 2026-04-08
reviewer: "lead-developer"
epic: EPIC-35
stories:
  - ST-35-01
  - ST-35-02
  - ST-35-03
  - ST-35-04
links:
  - REF-launch-seo-and-search-indexing-readiness-2026-04-08
  - REF-review-workflow
  - EPIC-32
---

## TL;DR

`EPIC-35` is the right backlog home for launch-phase SEO and indexing readiness. The package does
not pretend to solve ranking or content strategy. It narrows the work to the current public
surface, current domain ambiguity, crawler-facing file correctness, route metadata, and the
operator lane needed to prove the site is actually crawlable and submitted.

## Problem Statement

Skriptoteket is now close enough to launch that search indexing has become a real delivery concern,
but the current public posture still mixes operational ambiguity with crawler-facing defects:

- more than one public hostname exists, but only one currently serves the real app
- `robots.txt` and `sitemap.xml` currently fall through to the SPA shell
- non-existent URLs still return `200 OK` from the backend edge
- public pages still expose generic metadata rather than route-specific search signals
- the repo has no retained operator plan for Search Console / Bing submission and verification

Without a dedicated epic, this work is likely to drift into ad hoc “SEO polish” without first
repairing the technical crawl contract.

## Proposed Solution

Approve `EPIC-35` as the dedicated launch SEO lane with four bounded story surfaces:

1. `ST-35-01` freezes the canonical host and non-canonical host policy.
2. `ST-35-02` repairs crawler files and honest backend status semantics.
3. `ST-35-03` adds explicit public-route metadata and indexing policy.
4. `ST-35-04` closes the operator loop with search-console verification and launch checks.

Keep [REF-launch-seo-and-search-indexing-readiness-2026-04-08](../../reference/ref-launch-seo-and-search-indexing-readiness-2026-04-08.md)
as the canonical evidence record.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/reference/ref-launch-seo-and-search-indexing-readiness-2026-04-08.md` | Live findings, repo findings, and the recommended launch path | 10 min |
| `docs/backlog/epics/epic-35-launch-seo-and-search-indexing-readiness.md` | Epic scope, risks, decision trees, and story ordering | 8 min |
| `docs/backlog/stories/story-35-01-canonical-public-host-and-edge-indexability-decision-package.md` | Canonical host freeze and ops consequences | 5 min |
| `docs/backlog/stories/story-35-02-crawler-surfaces-and-honest-http-status-semantics.md` | Crawler file and soft-404 truth gate | 5 min |
| `docs/backlog/stories/story-35-03-public-route-metadata-canonical-and-indexing-policy.md` | Launch metadata and route-indexing scope | 5 min |
| `docs/backlog/stories/story-35-04-search-console-bing-and-launch-day-seo-operations.md` | Operator ownership and submission workflow | 4 min |
| `compose.prod.yaml` | Current production host anchoring | 3 min |
| `src/skriptoteket/web/routes/spa_fallback.py` | Current edge behavior that causes the crawler defects | 3 min |
| `frontend/apps/skriptoteket/index.html` | Current thin HTML shell baseline | 3 min |

**Total estimated time:** ~46 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Create `EPIC-35` as a dedicated launch SEO lane | Prevents domain, crawler, metadata, and operator work from fragmenting into ungoverned polish tasks | [ ] |
| Freeze the canonical host before deeper SEO work | Avoids building sitemap, metadata, and search-console ownership around an unstable hostname | [ ] |
| Treat crawler files and honest HTTP semantics as the first technical truth gate | Search indexing cannot be healthy if `/robots.txt`, `/sitemap.xml`, and unmatched URLs lie at the edge | [ ] |
| Keep SSR/prerender as a follow-on decision rather than a day-one blocker | Lets the team secure minimum viable crawlability first without hiding technical defects behind a larger rendering rewrite | [ ] |
| Include an explicit operator submission and verification story | Makes launch readiness measurable instead of anecdotal | [ ] |

## Review Checklist

- [ ] The epic scope is limited to launch-phase search readiness rather than ranking or generic marketing work
- [ ] The story split keeps host policy, crawler semantics, metadata, and operator operations reviewable as separate concerns
- [ ] The current live evidence is strong enough to justify the proposed order of work
- [ ] The package distinguishes clearly between “crawlable and submitted” and “already indexed”
- [ ] The epic is ready to govern implementation without reopening `EPIC-32` public-route scope unnecessarily

## Review Feedback

**Reviewer:** `lead-developer`
**Date:** `2026-04-08`
**Verdict:** pending

### Required Changes

- Pending review.

### Suggestions (Optional)

- Pending review.

### Decision Approvals

- [ ] Create `EPIC-35` as a dedicated launch SEO lane
- [ ] Freeze the canonical host before deeper SEO work
- [ ] Treat crawler files and honest HTTP semantics as the first technical truth gate
- [ ] Keep SSR/prerender as a follow-on decision rather than a day-one blocker
- [ ] Include an explicit operator submission and verification story

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `REF-launch-seo-and-search-indexing-readiness-2026-04-08` | Added the evidence and analysis reference for the 2026-04-08 launch SEO assessment |
| 2 | `EPIC-35` | Added the canonical launch SEO and indexing-readiness epic |
| 3 | `ST-35-01` to `ST-35-04` | Added the bounded story scaffolds for host policy, crawler semantics, metadata, and search operations |
| 4 | `REV-EPIC-35` | Opened the required retained review gate for the proposed epic package |
