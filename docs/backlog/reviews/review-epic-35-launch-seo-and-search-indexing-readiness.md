---
type: review
id: REV-EPIC-35
title: "Review: Launch SEO and search indexing readiness"
status: approved
owners: "agents"
created: 2026-04-08
updated: 2026-04-15
reviewer: "lead-developer"
epic: EPIC-35
stories:
  - ST-35-01
  - ST-35-02
  - ST-35-03
  - ST-35-04
links:
  - REF-huleedu-launch-surface-and-shared-auth-topology-2026-04-08
  - REF-launch-seo-and-search-indexing-readiness-2026-04-08
  - REF-review-workflow
  - EPIC-28
  - EPIC-32
---

## TL;DR

`EPIC-35` is the right backlog home for launch-phase SEO and indexing readiness once the broader
cross-repo topology is frozen by `EPIC-28`. The package does not pretend to solve ranking,
content strategy, or the HuleEdu platform rollout itself. It narrows the work to the Skriptoteket
public app host, crawler-facing file correctness, route metadata, and the operator lane needed to
prove the site is actually crawlable and submitted.

## Problem Statement

Skriptoteket is now close enough to launch that search indexing has become a real delivery concern,
but the current public posture still mixes cross-repo dependency ambiguity with crawler-facing defects:

- more than one public hostname exists, but only one currently serves the real app
- `robots.txt` and `sitemap.xml` currently fall through to the SPA shell
- non-existent URLs still return `200 OK` from the backend edge
- public pages still expose generic metadata rather than route-specific search signals
- the repo has no retained operator plan for Search Console / Bing submission and verification

Without a dedicated epic, this work is likely to drift into ad hoc “SEO polish” without first
repairing the technical crawl contract or consuming the shared launch topology correctly.

## Proposed Solution

Approve `EPIC-35` as the dedicated downstream Skriptoteket launch SEO lane with four bounded story surfaces:

1. `ST-35-01` freezes the Skriptoteket-side host and edge policy under the upstream topology from `ST-28-05`.
2. `ST-35-02` repairs crawler files and honest backend status semantics.
3. `ST-35-03` adds explicit public-route metadata and indexing policy.
4. `ST-35-04` closes the operator loop with search-console verification and launch checks.

