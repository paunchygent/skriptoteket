---
type: story
id: ST-05-07
title: "Frontend stabilisering och modern CSS"
status: in_progress
owners: "agents"
created: 2025-12-17
epic: "EPIC-05"
acceptance_criteria:
  - "Given components.css, when parsed, then all CSS rules have matching braces"
  - "Given any single-column page, when rendered, then content width is consistent (42rem)"
  - "Given editor page on any modern browser, when CodeMirror loads, then layout is stable without collapse"
  - "Given dvh units, when on older browsers, then vh fallback prevents layout break"
---

## Context

Frontend-expert analys identifierade bräcklighet och inkonsistens i Skriptotekets CSS/JS-arkitektur. Denna story adresserar de mest kritiska problemen utan att introducera nya beroenden eller ramverk.

**Källa:** `.claude/repomix_packages/TASK-frontend-review.md` och `.claude/plans/vast-sprouting-locket.md`

## Tasks

### Kritiska (Prio 1-2)

- [x] ~~Fix saknad `}` i `components.css`~~ - **FALSE POSITIVE** (CSS är korrekt balanserad)
  - Verifierat: `src/skriptoteket/web/static/css/app/components.css` har 58 `{` och 58 `}` och `.huleedu-toast-container` stängs korrekt (`src/skriptoteket/web/static/css/app/components.css:261` + `src/skriptoteket/web/static/css/app/components.css:271`).
- [ ] Lägg till `--huleedu-content-width` (app-policy) som alias till 42rem
  - Obs: 42rem finns redan som `--huleedu-max-width-2xl` i `src/skriptoteket/web/static/css/huleedu-design-tokens.css:169`.
  - Föreslagen ändring: definiera `--huleedu-content-width: var(--huleedu-max-width-2xl);` i `src/skriptoteket/web/static/css/app/utilities.css` nära panel-sektionen.
- [ ] Uppdatera `.huleedu-panel` att använda `--huleedu-content-width`
  - Nuvarande: `max-width: var(--huleedu-max-width-2xl)` + `margin-left/right` (`src/skriptoteket/web/static/css/app/utilities.css:55`–`61`).
  - Föreslagen: `max-width: var(--huleedu-content-width); margin-inline: auto;`.

### Panel/Card-bredd (Prio 3)

- [ ] Migrera `login.html` till `.huleedu-panel`
- [ ] Migrera `home.html` till `.huleedu-panel`
- [ ] Migrera `error.html` till `.huleedu-panel` (idag `huleedu-max-w-md`)
- [ ] Verifiera/åtgärda återstående single-column sidor som saknar `.huleedu-panel`
  - Saknar panel idag (bredare än 42rem via `.huleedu-main`): `src/skriptoteket/web/templates/my_runs/detail.html` och `src/skriptoteket/web/templates/suggestions_review_detail.html`.
    - `src/skriptoteket/web/templates/my_runs/detail.html:3` saknar wrapper runt innehållet → lägg till `.huleedu-panel`.
    - `src/skriptoteket/web/templates/suggestions_review_detail.html:3` använder `huleedu-card` utan panel → lägg till `.huleedu-panel`.
  - Redan panel (42rem via `.huleedu-panel`): `src/skriptoteket/web/templates/browse_professions.html:3`, `src/skriptoteket/web/templates/browse_categories.html:3`, `src/skriptoteket/web/templates/browse_tools.html:3`, `src/skriptoteket/web/templates/my_tools.html:3`, `src/skriptoteket/web/templates/admin_tools.html:3`, `src/skriptoteket/web/templates/suggestions_new.html:3`, `src/skriptoteket/web/templates/suggestions_review_queue.html:3`, `src/skriptoteket/web/templates/tools/run.html:3`, `src/skriptoteket/web/templates/tools/result.html:3`.

### Layout-robusthet (Prio 4-5)

- [ ] Lägg till `dvh` fallback: `height: 100vh; height: 100dvh;` i layout.css
  - Endast `dvh` hittas i `src/skriptoteket/web/static/css/app/layout.css:9`–`18` (ingen `vh` fallback idag).
- [ ] Refaktorera editorns interna layout (CodeMirror + toolbar + run-result) till stabil höjdmodell
  - Nuvarande 2-kolumn grid finns redan (`src/skriptoteket/web/static/css/app/editor.css:57`–`77`), men code-card är flex med “växer, krymper inte” (`flex: 1 0 auto`) och editor har `min-height: 500px` (`src/skriptoteket/web/static/css/app/editor.css:131`–`162`).
  - Run-result expanderar utan scrollcap (`max-height: none; overflow: visible`) (`src/skriptoteket/web/static/css/app/editor.css:210`–`218`).
  - Mål: tydliga scroll-ansvar + `min-height: 0` där relevant + run-result ska inte kunna “trycka sönder” editorn.
