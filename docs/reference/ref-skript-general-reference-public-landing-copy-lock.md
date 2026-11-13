---
type: reference
id: REF-SKRIPT-GENERAL-reference-public-landing-copy-lock
title: 'Reference: public landing copy lock'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: active
reference_kind: general
retired_ids:
- REF-public-landing-copy-lock
summary: 'Reference: public landing copy lock'
---

## Overview

### Reference: Public Landing Copy Lock

### Purpose

This reference locks the approved signed-out public landing copy after
`PR-0371` and the public header simplification after `PR-0372`. Future changes
to the landing-page words must update this reference, the focused landing
tests, and the governing backlog task or follow-up task.

### Scope

This copy applies to the signed-out `/` landing route, including the
Klassrumskartan hero and the below-hero authenticated-app preview.

Runtime sources:

- `frontend/apps/skriptoteket/src/views/HomeView.vue`
- `frontend/apps/skriptoteket/src/components/home/LandingClassroomPreview.vue`
- `frontend/apps/skriptoteket/src/components/home/LandingAuthenticatedPreview.vue`
- `frontend/apps/skriptoteket/src/components/layout/LandingLayout.vue`
- `frontend/apps/skriptoteket/src/views/HomeView.spec.ts`

Governance sources:

- `EPIC-37`
- `ST-37-04`
- `PR-0370`
- `PR-0371`
- `PR-0372`
- `MOCK-pr-0370-public-landing-approved-copy`

### Approved Public Header Copy

Header actions:

```text
Logga in
Hjälp
```

The public header must not render a separate `Klassrumskartan` navigation link.
The hero section owns the public Klassrumskartan CTA.

### Approved Signed-Out Hero Copy

Heading:

```text
Lektionsplanera direkt i webbläsaren.
```

Lead:

```text
Klassrumskartan är en av Skriptotekets appar. Den är öppen för alla.
Du behöver inget konto för att komma igång.
```

Primary action:

```text
Öppna Klassrumskartan
```

Secondary line:

```text
eller skapa ett konto för att spara ditt arbete.
```

### Approved Authenticated-App Preview Copy

Section heading:

```text
När du loggar in
```

Panels:

```text
Transkribera tal till text
Skapa PDF:er med hjälp av HTML och CSS
Skapa, redigera och konvertera prov
```

Footer actions:

```text
Logga in
Skapa konto
```

### Explicit Copy Decisions

- The signed-out landing page no longer renders the repeated
  Klassrumskartan showcase from `LandingFeaturedClassroom`.
- The signed-out landing page no longer renders the retired generic
  authenticated-value ledger, its lead paragraph, or its `Kräver konto`
  badges.
- The authenticated-app preview must not render Roman numerals, numeric
  markers, category labels, metadata labels, `Direkt i appen`, `Vad du gör`,
  `Nytta`, or similar explanatory chrome.
- The authenticated-app preview must reuse the same app symbol assets used on
  authenticated home for audio transcription, document conversion, and exam
  handling. Do not replace them with custom SVG diagrams or alternate icon
  compositions.
- The hero keeps the existing Klassrumskartan illustration direction through
  `LandingClassroomPreview`.
- The public header keeps `Logga in` and `Hjälp` as same-style actions on one
  row and does not add a hamburger or extra public navigation for
  `Klassrumskartan`.
- The footer actions `Logga in` and `Skapa konto` must continue to open shared
  HuleEdu ceremony URLs through `resolveLandingAuthContinuation(...)` and
  `sharedAuthCeremonyUrl(...)`.

### Change Policy

When public landing copy changes:

1. Update this reference in the same docs-as-code slice.
2. Update `HomeView.spec.ts` or more specific component tests to lock the new
   approved words.
3. Record whether the change affects `ST-37-04`, the public Klassrumskartan
   hero, or the signed-out authenticated-app preview.
4. Keep the signed-out copy short, conversational, teacher-facing, and free of
   implementation terms.

## Facts And Semantics

The source material below remains authoritative for this section.

## Decisions And Interpretation

The source material below remains authoritative for this section.
