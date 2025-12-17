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
- [ ] Lägg till `--huleedu-content-width: 42rem` i utilities.css
- [ ] Uppdatera `.huleedu-panel` att använda content-width token

### Panel/Card-bredd (Prio 3)

- [ ] Migrera `login.html` till `.huleedu-panel`
- [ ] Migrera `home.html` till `.huleedu-panel`
- [ ] Verifiera konsekvent bredd på alla single-column sidor

### Layout-robusthet (Prio 4-5)

- [ ] Lägg till `dvh` fallback: `height: 100vh; height: 100dvh;` i layout.css
- [ ] Refaktorera editor-layout till CSS Grid med `grid-template-areas`
- [ ] Uppdatera `script_editor.html` med nya grid-klasser

### Modern CSS (Prio 6+, valfritt)

- [ ] Lägg till `@supports` för progressiv förbättring där relevant
- [ ] Introducera `clamp()` för fluid typography
- [ ] Byt `setTimeout` → `ResizeObserver` för CodeMirror refresh i app.js

## Filer att modifiera

```
src/skriptoteket/web/static/css/app/components.css     # No changes needed (false positive)
src/skriptoteket/web/static/css/app/utilities.css      # Content-width token
src/skriptoteket/web/static/css/app/layout.css         # dvh fallback
src/skriptoteket/web/static/css/app/editor.css         # Grid areas refactor
src/skriptoteket/web/templates/login.html              # Use .huleedu-panel
src/skriptoteket/web/templates/home.html               # Use .huleedu-panel
src/skriptoteket/web/templates/admin/script_editor.html # Updated grid classes
src/skriptoteket/web/static/js/app.js                  # ResizeObserver (optional)
```

## Implementation Notes

### 2025-12-17: CSS Brace Bug - FALSE POSITIVE

**Ursprunglig rapport:** Frontend-expert rapporterade att `.huleedu-toast-container` i `components.css` saknade closing brace `}`.

**Verifikation:** Vid granskning av faktiska filen konstaterades att:
- CSS-filen har 58 opening braces och 58 closing braces (balanserad)
- `.huleedu-toast-container`-blocket är korrekt avslutat på rad 269
- `.huleedu-toast`-regeln börjar korrekt på rad 271

**Slutsats:** Buggen existerar INTE. Repomix-paketet hade troligen trunkerat eller korrumperat innehållet vid export. Frontend-expertens analys baserades på felaktig data.

**Åtgärd:** Markerad som icke-applicerbar. Nästa session ska fokusera på de verkliga problemen:
- Panel-bredd inkonsistens
- Editor-layout bräcklighet
- dvh fallback

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

1. Validera att CSS-buggen är fixad (toasts renderas korrekt)
2. Implementera panel-bredd-unifiering med `--huleedu-content-width`
3. Fylla i exakta patches för editor-layout refaktoring
4. Testa layout på olika browsers/viewports
