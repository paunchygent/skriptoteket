---
type: pr
id: PR-0370
title: "ST-37-04 public landing authenticated-app preview mockup approval"
status: in_progress
owners: "agents"
created: 2026-06-19
updated: 2026-06-19
stories:
  - "ST-37-04"
tags: ["frontend", "ux", "landing-page", "mockup", "copy"]
dependencies:
  - "PR-0362"
  - "PR-0364"
  - "REF-current-product-lanes-and-sir-convert-boundary-v1"
  - "REF-app-presentation-decomposition-and-naming-plan-v1"
  - "REF-public-landing-copy-lock"
acceptance_criteria:
  - "Given the signed-out landing page currently repeats Klassrumskartan below a Klassrumskartan-led hero, when this mockup package closes, then the approved direction replaces the repeated section with a truthful authenticated-app preview concept."
  - "Given the product owner requires image-first exploration, when concept work begins, then image-generated landing-page mockups are created and iterated until product-owner approval before any HTML/CSS mockup is authored."
  - "Given the product owner must approve all Swedish copy, when HTML/CSS mockups are authored, then every visible sentence remains provisional until product-owner approval is recorded in this package."
  - "Given this is a mockup and approval package, when it closes, then no production Vue, route, test, registry, public capability, Sir Convert, HuleEdu, QTI, DOCX, or backend/API contract change has been made."
---

# PR-0370: ST-37-04 Public Landing Authenticated-App Preview Mockup Approval

## Problem

The current signed-out landing page correctly leads with the public
Klassrumskartan entry, but it then repeats Klassrumskartan in the next major
section. The authenticated-value section stays generic, so visitors do not see
the current app-lane proposition clearly before being asked to log in or create
an account.

## Goal

Create and approve a new public landing direction that keeps Klassrumskartan as
the public first action while using the below-the-fold authenticated preview to
show real account-backed Skriptoteket app lanes.

The required design sequence is:

1. Generate image mockup directions.
2. Iterate image mockups until product-owner approval.
3. Create HTML/CSS mockups from the approved image direction.
4. Iterate HTML/CSS layout and Swedish copy until product-owner approval.
5. Hand the approved package to a separate implementation slice.

## Non-goals

- No production `HomeView.vue` or landing component changes in this slice.
- No `HomeView.spec.ts` or copy-lock updates in this slice.
- No route, app-id, registry, backend/API, Sir Convert, HuleEdu, QTI, DOCX, or
  Exam.net contract changes.
- No HTML/CSS mockup before an image-generated direction is approved.
- No production copy that promises unavailable authenticated capabilities.

## Approval Rules

- Image-generated mockups are directional and may use provisional labels.
- `round-4-no-index-markers.png` is the approved image direction.
- The copy requirements review package must define what the page must
  communicate before any Swedish copy alternatives are drafted.
- `docs/mockups/pr-0370-public-landing-authenticated-app-preview/approved-copy.md`
  is the approved copy source for HTML/CSS mockups.
- The final HTML/CSS mockup must record whether `Transkribera tal till text`,
  HTML/CSS-to-PDF conversion, digital exam creation/editing/sharing, printed
  export, and Exam.net import are live capabilities or planned capabilities.
- Production implementation may only begin after this package records the
  approved visual direction, section order, CTA labels, and Swedish copy.

## Implementation Plan

1. Create the mockup bundle:
   `docs/mockups/pr-0370-public-landing-authenticated-app-preview/`.
2. Generate 2-3 image concept directions for the public landing page:
   - preserve the public Klassrumskartan hero and primary CTA
   - replace the repeated Klassrumskartan showcase with account-backed app
     lanes
   - show account-only capability honestly
   - avoid generic card-stack marketing composition
3. Iterate image concepts until the product owner approves one direction.
4. Convert the approved image direction into self-contained HTML/CSS mockups in
   the bundle.
5. Iterate the HTML/CSS mockups until the product owner approves the final
   Swedish copy and layout.
6. Update the bundle README with approved direction, rejected variants, and
   implementation handoff notes.
7. Create or attach the follow-up implementation slice with red-first landing
   tests and live browser proof requirements.

## Test Plan

- Open retained image previews and HTML/CSS mockups locally for visual review.
- `pdm run docs-validate`
- `git diff --check`

## Rollback Plan

Remove the mockup bundle and this PR slice if product direction changes before
approval. Leave existing public landing production code and copy lock untouched.
