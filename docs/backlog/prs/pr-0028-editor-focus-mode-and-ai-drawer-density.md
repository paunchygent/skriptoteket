---
type: pr
id: PR-0028
title: "Editor focus mode + AI drawer density + consent relocation"
status: done
owners: "agents"
created: 2026-01-13
updated: 2026-01-14
stories: []
tags: ["frontend", "backend", "editor", "ai", "ux", "performance", "profile"]
links: ["EPIC-14", "EPIC-15"]
acceptance_criteria:
  - "I fokusläge använder editorn maximal yta (utan onödig padding/gap) och chat-drawer kan visa långa AI-svar utan onödigt scroll."
  - "Chat-drawer är tätare: historiken fyller vertikalt utrymme, composer är förankrad i botten och kontroller är omstrukturerade för mindre dödutrymme."
  - "Remote-fallback samtycke hanteras i användarprofil (persistens på server) och kan ändras där."
  - "Vid första remote-fallback-försöket (om valet är unset) frågar UI efter ett explicit val (aktivera/stäng av) och sparar svaret; om prompten stängs behandlas det som ett nej för just den begäran (ingen remote request)."
  - "Profilens AI-inställningar använder samma kanoniska design som verktygslistan/editor: panel-primitives (`border border-navy bg-white shadow-brutal-sm` / `panel-inset*`) och knapp-primitives (`btn-primary`/`btn-ghost`) utan ad-hoc styling."
  - "Composer har ett tydligt Chat/Redigera-läge (toggle). Sänd-ikon (t.ex. pappersflygplan) finns i inputens nedre högra hörn och Enter skickar (Shift+Enter ny rad)."
  - "Inga regressions i editorflöden (källkod/diff/metadata/testkör). Playwright-smokes tar screenshots och asserts för layout + interaktion."
  - "`pdm run fe-test` passerar (och `pdm run fe-lint`/`pdm run fe-type-check` om konfigurerat)."
---

## Problem

Tool editor är en komplex “app i appen” där layoutval får stor påverkan på upplevd prestanda och användbarhet.
I fokusläge och i AI-drawer offras mycket yta:

- Editorn använder inte maximal yta (padding/gap/sidoytor) trots fokusläge.
- Chat-drawer har mycket “dead space” och för lite effektiv yta för historik + lång AI-output.
- Remote-fallback samtycke ligger i direkt kontext i chatten, vilket tar yta och blandar “inställning” med “uppgift”.
- Composer har flera knappar och dubbel-path (Skicka / Föreslå ändringar) som tar yta och gör interaktion tyngre.

## Goal

- Maximera editor-yta i fokusläge utan att bryta design tokens eller layoutkontrakt.
- Göra chat-drawer tätare och mer IDE-lik (historia fyller, composer förankrad, färre divider/padding).
- Flytta remote-fallback samtycke till profil (serverpersistens) och be om explicit val vid första remote-fallback-försöket om användaren inte valt (unset).
- Enhetlig composer: ett läge i taget (Chat vs Redigera) med snabb inmatning (Enter) och diskret sänd-ikon.
- Hålla initial-load snabb: fortsätt lazy-load av tunga editor/AI-delar och undvik nya “god components”.

## Non-goals

- Ändra AI-promptar, budgetar, provider-urval eller backend-LLM-pipeline.
- Införa ett nytt design-system eller nya globala CSS-entrypoints.
- Ändra editor-routes eller workflowregler (publicering/granskning) utöver UI-ytor.

## Modularisering + återanvändning (performance-first)

Principer:

1. **Layout-kontrakt i ett ställe**: definiera “EditorShell”/layout-API (höjd, padding, kolumner) så paneler inte blir content-sized.
2. **Chat-drawer som tre delar**: Header (stateless) + MessageList (scroll) + Composer (input + actions). Varje del har en tydlig ägare.
3. **Inställningar flyttas ut ur uppgiften**: remote-fallback samtycke är en profilinställning; chatten visar endast status + kontextuella meddelanden.
4. **Kodsplit för tunga vyer**: diff/test/metadata och AI-drawer ska fortsätta vara lazy där det är möjligt utan att skapa race conditions.
5. **Verifiera visuellt via Playwright**: varje layoutändring måste få en screenshot + enkel bounding-box assert.
6. **Kanonisk UI**: profilpaneler/knappar återanvänder SPA-primitives (`page-*`, `btn-*`, `panel-inset*`) och token-driven spacing.

## Implementation plan (stegvis, mergebar)

1) **Fokusläge: fyll ytan**
   - Reducera padding/gap i editor-route när `focusMode=true` (utan att påverka andra vyer).
   - Säkerställ att editor-ytan använder full höjd under AuthTopBar (konsistent “height chain”).
   - Skapa en tydlig plats för editor-specifika layout-tokens (t.ex. CSS-variabler eller klass-variant).

2) **Chat-drawer: minska dödutrymme**
   - Refaktorera chat-drawer till `ChatHeader` + `ChatHistory` + `ChatComposer`.
   - Gör historikytan till `flex-1 min-h-0 overflow-y-auto` och minska vertikal padding/dividers.
   - Flytta sekundära kontroller (Ny chatt / status) till en liten tool-row i composer så historiken får maximal yta.

3) **Remote-fallback samtycke i profil + “first remote attempt” prompt (backend + frontend)**
   - Backend: inför en serverpersistad inställning (tri-state: unset/allow/deny) kopplad till user.
   - API: exponera via `/api/v1/auth/me` eller separat endpoint under profil.
   - Frontend: `useAiStore` hydraterar från server och faller tillbaka till localStorage endast som migration.
   - Chat: ta bort checkboxen från chat-drawer.
   - Vid remote-fallback-försök:
     - `allow`: fortsätt och skicka remote request.
     - `deny`: visa tydligt meddelande och skicka inte remote request.
     - `unset`: visa en liten prompt med “Aktivera”/“Stäng av” (med länk till Profil); spara val vid klick. Om prompten stängs behandlas det som “stäng av” för denna begäran (ingen remote request), men inställningen förblir `unset`.

