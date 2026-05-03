---
type: review
id: REV-PR-0279
title: "Review: PR-0279 shared-link seating label typography"
status: changes_requested
owners: "agents"
created: 2026-05-02
updated: 2026-05-03
reviewer: "lead-developer"
prs:
  - PR-0279
links:
  - EPIC-26
  - ST-26-06
  - ST-26-07
  - PR-0276
  - PR-0277
---

## TL;DR

`PR-0279` is the pre-implementation review gate for fixing shared-link seating
seat-label typography: remove first/second-line visual collision, render
ordinary long names in full without default ellipsis, and preserve the Teams
preview asset lifecycle when the static share renderer changes.

## Problem Statement

The static seating share page is now the canonical public presentation surface
for shared sitting plans, and its stored HTML/CSS also feeds 1200x630
Teams/social preview images. Current label styling can obscure the first-line
font when the second line is stacked tightly, and normal long names can collapse
to `...`. The review must confirm that the task is a narrow renderer/CSS
correction with deterministic long-name tiers, not a broader share-link
redesign or token/lifecycle change.

## Proposed Solution

Approve `PR-0279` as a small EPIC-26 follow-up under `ST-26-06`, with
`ST-26-07` linked because preview thumbnails are derived from the same stored
share artifact. The implementation should keep layout geometry CSS-owned, avoid
JavaScript measurement, preserve full accessible labels, and explicitly handle
renderer-version/backfill implications for existing preview assets. The
approved remediation shape keeps grouping and seating renderer provenance
separate so seating-only typography fixes do not invalidate grouping previews.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-0279-st-26-06-shared-link-seating-label-typography-and-long-name-fit.md` | Scope, acceptance, stop conditions | 12 min |
| `docs/backlog/stories/story-26-06-klassrumskartan-shareable-html-css-export-links.md` | Parent share-link renderer contract | 6 min |
| `docs/backlog/stories/story-26-07-klassrumskartan-share-link-teams-preview-thumbnails.md` | Preview asset lifecycle impact | 6 min |
| `src/skriptoteket/infrastructure/curated_apps/apps/classroom_planner/share_scene_renderer.py` | Seat label markup/CSS entry point | 8 min |
| `src/skriptoteket/infrastructure/curated_apps/apps/classroom_planner/share_preview_renderer.py` | 1200x630 render proof implications | 5 min |

**Total estimated time:** ~37 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Keep the task under `ST-26-06` with `ST-26-07` linked | The bug is in shared-link HTML/CSS, and preview thumbnails inherit that renderer. | [ ] |
| Use deterministic CSS-owned long-name tiers | The immutable share artifact must remain static and script-free. | [ ] |
| Preserve full accessible labels | Visual fallback must not hide the actual student name from `aria-label`/`title`. | [ ] |
| Split grouping and seating renderer provenance | Grouping output is unchanged; seating-only CSS/markup should not invalidate grouping preview assets. | [ ] |
| Treat seating preview asset staleness as in-scope | Existing seating preview rows may need renderer-version/hash/backfill handling after output changes. | [ ] |

## Review Checklist

- [ ] Scope is limited to shared-link seating label typography and preview lifecycle proof.
- [ ] No share-token, revocation, expiry, owner, public-read, guest helper, or import semantics change.
- [ ] The task forbids JavaScript measurement or SPA hydration inside immutable share artifacts.
- [ ] Long-name support has a reviewable weighted-width visual cap and deterministic fallback.
- [ ] Full escaped labels remain available through accessible/title text.
- [ ] Grouping renderer provenance and grouping CSS output remain unchanged unless explicitly governed.
- [ ] Seating renderer-version, hashes, stale preview detection, and backfill expectations are explicit.
- [ ] Visual proof covers desktop, mobile, and 1200x630 preview PNGs.
- [ ] Visual proof fails on hidden clipping via `scrollWidth > clientWidth`, empty visible lines, ellipsis styles, or literal `...`.
- [ ] Tests cover escaping, no-script behavior, boundary long names, wide-token fallback, and extreme fallback containment.

## Review Feedback

**Reviewer:** `lead-developer`
**Date:** `2026-05-02`
**Verdict:** changes_requested

### Prior Required Changes

1. Replace the raw `<= 18 chars` fit rule with a deterministic weighted-width
   budget that treats narrow, wide, uppercase, spaces, and hyphens differently.
2. Strengthen the proof script so every visible supported line is checked for
   hidden clipping (`scrollWidth <= clientWidth` within tolerance), non-empty
   text, and no ellipsis/`...`.
3. Split renderer provenance and CSS composition by share kind:
   `klassrumskartan-share-renderer-v1` for unchanged grouping output and a
   seating-specific v2 renderer for seating label CSS/markup.

### Current Required Changes

1. **Blocker: active seating shares are not actually forced through the new
   seating renderer/backfill contract.** The implementation moves newly
   rendered seating artifacts to `klassrumskartan-seating-share-renderer-v2`,
   but the backfill path only selects rows whose preview asset differs from the
   currently stored artifact `content_hash`, `presentation_hash`, or
   `renderer_version`. Existing active seating artifacts created with
   `klassrumskartan-share-renderer-v1` and matching old preview rows therefore
   remain fresh by definition, and the backfill command regenerates PNG bytes
   from the already-stored old `rendered_html` rather than re-rendering the
   artifact from `presentation_payload` with the new seating renderer. This does
   not satisfy the `PR-0279` / `ST-26-07` lifecycle requirement that seating
   renderer output changes either refresh/backfill active preview assets or
   prove stale-preview detection forces fresh assets. Fix by choosing and
   implementing one governed path: either explicitly document that PR-0279 is
   new-share-only and remove the active-link backfill claim from PR/story/handoff
   docs, or add a seating-only artifact refresh/backfill command that re-renders
   active seating artifacts from stored presentation payload, updates
   renderer/content provenance, and then regenerates previews. Add unit and
   repository tests for an old seating artifact with a matching old preview row
   so the selected behavior is proved.
2. **Medium: the visual proof still does not assert the full overlap contract.**
   The proof script asserts line containment inside each token, first/second-line
   separation, hidden text clipping, ellipsis absence, fallback accessibility,
   and token-token overlap. It does not assert the required map-fit or fixture
   overlap conditions: labels/tokens versus benches, fixtures, rows, or room
   edge. The PR doc says proof must inspect or assert those conditions, but the
   retained evidence now only claims that seat tokens did not overlap each
   other. Extend the Playwright proof to collect room surface and fixture rects,
   assert token/label rects stay inside the surface, and assert no occupied
   token/label intersects fixtures that should remain visually separate. Keep
   the screenshots as review artifacts, but make the failure mode mechanical.

### Suggestions (Optional)

Pending review.

### Implementation Evidence To Review

Latest proof artifacts:

- `.artifacts/pr-0279-share-label-typography/20260503T001858584113Z/proof.json`
- `.artifacts/pr-0279-share-label-typography/20260503T001858584113Z/desktop.png`
- `.artifacts/pr-0279-share-label-typography/20260503T001858584113Z/mobile.png`
- `.artifacts/pr-0279-share-label-typography/20260503T001858584113Z/preview-1200x630.png`
- `.artifacts/pr-0279-share-label-typography/20260503T001858584113Z/share-page.html`

Remediation evidence to review:

- The preview backfill path now accepts the current seating renderer version,
  selects active seating artifacts stored with older renderer provenance even
  when their old preview row matches, re-renders from `presentation_payload`,
  updates artifact renderer/content/presentation provenance, and then generates
  the preview from the refreshed artifact.
- Unit and repository tests cover an active old seating artifact with a matching
  old preview row so the governed refresh path cannot silently become
  new-share-only.
- The Playwright proof now asserts occupied tokens and visible label lines stay
  within the room surface, that the 1200x630 room surface fits the preview
  viewport, and that labels/tokens do not intersect fixtures that must remain
  visually separate. Bench carrier geometry is allowed to underlay seat tokens,
  but visible label lines are still checked against fixture overlap.

Verification recorded by the implementer:

```bash
pdm run pytest -q tests/unit/infrastructure/curated_apps/apps/classroom_planner/test_share_renderer.py
PYTHONPATH=src:. pdm run python -m scripts.prove_pr_0279_share_label_typography
pdm run pytest -q tests/integration/infrastructure/repositories/test_classroom_planner_share_artifacts.py
pdm run pytest -q tests/unit/infrastructure/curated_apps/apps/classroom_planner/test_share_renderer.py tests/unit/application/apps/classroom_planner/test_share_artifacts.py tests/unit/web/apps/classroom_planner/test_share_pages.py
pdm run pytest -q tests/unit/infrastructure/curated_apps/apps/classroom_planner/test_share_renderer.py tests/unit/application/apps/classroom_planner/test_share_artifacts.py tests/unit/web/apps/classroom_planner/test_share_pages.py tests/unit/application/apps/classroom_planner/test_authenticated_shares.py tests/unit/application/apps/classroom_planner/test_public_shares.py tests/unit/web/apps/classroom_planner/test_share_api.py tests/unit/web/test_public_apps_classroom_planner_shares.py tests/unit/infrastructure/curated_apps/apps/classroom_planner/test_share_pdf_renderer.py
pdm run handoff-validate
pdm run lint
pdm run typecheck
pdm run docs-validate
git diff --check
```

### Decision Approvals

- [ ] Keep the task under `ST-26-06` with `ST-26-07` linked
- [ ] Use deterministic CSS-owned long-name tiers
- [ ] Preserve full accessible labels
- [ ] Split grouping and seating renderer provenance
- [ ] Treat seating preview asset staleness as in-scope

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `PR-0279` | Added task for shared-link seating label typography and long-name fit. |
| 2 | `REV-PR-0279` | Added retained pre-implementation review gate. |
| 3 | `EPIC-26` / `ST-26-06` / `ST-26-07` | Linked the renderer correction and preview lifecycle implications. |
| 4 | `PR-0279` | Implemented renderer-versioned seat-label tiers and recorded proof artifacts for review. |
| 5 | `PR-0279` / `REV-PR-0279` | Added remediation requirements for weighted fit, clipping proof, and share-kind-specific renderer provenance. |
| 6 | `PR-0279` / `REV-PR-0279` | Added remediation evidence for old active seating artifact refresh/backfill and stronger map-fit/fixture-overlap proof. |