- [ ] Uppdatera `src/skriptoteket/web/templates/admin/script_editor.html` för den nya layouten
  - Nuvarande struktur: textarea → toolbar → `#run-result` i samma card (`src/skriptoteket/web/templates/admin/script_editor.html:36`–`96`).

### Modern CSS (Prio 6+, valfritt)

- [ ] Lägg till `@supports` för progressiv förbättring där relevant
- [ ] Introducera `clamp()` för fluid typography
- [ ] Byt `setTimeout` → `ResizeObserver` för CodeMirror refresh i app.js
  - Nuvarande debounce refresh: `setTimeout(..., 50)` i `scheduleAllEditorsRefresh()` (`src/skriptoteket/web/static/js/app.js:139`–`152`) triggas på `htmx:afterSwap`, `htmx:afterSettle` och `resize` (`src/skriptoteket/web/static/js/app.js:234`–`247`).

## Filer att modifiera

```
src/skriptoteket/web/static/css/app/components.css     # No changes needed (false positive)
src/skriptoteket/web/static/css/app/utilities.css      # Content-width token
src/skriptoteket/web/static/css/app/layout.css         # dvh fallback
src/skriptoteket/web/static/css/app/editor.css         # Grid areas refactor
src/skriptoteket/web/templates/login.html              # Use .huleedu-panel
src/skriptoteket/web/templates/home.html               # Use .huleedu-panel
src/skriptoteket/web/templates/error.html              # Use .huleedu-panel
src/skriptoteket/web/templates/my_runs/detail.html     # Consider wrapping in .huleedu-panel (consistency)
src/skriptoteket/web/templates/suggestions_review_detail.html # Consider .huleedu-panel (single-column consistency)
src/skriptoteket/web/templates/admin/script_editor.html # Updated grid classes
src/skriptoteket/web/static/js/app.js                  # ResizeObserver (optional)
```

## Implementation Notes

### 2025-12-17: CSS Brace Bug - FALSE POSITIVE

**Ursprunglig rapport:** Frontend-expert rapporterade att `.huleedu-toast-container` i `components.css` saknade closing brace `}`.

**Verifikation:** Vid granskning av faktiska filen konstaterades att:
- CSS-filen har 58 opening braces och 58 closing braces (balanserad)
- `.huleedu-toast-container`-blocket är korrekt avslutat på rad 271 (`src/skriptoteket/web/static/css/app/components.css:271`)
- `.huleedu-toast`-regeln börjar korrekt på rad 273 (`src/skriptoteket/web/static/css/app/components.css:273`)

**Slutsats:** Buggen existerar INTE. Repomix-paketet hade troligen trunkerat eller korrumperat innehållet vid export. Frontend-expertens analys baserades på felaktig data.

**Åtgärd:** Markerad som icke-applicerbar. Nästa session ska fokusera på de verkliga problemen:
- Panel-bredd inkonsistens
- Editor-layout bräcklighet
- dvh fallback

### 2025-12-17: Panel-bredd – verifierad inkonsistens

- `.huleedu-panel` ger 42rem via `--huleedu-max-width-2xl` (`src/skriptoteket/web/static/css/app/utilities.css:55`–`61`, token i `src/skriptoteket/web/static/css/huleedu-design-tokens.css:169`).
- `login.html`, `home.html`, `error.html` använder istället `huleedu-max-w-md huleedu-mx-auto` (28rem) (`src/skriptoteket/web/templates/login.html:3`, `src/skriptoteket/web/templates/home.html:3`, `src/skriptoteket/web/templates/error.html:3`).

### 2025-12-17: dvh – verifierad utan fallback

- `src/skriptoteket/web/static/css/app/layout.css` använder `100dvh` utan `100vh` fallback (`src/skriptoteket/web/static/css/app/layout.css:9`–`18`).

### 2025-12-17: Editor – nuvarande layout och riskpunkter

