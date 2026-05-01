---
type: review
id: REV-ST-26-07
title: "Review: ST-26-07 share-link Teams preview thumbnails"
status: changes_requested
owners: "agents"
created: 2026-05-01
updated: 2026-05-01
reviewer: "lead-developer"
stories:
  - ST-26-07
prs:
  - PR-0277
links:
  - EPIC-26
  - ST-26-06
  - REV-ST-26-06
  - PR-0276
---

## TL;DR

`ST-26-07` and `PR-0277` are the right follow-up to the successful SA24D/G20
Teams diagnostic, but the package is blocked pending re-review. The retained
findings require an explicit review gate, exact preview-asset persistence and
lifecycle semantics, a production-ready headless rendering runtime contract,
Teams cache-aware proof, and a strict JSON-LD allowlist.

## Problem Statement

This review checks whether renderer-derived Teams/social preview thumbnails are
specified enough for implementation without weakening the existing
public-by-token HTML/CSS share artifact contract from `ST-26-06`.

## Proposed Solution

Add a `PR-0277` slice that stores immutable preview thumbnails derived from the
rendered share HTML/CSS, exposes token-addressed preview images for active
shares, and emits complete link-preview metadata while keeping the opened URL
as the HTML/CSS share page.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/stories/story-26-07-klassrumskartan-share-link-teams-preview-thumbnails.md` | Parent story and readiness state | 8 min |
| `docs/backlog/prs/pr-0277-st-26-07-share-link-teams-preview-thumbnails.md` | Asset model, renderer runtime, metadata, proof obligations | 18 min |
| `docs/backlog/epics/epic-26-klassrumskartan-explicit-exports-and-class-list-import.md` | Epic scope and risk alignment | 6 min |
| `docs/backlog/stories/story-26-06-klassrumskartan-shareable-html-css-export-links.md` | Existing share-link privacy and export boundary | 6 min |
| `src/skriptoteket/infrastructure/curated_apps/apps/classroom_planner/share_renderer.py` | Current share HTML metadata source | 6 min |
| `src/skriptoteket/web/routes/classroom_planner_share_pages.py` | Current public token read route and lifecycle checks | 6 min |
| `src/skriptoteket/infrastructure/db/models/classroom_planner_share_artifact.py` | Current persisted share artifact fields | 6 min |

**Total estimated time:** ~56 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Keep the opened share URL as HTML/CSS | Preserves `ST-26-06`; the image is only for link unfurling | [x] |
| Require renderer-derived preview images for seating and grouping | The production diagnostic proved Teams uses the preview image reliably | [x] |
| Store preview assets in a first-class share-preview table | Avoids inventing persistence semantics inside implementation | [ ] |
| Use a bounded Playwright-backed adapter behind a protocol | Needed because thumbnail generation depends on browser screenshot runtime | [ ] |
| Use versioned image URLs and never-posted URLs for proof | Teams link unfurl results are cached for 30 minutes | [ ] |
| Allow only conservative `CreativeWork` JSON-LD fields | Prevents machine-readable roster, placement, or grouping leakage | [ ] |

## Review Checklist

- [x] Story is linked to the correct epic
- [x] Opened URL remains the real HTML/CSS share artifact
- [ ] Story/task readiness matches review status
- [ ] Preview asset persistence and lifecycle are exact
- [ ] Headless renderer runtime is production-defined
- [ ] Teams cache behavior is reflected in proof obligations
- [ ] JSON-LD allowed fields and exclusions are explicit

## Review Feedback

**Reviewer:** `lead-developer`
**Date:** `2026-05-01`
**Verdict:** `changes_requested`

### Required Changes

1. **P1: Ready state skips retained review gate.**

   Both `ST-26-07` and `PR-0277` were marked `ready`, but no retained review
   doc existed for `REV-ST-26-07` or `REV-PR-0277`. Rule 096 requires proposed
   implementation packages to be reviewed before implementation begins, and
   `EPIC-26` says a review doc should be created and approved before
   implementation.

   Required fix: create the target-based retained review record and keep the
   package out of `ready` state until this finding set is resolved and
   re-reviewed.

2. **P1: Preview asset persistence is not a contract yet.**

   `PR-0277` said to add "image bytes or artifact reference" plus metadata, but
   did not choose the storage shape, route identity, migration/backfill fields,
   content hash relationship, or purge linkage. Current share artifacts persist
   `rendered_html`, `rendered_css`, and hashes, not preview assets.

   Required fix: specify the exact asset model, including stored bytes versus
   static artifact reference, preview content hash, dimensions, MIME type,
   generated timestamp, renderer-version tie-in, migration/backfill behavior,
   and lifecycle deletion with the share artifact.

3. **P1: Headless render runtime is undefined.**

   Generating thumbnails before share creation completes turns the create path
   into a browser/image-rendering runtime path, but the task did not define the
   adapter, timeout, concurrency limits, browser binary installation, failure
   semantics, or production Docker/BuildKit proof. Context7 confirms Playwright
   can set a viewport and return screenshot bytes, but it also requires
   installed browser binaries.

   Required fix: name the renderer boundary and runtime, for example
   `ClassroomPlannerSharePreviewRendererProtocol` plus an infrastructure
   adapter, a 1200x630 viewport contract, hard timeout, bounded concurrency,
   deterministic failure behavior, dependency image changes, and
   production-like smoke proof.

4. **P2: Teams cache/backfill proof is overclaimed.**

   The task requires pre-existing active links to receive thumbnails and
   requires Teams proof, but did not account for Teams unfurl caching or
   already-posted text-only cards. Microsoft documents Teams link unfurl results
   as cached for 30 minutes.

   Required fix: require versioned/hash-based preview image URLs, proof using a
   never-posted production-like URL, and explicit wording that old Teams
   messages may not refresh immediately even after backfill or lazy generation.

5. **P2: Schema.org contract is too vague for roster-adjacent data.**

   The task asks for conservative schema.org JSON-LD while forbidding
   machine-readable roster, placement, or group-membership data. That intent is
   correct but not implementation-ready because the exact schema type and
   allowed properties are not named.

   Required fix: list the exact JSON-LD type and fields, explicitly exclude
   student/member arrays and placement/group relationships, and add
   hostile/sensitive-value assertions for JSON-LD separately from Open Graph
   tags.

### Suggestions (Optional)

- Keep the Teams app/message-extension path out of this slice; the diagnostic
  only proved ordinary web metadata plus `og:image`.
- Consider separating later thumbnail regeneration tooling from this first
  implementation if renderer-version migration grows beyond one PR.

### Decision Approvals

- [x] Keep the opened share URL as HTML/CSS
- [x] Require renderer-derived preview images for seating and grouping
- [ ] Store preview assets in a first-class share-preview table
- [ ] Use a bounded Playwright-backed adapter behind a protocol
- [ ] Use versioned image URLs and never-posted URLs for proof
- [ ] Allow only conservative `CreativeWork` JSON-LD fields

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `ST-26-07` | Status changed to `blocked`, review pointer added, and runtime/persistence notes tightened. |
| 2 | `PR-0277` | Status changed to `blocked`; exact preview table, route, renderer protocol, runtime limits, Docker proof, backfill command, Teams cache proof, and JSON-LD allowlist added. |
| 3 | `docs/index.md` | Review record added to the docs doorway. |
