---
type: pr
id: PR-0010
title: "Editor save/restore UX clarity (naming, availability, last restore source)"
status: ready
owners: "agents"
created: 2026-01-08
updated: 2026-01-08
stories: []
tags: ["frontend", "editor", "ux"]
acceptance_criteria:
  - "Versionlistan skiljer tydligt på serverversioner och lokala återställningspunkter och visar inte autosparade debounce-punkter."
  - "UI visar vilken arbetsversion som är aktuell och vilken återställningspunkt som senast användes (lokal vs server)."
  - "Benämningar och hjälpcopy för spar/återställ är begripliga för icke-tekniska användare."
  - "Undo/redo (återställ senaste ändring) kommuniceras som återhämtning, inte som sparade versioner."
---

## Problem

Spar- och återställningsytorna blandar serverversioner, lokala checkpoints och autosparade debounce-punkter. Det är svårt
för användaren att förstå vilken arbetsversion som är aktiv, vad som senast återställdes och varför vissa punkter finns.

## Goal

Skapa en tydlig och konsekvent UX för spar/återställ:
- Separera serverversioner från lokala återställningspunkter.
- Dölja autosparade debounce-punkter från listan (de används endast för automatisk återställning).
- Visa vilken återställningspunkt som senast användes och om den var lokal eller serverbaserad.

## Non-goals

- Ändra backend-logik för versionering eller checkpoints.
- Ändra datamodell för working copy.
- Implementera nya typer av versioner i databasen.
- Implementera global Tillbaka-länk i fokusläge (ska visas på alla vyer utom `/`; hanteras i separat PR).

## Implementation plan

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

## Test plan

- FE: uppdatera/addera Vitest för working copy/restore UI (om aktuellt).
- Manuell: öppna editor, verifiera separata listor + senaste återställningskälla och att autosparade punkter inte syns.

## Rollback plan

- Revertera PR-0010; ingen datamodell ändras.
