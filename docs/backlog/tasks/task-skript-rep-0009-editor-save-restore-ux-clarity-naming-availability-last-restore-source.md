---
type: task
id: TASK-SKRIPT-REP-0009
title: Editor save/restore UX clarity (naming, availability, last restore source)
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: ready
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
task_kind: repository
acceptance_criteria:
- Versionlistan skiljer tydligt på serverversioner och lokala återställningspunkter
  och visar inte autosparade debounce-punkter.
- UI visar vilken arbetsversion som är aktuell och vilken återställningspunkt som
  senast användes (lokal vs server).
- Benämningar och hjälpcopy för spar/återställ är begripliga för icke-tekniska användare.
- Undo/redo (återställ senaste ändring) kommuniceras som återhämtning, inte som sparade
  versioner.
---

## Context

Source: `docs/backlog/prs/pr-0010-editor-save-restore-ux-clarity.md`. Editor save/restore UX clarity (naming, availability, last restore source).

Spar- och återställningsytorna blandar serverversioner, lokala checkpoints och autosparade debounce-punkter. Det är svårt för användaren att förstå vilken arbetsversion som är aktiv, vad som senast återställdes och varför vissa punkter finns. Skapa en tydlig och konsekvent UX för spar/återställ: - Separera serverversioner från lokala återställningspunkter. - Dölja autosparade debounce-punkter från listan (de används endast för automatisk återställning). - Visa vilken återställningspunkt som senast användes och om den var lokal eller serverbaserad. - Ändra backend-logik för versionering eller checkpoints. - Ändra datamodell för working copy. - Implementera nya typer av versioner i databasen.

## Impact And Escalation

The source task remains bounded to its repository-owned surface; product behavior or unapproved scope escalates to the parent story/epic.

## Decision And Assumption Ledger

| ID | Type | Status | Question/Assumption | Recommendation/Decision | Source |
| --- | --- | --- | --- | --- | --- |
| MIG-TASK-SKRIPT-REP-0009 | migration | closed | How is source meaning preserved? | Preserve the source task contract, current relationships, and status while changing identity only. | ST-SKILL-08-06; TASK-SKRIPT-REP-0003 |

## Contract Inputs

- Source task/PR and audit-approved migration authority.
- Current story or repository relationship in candidate frontmatter.

## Plan

Execute only the bounded plan represented by the source record; do not add scope during migration.

## Implementation Steps

1. Preserve the source implementation or proof sequence.
2. Verify current relationships and focused evidence at task closeout.

## Proof

The source proof obligations are retained as historical evidence below; no execution proof is asserted by this candidate.

## Validation

Run the task-selected focused gates and repository docs validation after parent integration.

## Stop Conditions

Stop for missing authority, unresolved identity/relationship, terminal ancestry, or scope expansion.

## Lessons Learned

The source material is retained verbatim below for migration fidelity.

## Notes

### Source evidence

### Problem

Spar- och återställningsytorna blandar serverversioner, lokala checkpoints och autosparade debounce-punkter. Det är svårt
för användaren att förstå vilken arbetsversion som är aktiv, vad som senast återställdes och varför vissa punkter finns.

### Goal

Skapa en tydlig och konsekvent UX för spar/återställ:
- Separera serverversioner från lokala återställningspunkter.
- Dölja autosparade debounce-punkter från listan (de används endast för automatisk återställning).
- Visa vilken återställningspunkt som senast användes och om den var lokal eller serverbaserad.

### Non-goals

- Ändra backend-logik för versionering eller checkpoints.
- Ändra datamodell för working copy.
- Implementera nya typer av versioner i databasen.
- Implementera global Tillbaka-länk i fokusläge (ska visas på alla vyer utom `/`; hanteras i separat PR).

### Implementation plan

1) **Namngivning och copy**
   - Byt etiketter i versionlistor och återställningsytor så de matchar användarens mentala modell.

2) **Avgränsa listor**
   - Visa endast serverversioner + manuella lokala checkpoints.
   - Autosparade debounce-punkter används enbart för automatisk återställning och syns inte i listan.

3) **Källa för senaste återställning**
   - Lägg till visning av senaste återställningskälla (serverversion eller lokal checkpoint) i editor-UI.

4) **Undo/redo-kommunikation**
   - Tydliggör att debounce-punkter används för återhämtning (återställ senaste ändring), inte som sparade versioner.

5) **UI-städning**
   - Göra listor/knappar kompaktare och mer IDE-lika.

### Test plan

- FE: uppdatera/addera Vitest för working copy/restore UI (om aktuellt).
- Manuell: öppna editor, verifiera separata listor + senaste återställningskälla och att autosparade punkter inte syns.

### Rollback plan

- Revertera PR-0010; ingen datamodell ändras.

## Readiness

No specialist approval is asserted; parent review remains required.

## Closeout

No closeout evidence is asserted in this candidate.
