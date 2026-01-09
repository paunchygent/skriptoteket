---
type: pr
id: PR-0011
title: "Editor modes + metadata mode + Kodskrivarassistent"
status: ready
owners: "agents"
created: 2026-01-08
updated: 2026-01-08
stories:
  - "ST-08-20"
tags: ["frontend", "editor", "ux"]
acceptance_criteria:
  - "Källkod/Diff/Metadata/Testkör är fasta lägen (toggles) i editorn; knapparna byter inte plats."
  - "Jämför är omdöpt till Diff och fungerar som läge oberoende av chattfönstret."
  - "Kodskrivarassisten är namngiven i toolbar och drawer, med uppdaterad copy enligt beslut."
  - "Fokusläge-toggle flyttas till top bar och behåller fast position; text ändras men placering gör inte det."
  - "Metadata-läget visar Verktygsinfo, Sökord (taxonomy rename), Instruktioner och Behörigheter samlat."
  - "Chatten öppnas default när editorn laddas och kan vara öppen i alla lägen."
  - "Testkör är ett eget läge i editorn (inte del av källkods-läget)."
  - "Indata- och Inställningsschema ligger sida vid sida, är kollapsbara, och Indata ligger till vänster."
  - "Tips/info-text under dropdowns flyttas till tooltips (schema + testkör)."
  - "Alla lägen fyller viewport-höjden utan layout-hopp; metadata-läget är mer kompakt utan onödig tom yta."
  - "Titel/sammanfattning/slug ligger som kompakt inline-rad i huvudytan (ingen separat header-panel)."
  - "Begär publicering/Publicera/Avslå ligger på samma rad som Spara och visas kompakt med tooltips för roll."
  - "Spara/Öppna är en enda dropdown-meny som samlar: spara arbetsversion, ändringssammanfattning, skapa lokal återställningspunkt och öppna historik."
  - "Workflow-knapparna ligger i den kompakta header-raden (inte i toolbar) och har enhetlig storlek utan hårda skuggor."
---

## Problem

Editor-ytan blandar lägen (källkod/jämför/metadata/testkör) med drawers och utilities. Knappar flyttar runt, vilket
bryter förutsägbarhet. Namnet "AI-chat" är otydligt och chatten saknar tydlig roll i redigeringsflödet. Schema- och
testkör-delarna tar för mycket plats och saknar kompakt, konsekvent layout.

## Goal

Skapa en tydlig, IDE-liknande mode-struktur:
- Fyra fasta lägen: **Källkod**, **Diff**, **Metadata**, **Testkör**.
- Chatten (Kodskrivarassisten) är en separat drawer som kan vara öppen i alla lägen.
- Fokusläge är ett globalt toggle i top bar.
- Schema-paneler är kompakta, side-by-side och kollapsbara; info flyttas till tooltips.

## Non-goals

- Ändra backend eller datamodell för versioner/checkpoints.
- Ändra autosave-logik (hanteras i PR-0010).
- Introducera nya UI-ramverk eller global CSS.

## Implementation plan

1) **Mode-toggles i toolbar**
   - Ersätt nuvarande jämför-knapp med "Diff"-toggle.
   - Lägg till Metadata-, Testkör- och Källkod-lägen i samma fasta grupp.

2) **Kodskrivarassistent**
   - Byt namn/copy i toolbar och drawer.
   - Chatten öppnas default vid editor-load.

3) **Fokusläge**
   - Flytta toggle till top bar och håll den på fast position.

4) **Metadata-läge**
   - Visa Verktygsinfo, Sökord (taxonomy rename), Instruktioner och Behörigheter i ett samlat läge.

5) **Schema-paneler (källkodsläget)**
   - Indata- och Inställningsschema sida vid sida, kollapsbara, Indata till vänster.
   - Flytta preset- och hjälptips till tooltips (inga beskrivningar under dropdowns).

6) **Testkör som läge**
   - Flytta Testkör kod till eget läge (inte del av källkodsflödet).
   - Flytta hjälptips under dropdowns till tooltips.

7) **UI-justeringar**
   - Knapphierarki och spacing hålls kompakt och konsekvent med IDE-känsla.
   - Alla lägen fyller viewport-höjden utan layout-hopp.
   - Titel/sammanfattning/slug flyttas in i huvudytan som kompakt kontextrad.
   - Spara/Öppna samlas i en dropdown-meny; ändringssammanfattning ligger i menyn.
   - Workflow-knappar flyttas till header-raden och får enhetlig storlek utan hård skugga.

## Test plan

- FE: uppdatera/addera tester för mode-toggles om de finns.
- Manuell: öppna editor, verifiera lägen + chat default + metadata-läge + testkör-läge och fokus-toggle i top bar.

## Rollback plan

- Revertera PR-0011; inga datamodeller ändras.
