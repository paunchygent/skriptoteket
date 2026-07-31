---
type: reference
id: REF-SKRIPT-MOCKUP-pr-0364-authenticated-home-work-apps-surface
title: PR-0364 authenticated home work-apps surface
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: active
reference_kind: mockup
summary: PR-0364 authenticated home work-apps surface
---

## Intent

### Source: Source introduction

### PR-0364 Authenticated Home Work-Apps Surface

### Source: Purpose

Retain the approved C2 direction for replacing the signed-in generic dashboard
first impression with an app-first authenticated work surface.

## Package Manifest

### Source: Assets

- [Static HTML/CSS mockup](index.html)
- [Rendered approval screenshot](approved-c2-authenticated-home.png)

## Design Interpretation

### Source: Approved Direction

- The first actionable signed-in surface is `Arbetsappar`.
- `Klassrumskartan`, `Exam Converter`, `Audio Transcription`,
  `Document Converter`, and `Kodredigerare` are presented as app shelves.
- `Kodredigerare` is an app, not a form, suggestion card, or secondary
  contribute action.
- `Document Converter` is retained as a visible product lane only; do not add a
  runtime link until a truthful reviewed route exists.
- `Mina körningar`, run-history summaries, latest-used apps, and recent-used
  vanity rows are not part of the approved home surface.
- Runtime-ready app shelves are whole-card links. Do not add separate `Öppna`
  links inside the app cards.
- App shelves need identifying graphics, stable equal-height geometry, and
  borders rather than hard per-card drop shadows.
- The lower secondary area is a flat ledger surface for files, catalog, and
  contribution affordances. Do not put UI cards inside another card or panel.
- `Mina filer` remains prominent as a material/file continuation path.
- The mockup shows the intended shell hierarchy. Runtime implementation may
  split home content and persistent navigation into their governed PR slices,
  but must preserve the approved hierarchy across the sequence.

## Runtime And Proof Boundary

No separate source material was recorded for this section.

## Governing Links And Follow-Up

### Source: Rejected Patterns

- No public landing-page redesign.
- No vanity highlight/callout copy.
- No `Mina körningar` primary or secondary card on this surface.
- No latest-used app row.
- No nested card layout for `Kodredigerare` or `Föreslå verktyg`.
- No separate `Öppna` action when the app card itself is the link.
- No fake `Document Converter` runtime link.
- No fixed heavy shadow treatment on individual app cards.