- Sida: `huleedu-main-fluid huleedu-editor-page` låser page-scroll och kräver stabila inre scroll-containers (`src/skriptoteket/web/static/css/app/editor.css:49`–`55`).
- Vänsterkolumn scrollar (`overflow-y: auto`) och code-card är flex med `flex: 1 0 auto` + editor `min-height: 500px` → tenderar att inte krympa (`src/skriptoteket/web/static/css/app/editor.css:119`–`162`).
- Run-result saknar scrollcap (`max-height: none; overflow: visible`) och ligger i samma card som editorn (`src/skriptoteket/web/static/css/app/editor.css:210`–`218`, `src/skriptoteket/web/templates/admin/script_editor.html:36`–`96`).
- CodeMirror refresh sker via event + debounce `setTimeout` (`src/skriptoteket/web/static/js/app.js:139`–`152`, `src/skriptoteket/web/static/js/app.js:234`–`247`).

### Avvisade alternativ

Följande alternativ utvärderades av frontend-expert och avvisades:

1. **Vue + Vite SPA för editor** - Bryter mot "inga externa beroenden", skapar två parallella paradigm
2. **Alpine.js hybrid** - Introducerar ytterligare JS-ramverk utan tillräcklig vinst
3. **@layer för cascade-kontroll** - Browser-support saknas i baseline (Safari 15+)

### Browser-baseline

Stödjer: Safari 15+, Chrome 90+, Firefox 90+

**Säkra moderna features:**
- `gap` i flexbox
- `aspect-ratio`
- `clamp()`
- Logical properties (`margin-inline`, `padding-block`)

**Undvik (saknar support):**
- `@layer`
- Container Queries
- `:has()` selector

## Nästa session

Nästa session ska:

1. Implementera panel-bredd-unifiering (minst: login/home/error → `.huleedu-panel`)
2. Implementera `vh` fallback för `dvh` i `layout.css`
3. Implementera editor-stabilisering (inre layout + scroll + CodeMirror refresh)
4. Live-check: verifiera editor-sidan efter ändringar (session rule) och logga i `.agent/handoff.md`

## Exakta patch-förslag (för nästa session)

### A) `utilities.css`: content-width token + panel

Plats: nära `.huleedu-panel` (`src/skriptoteket/web/static/css/app/utilities.css:55`).

```css
:root {
  --huleedu-content-width: var(--huleedu-max-width-2xl); /* 42rem */
}

.huleedu-panel {
  width: 100%;
  max-width: var(--huleedu-content-width);
  margin-inline: auto;
}
```

### B) `login.html`, `home.html`, `error.html`: byt till `.huleedu-panel`

- `src/skriptoteket/web/templates/login.html:3`
- `src/skriptoteket/web/templates/home.html:3`
- `src/skriptoteket/web/templates/error.html:3`

Byt `huleedu-max-w-md huleedu-mx-auto` → `huleedu-panel` (mönster finns redan i flera templates).

### C) `layout.css`: dvh fallback-stapling

Plats: `.huleedu-frame` (`src/skriptoteket/web/static/css/app/layout.css:5`–`18`).

```css
.huleedu-frame {
  min-height: 100vh;
  height: 100vh;
  min-height: 100dvh;
  height: 100dvh;
}

@media (min-width: 768px) {
  .huleedu-frame {
    min-height: calc(100vh - var(--huleedu-space-8));
    height: calc(100vh - var(--huleedu-space-8));
    min-height: calc(100dvh - var(--huleedu-space-8));
    height: calc(100dvh - var(--huleedu-space-8));
  }
}
```

### D) Editor: förslag på riktning (utan full diff här)

- Flytta/ändra layout i `src/skriptoteket/web/static/css/app/editor.css` så att editorn kan krympa (`min-height: 0`) och att run-result får scrollcap (t.ex. `max-height` + `overflow: auto`) istället för att expandera obegränsat (`src/skriptoteket/web/static/css/app/editor.css:131`–`218`).
- Ersätt “event + setTimeout” refresh med ResizeObserver på wrappern (för att decoupla från HTMX timing) i `src/skriptoteket/web/static/js/app.js` runt `scheduleAllEditorsRefresh()` (`src/skriptoteket/web/static/js/app.js:139`–`152`).

### E) Single-column sidor som saknar `.huleedu-panel`

`my_runs/detail.html` (idag blir innehållet bredare än 42rem eftersom `.huleedu-main` är 6xl):

```html
{% block content %}
  <div class="huleedu-panel">
    <div class="huleedu-mb-4">
      <a class="huleedu-link" href="/browse">← Tillbaka till katalog</a>
    </div>
    {% include "tools/partials/run_result.html" %}
  </div>
{% endblock %}
```

`suggestions_review_detail.html` (single-column admin-detaljsida):

- Byt toppnivå från `<div class="huleedu-card">` till `<div class="huleedu-card huleedu-panel">` (`src/skriptoteket/web/templates/suggestions_review_detail.html:3`).
