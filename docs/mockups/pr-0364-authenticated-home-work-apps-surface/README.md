---
type: mockup
id: MOCK-pr-0364-authenticated-home-work-apps-surface
title: "PR-0364 authenticated home work-apps surface"
status: approved
owners: "agents"
created: 2026-06-19
updated: 2026-06-19
tags: ["PR-0364", "ST-37-03", "authenticated-home", "service-shell", "mockup"]
summary: "Approved C2 direction for the authenticated home and app-first shell surface."
canonical_preview: "index.html"
submission_policy: "Use the approved C2 mockup as product-owner direction before changing authenticated home or shell navigation surfaces."
winner_policy: "Implement the hierarchy, app shelf semantics, and forbidden-pattern exclusions; do not pixel-match the static HTML."
---

# PR-0364 Authenticated Home Work-Apps Surface

## Purpose

Retain the approved C2 direction for replacing the signed-in generic dashboard
first impression with an app-first authenticated work surface.

## Assets

- [Static HTML/CSS mockup](index.html)
- [Rendered approval screenshot](approved-c2-authenticated-home.png)

## Approved Direction

- The first actionable signed-in surface is `Arbetsappar`.
- `Klassrumskartan`, `Exam Converter`, `Audio Transcription`,
  `Document Converter`, and `Kodredigerare` are presented as app shelves.
- `Kodredigerare` is an app, not a form, suggestion card, or secondary
  contribute action.
- `Mina körningar`, run-history summaries, latest-used apps, and recent-used
  vanity rows are not part of the approved home surface.
- App shelves are whole-card links. Do not add separate `Öppna` links inside
  the app cards.
- App shelves need identifying graphics, stable equal-height geometry, and
  borders rather than hard per-card drop shadows.
- The lower secondary area is a flat ledger surface for files, catalog, and
  contribution affordances. Do not put UI cards inside another card or panel.
- `Mina filer` remains prominent as a material/file continuation path.
- The mockup shows the intended shell hierarchy. Runtime implementation may
  split home content and persistent navigation into their governed PR slices,
  but must preserve the approved hierarchy across the sequence.

## Rejected Patterns

- No public landing-page redesign.
- No vanity highlight/callout copy.
- No `Mina körningar` primary or secondary card on this surface.
- No latest-used app row.
- No nested card layout for `Kodredigerare` or `Föreslå verktyg`.
- No separate `Öppna` action when the app card itself is the link.
- No fixed heavy shadow treatment on individual app cards.
