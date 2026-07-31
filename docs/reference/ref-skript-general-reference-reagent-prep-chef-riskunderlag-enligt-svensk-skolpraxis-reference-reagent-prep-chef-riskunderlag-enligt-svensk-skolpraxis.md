---
type: reference
id: REF-SKRIPT-GENERAL-reference-reagent-prep-chef-riskunderlag-enligt-svensk-skolpraxis
title: 'Reference: Reagent Prep Chef — riskunderlag enligt svensk skolpraxis'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: active
reference_kind: general
retired_ids:
- REF-reagent-prep-chef-riskunderlag-skolpraxis
summary: 'Reference: Reagent Prep Chef — riskunderlag enligt svensk skolpraxis'
---

## Overview

Source: `docs/reference/ref-reagent-prep-chef-riskunderlag-skolpraxis.md`. Reference: Reagent Prep Chef — riskunderlag enligt svensk skolpraxis.

Det här underlaget anger miniminivån för vilka fält Reagent Prep Chef behöver för kemisk riskdokumentation i skolkontext, med namngivna källor från Arbetsmiljöverket och Skolverket. Målet är att: - vara källstyrd (inte "best guess"), - minska onödig dokumentation för lärare, - hålla backend som enda källa för required/optional, - undvika juridisk överclaim i dokumentnamngivning. 1. **AFS 2023:1** (systematiskt arbetsmiljöarbete), 11 §: - riskbedömning ska göras och dokumenteras skriftligt, - dokumentationen ska visa vilka risker som finns och om de är allvarliga. - URL: https://www.av.se/globalassets/filer/publikationer/foreskrifter/systematiskt-arbetsmiljoarbete-grundlaggande-skyldigheter-f

## Facts And Semantics

This reference retains durable facts, terminology, evidence, and interpretation.

### Source evidence

### Overview

Det här underlaget anger miniminivån för vilka fält Reagent Prep Chef behöver för kemisk riskdokumentation i
skolkontext, med namngivna källor från Arbetsmiljöverket och Skolverket.

Målet är att:

- vara källstyrd (inte "best guess"),
- minska onödig dokumentation för lärare,
- hålla backend som enda källa för required/optional,
- undvika juridisk överclaim i dokumentnamngivning.

### Named sources

### Arbetsmiljöverket (gällande föreskrifter)

1. **AFS 2023:1** (systematiskt arbetsmiljöarbete), 11 §:
   - riskbedömning ska göras och dokumenteras skriftligt,
   - dokumentationen ska visa vilka risker som finns och om de är allvarliga.
   - URL: https://www.av.se/globalassets/filer/publikationer/foreskrifter/systematiskt-arbetsmiljoarbete-grundlaggande-skyldigheter-for-dig-med-arbetsgivaransvar-afs2023-1.pdf
2. **AFS 2023:10** (risker i arbetsmiljön), 7 kap. 12 §:
   - dokumentationen för kemiska riskbedömningar ska ange omfattning/situation, skyddsåtgärder, åtgärdsansvar,
     deltagare, nästa planerade undersökning/riskbedömning samt datum + ansvarig godkännare.
   - URL: https://www.av.se/globalassets/filer/publikationer/foreskrifter/konsoliderade-foreskrifter/risker-i-arbetsmiljon-afs2023-10-konsoliderad.pdf

### Skolverket (skolkontext och ansvar)

1. **Arbetsmiljön i skola och förskola**:
   - huvudmannen (arbetsgivaren) ansvarar för arbetsmiljön,
   - elever omfattas i huvudsak av arbetsmiljölagen från förskoleklass,
   - arbetsmiljöarbetet ska ske systematiskt.
   - URL: https://www.skolverket.se/larande-och-trygghet/trygghet-vardegrund-och-arbetsmiljo/arbetsmiljon-i-skola-och-forskola

### Decision checkpoint: “Riskbedömning” vs “Underlag till riskbedömning”

### Decision

Använd **“Underlag till riskbedömning”** för exporterad PDF och filnamn.

### Rationale

- AFS-läget lägger ansvar och godkännande på arbetsgivaren/huvudmannen.
- Appen producerar ett strukturerat, deterministiskt beslutsstöd men kan inte ensam stå för verksamhetens fulla
  arbetsmiljöansvar.
- Formuleringen "underlag" minskar risk för att lärare tolkar dokumentet som juridiskt komplett i alla situationer.

### Scope for naming

- Flödessteg i appen kan fortsatt heta **Riskbedömning** (igenkänning i lärararbetsflödet).
- Exporterad PDF, nedladdningsnamn och “save to vault”-filnamn använder **Underlag till riskbedömning**.

### Mapping: current field → keep/merge/drop

| current_field | source anchor | decision | why |
| --- | --- | --- | --- |
| `scope` | AFS 2023:10, 7 kap. 12 § p1–p2 | **keep (required)** | Måste beskriva vad/situation som riskbedömningen avser. |
| `location` | AFS 2023:10, 7 kap. 12 § p1 | **keep (optional)** | Hjälper i skolmiljö med flera salar/lab, men behövs inte som blockerande krav. |
| `participants` | AFS 2023:10, 7 kap. 12 § p7 | **keep (required)** | Vem som deltagit i undersökning/riskbedömning ska framgå. |
| `approver` | AFS 2023:10, 7 kap. 12 § p9 | **keep (required)** | Ansvarig person som godkänt dokumentet ska framgå. |
| `assessment_date` | AFS 2023:10, 7 kap. 12 § p9 | **keep (required)** | Datum för dokumentet krävs uttryckligen. |
| `next_review_date` | AFS 2023:10, 7 kap. 12 § p8 | **keep (required)** | Nästa planerade undersökning/riskbedömning ska framgå. |
| `local_routines` | AFS 2023:10, 7 kap. 12 § p3/p5/p6 | **keep (optional)** | Lokala rutiner kan förtydliga åtgärd/beredskap men bör inte blockera export. |

### Implementation implications

1. Backend definierar required/optional i en gemensam valideringsfunktion (single source of truth).
2. API returnerar `draft.export_gate.missing_context_fields`; SPA använder den för både gating och “saknas”-copy.
3. Exportering/sparning använder naming enligt beslutet ovan.

## Decisions And Interpretation

No implementation authority is created by this reference.
