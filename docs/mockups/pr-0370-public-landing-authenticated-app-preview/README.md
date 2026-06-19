---
type: mockup
id: MOCK-pr-0370-public-landing-authenticated-app-preview
title: "PR-0370 public landing authenticated-app preview"
status: proposed
owners: "agents"
created: 2026-06-19
updated: 2026-06-19
tags: ["PR-0370", "ST-37-04", "public-landing", "authenticated-preview", "mockup"]
summary: "Image-first and then HTML/CSS mockup package for replacing the repeated Klassrumskartan section with a truthful account-backed app preview."
canonical_preview: "index.html"
submission_policy: "Generate and iterate image mockups before authoring HTML/CSS; all Swedish copy remains provisional until product-owner approval."
winner_policy: "Approved image direction must be translated into HTML/CSS and approved again before production implementation."
---

# PR-0370 Public Landing Authenticated-App Preview

## Purpose

Explore a revised signed-out landing page that keeps Klassrumskartan as the
public first action while using the next major section to preview authenticated
Skriptoteket apps instead of repeating Klassrumskartan.

## Required Sequence

1. Image-generated mockups.
2. Product-owner approval or iteration.
3. HTML/CSS mockups based on the approved image direction.
4. Product-owner approval or iteration.
5. Separate production implementation slice.

## Review Packages

- [Copy requirements review](copy-requirements-review.md)
- [Approved copy](approved-copy.md)

## Current Product Truth Ledger

| App or promise | Mockup treatment |
|---|---|
| Klassrumskartan | Public hero and primary CTA remain visible. |
| Ljudtranskribering | May be shown as account-backed app value. |
| Provkonverteraren | May be shown as account-backed app value with truthful export wording. |
| Dokumentkonverteraren | May be shown as planned/account-backed lane only until a truthful route exists. |
| HTML/CSS to PDF | May be explored as document conversion copy; production wording needs route/capability verification. |
| Digital exams: create, edit, share | May be explored as product direction; production wording needs current capability verification. |
| Exam.net import/export | May be explored only as provisional copy until the implementation slice verifies exact live capability. |

## Image Concept Brief

The first image-generation round should create distinct landing-page directions,
not final production assets:

- Preserve the current brutalist-academic Skriptoteket identity: grid paper
  canvas, deep navy structure, hard rules, strong serif headings, calm
  institutional tone.
- Keep the hero focused on the open public Klassrumskartan route.
- Replace the repeated Klassrumskartan showcase with a more specific
  authenticated-app preview for speech-to-text, document/PDF conversion, and
  digital exams.
- Make account-gated status clear without turning the section into a dull
  login wall.
- Avoid glossy SaaS gradients, soft cards, nested cards, oversized marketing
  claims, and generic icon rows.

## Draft Copy Constraints

- Swedish copy is provisional until explicitly approved by the product owner.
- Copy should be short, teacher-facing, and free of internal implementation
  terms.
- Category labels and metadata labels are forbidden in the public landing
  direction. Do not use headings or markers such as `Vad du gör`, `Nytta`,
  `Status`, account-state column labels, all-caps eyebrow labels, or similar
  explanatory chrome. Let section structure, normal headings, and direct app
  names carry the meaning.
- Roman numerals, numeric list markers, and index markers are forbidden in the
  authenticated-app preview. The three workflows should be separated by layout,
  dividers, and diagrams instead of `I`, `II`, `III`, `01`, `02`, or similar
  numbering.
- Do not use final production phrasing for planned capabilities unless the
  follow-up implementation slice verifies that the capability is live.

## Approval Log

- 2026-06-19: Product owner required image-generated mockups first, then
  approval/iteration, then HTML/CSS mockups, then approval/iteration, then
  implementation.
- 2026-06-19: First image-generation round rejected by product owner as too
  AI-sloppy. Do not use those concepts as implementation direction.
- 2026-06-19: Product owner banned category/metadata labels such as `Vad du
  gör` and `Nytta`; future concepts must rely on structure rather than labels.
- 2026-06-19: Product owner accepted the label-free composition as close, with
  the required change that Roman numerals/index markers must be removed before
  HTML/CSS mockups begin.
- 2026-06-19: Product owner approved
  `round-4-no-index-markers.png` as the image direction and requested a minimum
  copy requirements review package with no copy suggestions.
- 2026-06-19: Product owner approved the final public landing copy. The copy is
  recorded in `approved-copy.md`; production copy lock update is deferred to
  the implementation slice.
- 2026-06-19: Product owner corrected workflow heading to `När du skapar ett
  konto`; HTML/CSS mockup updated accordingly.

## Assets

- HTML/CSS mockup:
  - `index.html`: current HTML/CSS approval candidate built from the approved
    image direction and approved copy.
  - Verified screenshots:
    `.artifacts/pr-0370-public-landing-authenticated-app-preview/html-mockup-desktop.png`
    and
    `.artifacts/pr-0370-public-landing-authenticated-app-preview/html-mockup-mobile.png`.
- Image-generated concepts:
  - `round-2-blueprint-cells.png`: retained intermediate concept, not
    approved.
  - `round-2-flat-ledger.png`: retained intermediate concept, not approved.
  - `round-3-label-free-with-pdf-leak.png`: retained anti-example; still leaks
    diagram text.
  - `round-3-icon-only-composition.png`: label-free candidate superseded by
    the no-index-marker variant.
  - `round-4-no-index-markers.png`: approved image direction; removes
    Roman numerals, numeric markers, labels, and lower-section microcopy.