Keep [REF-launch-seo-and-search-indexing-readiness-2026-04-08](../../reference/ref-launch-seo-and-search-indexing-readiness-2026-04-08.md)
as the canonical evidence record.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/reference/ref-huleedu-launch-surface-and-shared-auth-topology-2026-04-08.md` | Upstream launch topology and cross-repo ownership matrix | 6 min |
| `docs/reference/ref-launch-seo-and-search-indexing-readiness-2026-04-08.md` | Live findings, repo findings, and the recommended launch path | 10 min |
| `docs/backlog/epics/epic-35-launch-seo-and-search-indexing-readiness.md` | Epic scope, risks, decision trees, and story ordering | 8 min |
| `docs/backlog/stories/story-35-01-canonical-public-host-and-edge-indexability-decision-package.md` | Canonical host freeze and ops consequences | 5 min |
| `docs/backlog/stories/story-35-02-crawler-surfaces-and-honest-http-status-semantics.md` | Crawler file and soft-404 truth gate | 5 min |
| `docs/backlog/stories/story-35-03-public-route-metadata-canonical-and-indexing-policy.md` | Launch metadata and route-indexing scope | 5 min |
| `docs/backlog/stories/story-35-04-search-console-bing-and-launch-day-seo-operations.md` | Operator ownership and submission workflow | 4 min |
| `compose.prod.yaml` | Current production host anchoring | 3 min |
| `src/skriptoteket/web/routes/spa_fallback.py` | Current edge behavior that causes the crawler defects | 3 min |
| `frontend/apps/skriptoteket/index.html` | Current thin HTML shell baseline | 3 min |

**Total estimated time:** ~52 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Create `EPIC-35` as a dedicated launch SEO lane | Prevents domain, crawler, metadata, and operator work from fragmenting into ungoverned polish tasks | [ ] |
| Consume the upstream topology from `EPIC-28` before deeper SEO work | Avoids building sitemap, metadata, and search-console ownership around the wrong product boundary | [ ] |
| Treat crawler files and honest HTTP semantics as the first technical truth gate | Search indexing cannot be healthy if `/robots.txt`, `/sitemap.xml`, and unmatched URLs lie at the edge | [ ] |
| Keep SSR/prerender as a follow-on decision rather than a day-one blocker | Lets the team secure minimum viable crawlability first without hiding technical defects behind a larger rendering rewrite | [ ] |
| Include an explicit operator submission and verification story | Makes launch readiness measurable instead of anecdotal | [ ] |

## Review Checklist

- [ ] The epic scope is limited to launch-phase search readiness rather than ranking or generic marketing work
- [ ] The story split keeps Skriptoteket app-host SEO work downstream of the cross-repo topology gate in `EPIC-28`
- [ ] The story split keeps host policy, crawler semantics, metadata, and operator operations reviewable as separate concerns
- [ ] The current live evidence is strong enough to justify the proposed order of work
- [ ] The package distinguishes clearly between “crawlable and submitted” and “already indexed”
- [ ] The epic is ready to govern implementation without reopening `EPIC-32` public-route scope unnecessarily

## Review Feedback

**Reviewer:** `lead-developer`
**Date:** `2026-04-15`
**Verdict:** `approved`

### Review Evidence

- Live edge re-check on 2026-04-15 confirmed the 2026-04-08 crawler defects still exist:
  `/`, `/robots.txt`, `/sitemap.xml`, and an arbitrary missing path all returned the same
  HTML shell with `200 OK` and `content-type: text/html; charset=utf-8`.
- Official crawler behavior still makes this a real contract issue: Google can consider `2xx`
  responses for indexing, treats `4xx` responses as missing content, and reports soft-404-like
  content separately; Bing Webmaster Tools expects verified site ownership before sitemap,
  URL-inspection, and robots validation workflows are available.

### Required Changes

- None. Re-review confirms the previous requested changes are resolved:
  - `ST-35-03` now makes backend-served initial HTML the launch-visible metadata contract for `/`
    and `/public/apps/classroom.group-seating-studio`, keeps client-only head management out of the
    proof path, and requires both backend HTML assertions and browser hydration checks.
  - `ST-35-02` now includes an explicit route-family matrix covering crawler files,
    launch-indexable public pages, non-indexable public app pages, auth/lifecycle routes,
    authenticated/private routes, malformed public-app routes, unknown routes, and backend-owned
    non-SPA paths.
  - `ST-35-04` now assigns Search Console / Bing verification to account-owning product/deployment
    operators, allows a blocked state when account access is missing, and defines redacted evidence
    fields plus post-deploy revalidation.

### Suggestions (Optional)

- Keep the first implementation slices small: `ST-35-01` should freeze host policy and `ST-35-02`
  should repair crawler files/status semantics before metadata work starts.
- Treat dynamic `/public/apps/{appId}` handling carefully during implementation. If the backend
  cannot safely resolve public app IDs without muddying fallback boundaries, keep the initial
  allowlist narrow and explicit for launch.

### Decision Approvals

- [x] Create `EPIC-35` as a dedicated launch SEO lane
- [x] Consume the upstream topology from `EPIC-28` before deeper SEO work
- [x] Treat crawler files and honest HTTP semantics as the first technical truth gate
- [x] Keep SSR/prerender as a follow-on decision rather than a day-one blocker
- [x] Include an explicit operator submission and verification story

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `REF-launch-seo-and-search-indexing-readiness-2026-04-08` | Added the evidence and analysis reference for the 2026-04-08 launch SEO assessment |
| 2 | `EPIC-35` | Added the canonical launch SEO and indexing-readiness epic |
| 3 | `ST-35-01` to `ST-35-04` | Added the bounded story scaffolds for host policy, crawler semantics, metadata, and search operations |
| 4 | `REV-EPIC-35` | Opened the required retained review gate for the proposed epic package |
| 5 | `ST-35-03` | Chose backend-served initial HTML as the launch-visible metadata contract and required backend plus hydration proof |
| 6 | `ST-35-02` | Added the explicit server-side route-family matrix and proof requirements for crawler files, valid SPA routes, malformed public routes, and unknown routes |
| 7 | `ST-35-04` | Assigned account-bound verification to product/deployment operators and added allowed verification methods, redacted evidence fields, blocked-state handling, and a post-deploy checklist |
| 8 | `REF-launch-seo-and-search-indexing-readiness-2026-04-08` | Refreshed the canonical evidence record with the 2026-04-15 live re-check and official crawler-reference links |
| 9 | `EPIC-35` | Updated the epic notes to record the April 15 changes-requested remediation before re-review |

## Approval Notes

- 2026-04-15 re-review approved the package after the three prior findings were addressed in the
  governed stories.
- The approval is for the documentation package and implementation governance. Live production
  still has the known crawler defects until the follow-on `ST-35-01` / `ST-35-02` implementation
  slices ship and are verified.
