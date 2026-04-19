---
type: reference
id: REF-public-landing-copy-lock
title: "Reference: public landing copy lock"
status: active
owners: "agents"
created: 2026-04-19
updated: 2026-04-19
topic: "public-landing-copy"
---

# Reference: Public Landing Copy Lock

## Purpose

This reference locks the approved signed-out public landing copy after `PR-0270`.
Future changes to the landing-page words must update this reference, the focused
landing tests, and the governing backlog task or follow-up task.

## Scope

This copy applies to the signed-out `/` landing route and its current
Klassrumskartan showcase plus authenticated-value preview.

Runtime sources:

- `frontend/apps/skriptoteket/src/views/HomeView.vue`
- `frontend/apps/skriptoteket/src/components/home/LandingFeaturedClassroom.vue`
- `frontend/apps/skriptoteket/src/components/home/LandingAuthenticatedPreview.vue`
- `frontend/apps/skriptoteket/src/views/HomeView.spec.ts`

Governance sources:

- `EPIC-32`
- `ST-32-08`
- `PR-0270`
- `MOCK-st-32-08-landing-authenticated-value-copy-alternatives`

## Approved Signed-Out Hero Copy

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

## Approved Klassrumskartan Showcase Copy

Section heading:

```text
Klassrumskartan
```

Description:

```text
Skapa salen, placera eleverna, spara som PDF eller för Excel. Som inloggad är alla dina klasser, grupperingar och klassrumsplaceringar sparade.
```

Action:

```text
Öppna appen
```

Step labels:

```text
I
Skapa salen

II
Placera eleverna

III
Exportera
```

Accessibility label:

```text
Tre steg i Klassrumskartan
```

## Approved Authenticated-Value Preview Copy

Section heading:

```text
Mer när du loggar in
```

Lead:

```text
Få tillgång till fler appar och arbetsverktyg. Du kan också ge förslag på nya appar som du anser skulle underlätta ditt arbete.
```

Rows:

```text
I
Fler färdiga lärarverktyg
Använd alla Skriptotekets appar och verktyg som finns tillgängliga.
Kräver konto

II
Dina förslag kan bli nya appar
Berätta vilka arbetsmoment du vill slippa göra för hand.
Kräver konto

III
Spara arbetet över tid
Kom tillbaka till klasser, filer, inställningar och placeringar.
Kräver konto
```

Footer actions:

```text
Logga in
Skapa konto
```

## Explicit Copy Decisions

- `PR-0270` selected the mockup's Alternative B direction.
- The final row I description is the product-owner tweak:
  `Använd alla Skriptotekets appar och verktyg som finns tillgängliga.`
- The landing page no longer presents the code editor as a signed-out ledger
  row.
- The authenticated-value preview does not use `Kräver ansökan` in the current
  landing copy.
- The step markers are Roman numerals: `I`, `II`, `III`.

## Change Policy

When public landing copy changes:

1. Update this reference in the same docs-as-code slice.
2. Update `HomeView.spec.ts` or more specific component tests to lock the new
   approved words.
3. Record whether the change affects `ST-32-07` hero/header hierarchy,
   `ST-32-08` below-the-fold showcase copy, or a new follow-up task.
4. Keep the signed-out copy short, conversational, teacher-facing, and free of
   implementation terms.