4) **Composer: Chat/Redigera toggle + sänd-ikon i input**
   - Byt “Skicka”/“Föreslå ändringar” till ett läge: `Chat` eller `Redigera`.
   - Enter skickar; Shift+Enter ny rad. Sänd-ikon (aria-label) i textarea (nedre höger).
   - Återanvänd befintliga `btn-*` primitives och token spacing. Ingen Tailwind default palette.

5) **Performance gates**
   - Bekräfta att nya split-punkter inte drar in tunga moduler i initial chunk.
   - Vid behov: ytterligare `defineAsyncComponent`/dynamic import för edit-ops/diff/test.

6) **Verifiering + docs-as-code**
   - Uppdatera Playwright smoke(s) med nya assertions/screenshots för fokusläge + chat-drawer.
   - Uppdatera `.agent/handoff.md` med exakta commands + artifacts (inga påståenden utan screenshot).

## Test plan

- FE: `pdm run fe-test` (+ `pdm run fe-lint`/`pdm run fe-type-check` om relevanta).
- Playwright: `BASE_URL=http://localhost:5173 pdm run ui-editor-smoke` (ska producera artifacts + screenshots).
- Manuell: öppna tool editor i fokusläge och verifiera chat-drawer (långa svar, toggles, Enter/Shift+Enter).

## Rollback plan

- Revertera PR-0028; migreringar (om införda) måste också rullas tillbaka via Alembic.

## Files touched (plan + checklist)

Detta avsnitt måste uppdateras efter varje delsteg (1-6) nedan. När alla checkboxar är ikryssade är PR:en klar.

### Planned files

#### Layout (focus mode + editor shell)

- `frontend/apps/skriptoteket/src/components/layout/AuthLayout.vue`
  - Editor-route + fokusläge: minska padding/gap och låt editor fylla ytan.
- `frontend/apps/skriptoteket/src/assets/main.css`
  - Vid behov: editor-route layout-helpers som är token-drivna (inga nya global-entrypoints).
- `frontend/apps/skriptoteket/src/views/admin/ScriptEditorView.vue`
  - Säkerställ “height chain” och att editor är flex-1 i route-stage.

#### Chat drawer density + composer UX

- `frontend/apps/skriptoteket/src/components/editor/ChatDrawer.vue`
  - Split: header/history/composer; reducerad padding/dividers; tydlig layout.
- `frontend/apps/skriptoteket/src/components/editor/ChatComposer.vue` (new)
  - Input + send-icon + Chat/Redigera toggle (a11y).
- `frontend/apps/skriptoteket/src/components/editor/ChatMessageList.vue` (new)
  - Scrollcontainer + message rendering.
- `frontend/apps/skriptoteket/src/components/editor/EditorWorkspaceDrawers.vue`
  - Wiring för nya chat-subcomponents (fortsatt lazy-load).

#### Consent relocation (profile + backend)

- Backend (tbd exact paths):
  - `src/skriptoteket/...` user profile model + settings field
  - `src/skriptoteket/web/api/...` endpoint för att läsa/skriva inställningen
  - `migrations/...` Alembic migration
- Frontend:
  - `frontend/apps/skriptoteket/src/stores/ai.ts` (eller motsv.) hydrering från server
  - `frontend/apps/skriptoteket/src/views/ProfileView.vue` profilinställning UI (ny/uppdaterad)
  - `frontend/apps/skriptoteket/src/components/profile/ProfileDisplay.vue` visa AI-inställning som panel i Profil
  - `frontend/apps/skriptoteket/src/components/profile/ProfileAiSettingsPanel.vue` (new) AI-inställningar (remote-fallback aktiverat/avstängt)
  - Design rule: använd panel/knapp-primitives från `frontend/apps/skriptoteket/src/assets/main.css` (ingen ny CSS entrypoint; undvik Tailwind default palette).

#### Playwright / verification

- `scripts/playwright_ui_editor_smoke.py`
  - Lägg till fokusläge-screenshot + chat-drawer density asserts.

### Progress checklist

- [x] 1. Fokusläge: editor fyller ytan och padding/gap är reducerat (Playwright screenshot + manuell kontroll).
- [x] 2. Chat-drawer densitet: historik fyller höjden, composer i botten, mindre dödutrymme (screenshots + asserts).
- [x] 3. Flytta remote-fallback samtycke till profil (serverpersistens + API), ta bort checkbox i chat-drawer, och lägg till “first remote attempt” prompt när valet är unset.
- [x] 4. Composer: Chat/Redigera toggle + sänd-ikon i input; Enter skickar, Shift+Enter ny rad (a11y).
- [x] 5. Performance: verifiera att initial editor-load inte regresserar (lazy-load där relevant).
- [x] 6. Quality gates + handoff: `pdm run fe-type-check`, `pdm run fe-test` och Playwright-smokes; uppdatera `.agent/handoff.md` med artifacts.

### Verification (2026-01-14)

- FE: `pdm run fe-type-check`, `pdm run fe-test`, `pdm run fe-build`
- Playwright: `BASE_URL=http://localhost:5173 pdm run ui-smoke`, `BASE_URL=http://localhost:5173 pdm run ui-editor-smoke`
- Artifacts: `.artifacts/ui-smoke/profile-ai-settings-desktop.png`, `.artifacts/ui-editor-smoke/editor-loaded.png`
