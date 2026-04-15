# Frontend Review & Refactoring Task

**Datum:** 2025-12-17
**Kontext-paket:** `repomix-frontend-architecture-review.xml` (52,498 tokens, 42 filer)

---

## Problembeskrivning

Skriptotekets frontend har vuxit organiskt under flera iterationer och lider nu av:

### 1. Bräcklighet (Fragility)
- **CSS-moduler överlappar** - `buttons.css`, `components.css`, `utilities.css` har duplicerade concerns
- **Layout-hacks** - Editor-sidan använder komplex grid + flex + nested scroll som lätt går sönder
- **HTMX-beroenden** - CodeMirror-initialisering är hårt kopplad till HTMX-livscykeln (`htmx:load`, `htmx:afterSwap`, `htmx:afterSettle`)
- **Toast-systemet** är tre lager djupt: cookie → middleware → template → JS auto-dismiss

### 2. Brist på Kohesion (Lack of Cohesion)
- **JavaScript-monoliten** (`app.js`, 293 rader) blandar: CodeMirror-hantering, toast-dismiss, HTMX-hooks, fil-input-display, form-synkronisering
- **Template-duplikation** - `run_result.html` existerar i både `admin/partials/` och `tools/partials/` med minimal skillnad
- **Inkonsekvent spacing** - Mix av utility-klasser (`.huleedu-mt-4`) och inline styles
- **CSS-filer utan tydlig separation** - `forms.css` vs `components.css` gränsdragning är oklar

### 3. Specifika UI-problem
- CodeMirror-editorn kan "kollapsa" efter HTMX-swap om timing är fel
- Toast-container kan överlappa header på smal viewport
- File-input har haft synlighetsproblem (visat dubbelt, dolts fel)
- Scroll-beteende på editor-sidan är browser-beroende

---

## Nuvarande Arkitektur

### Tech Stack
- **Server**: FastAPI + Jinja2 (server-rendered HTML)
- **Interaktivitet**: HTMX för AJAX, vanilla JavaScript för resten
- **Styling**: CSS Custom Properties (design tokens) + modulär CSS
- **Editor**: CodeMirror (vendored, lazy-loaded)

### CSS-struktur
```
static/css/
├── huleedu-design-tokens.css    # Design system tokens (färg, typografi, spacing)
├── app.css                      # Entry point (@import av moduler)
└── app/
    ├── base.css                 # Reset, body, grid-background
    ├── layout.css               # Frame, header, main, sidebar
    ├── buttons.css              # Button variants och states
    ├── forms.css                # Inputs, textareas, file upload
    ├── components.css           # Cards, badges, lists, tables
    ├── editor.css               # CodeMirror theme + editor layout
    └── utilities.css            # Flex, stack, gap, margins, max-width
```

### JavaScript-struktur
```javascript
// app.js - En enda IIFE med allt
(function() {
  // 1. Vendor lazy-loading (CodeMirror CSS/JS)
  // 2. CodeMirror editor management
  // 3. HTMX event listeners (load, afterSwap, afterSettle, configRequest)
  // 4. Toast auto-dismiss med MutationObserver
  // 5. File input name display
  // 6. Form sync before submit
})();
```

### Template-hierarki
```
templates/
├── base.html                    # Root: header + main + toast container
├── [page].html                  # Full pages extending base
├── admin/
│   ├── script_editor.html       # Komplex två-kolumns editor
│   └── partials/                # HTMX fragments
├── tools/
│   ├── run.html                 # User tool execution
│   └── partials/                # HTMX fragments
└── partials/
    └── toast.html               # Reusable toast component
```

---

## Design System Specifikation

### Färgpalett
| Token | Värde | Användning |
|-------|-------|------------|
| `--huleedu-canvas` | `#F9F8F2` | Bakgrund (varm off-white) |
| `--huleedu-navy` | `#1C2E4A` | Primär text, borders, brutalist shadows |
| `--huleedu-burgundy` | `#6B1C2E` | CTA-knappar, accent |
| `--huleedu-success` | `#059669` | Lyckade operationer |
| `--huleedu-error` | `#DC2626` | Fel, varningar |

### Typografi
- **Sans**: IBM Plex Sans (body, UI)
- **Serif**: IBM Plex Serif (brand, rubriker vid behov)
- **Mono**: IBM Plex Mono (kod, editor)

### Spacing (4px-skala)
```css
--huleedu-space-1: 4px;
--huleedu-space-2: 8px;
--huleedu-space-4: 16px;
--huleedu-space-6: 24px;
--huleedu-space-8: 32px;
```

### Brutalist Signatur
- **Offset shadow**: `6px 6px 0px 0px var(--huleedu-navy)` på cards
- **Solid borders**: `1px solid var(--huleedu-navy)`
- **Minimal radius**: `2px` på knappar/inputs, `0` på cards

### Komponent-klasser (nuvarande)
| Klass | Beskrivning |
|-------|-------------|
| `.huleedu-btn` | Burgundy CTA-knapp |
| `.huleedu-btn-navy` | Navy funktionsknapp |
| `.huleedu-btn-secondary` | Outlined knapp |
| `.huleedu-card` | Card med brutalist shadow |
| `.huleedu-card-flat` | Card utan shadow |
| `.huleedu-panel` | Centrerad single-column container |
| `.huleedu-input` | Textfält |
| `.huleedu-label` | Form label |
| `.huleedu-badge` | Status-badges |
| `.huleedu-list` / `.huleedu-list-item` | Listor |
| `.huleedu-tool-row` | Tool-lista med actions |

---

## Målbild

### A. CSS-arkitektur
**Mål:** Tydlig separation, inga överlapp, förutsägbar cascade.

```
static/css/
├── huleedu-design-tokens.css    # ORÖRD - tokens endast
├── app.css                      # Entry point
└── app/
    ├── 00-reset.css             # Minimal reset
    ├── 01-base.css              # Body, typography defaults
    ├── 10-layout.css            # Frame, header, main (sidspecifika)
    ├── 20-components/
    │   ├── buttons.css          # Alla button-varianter
    │   ├── cards.css            # Card, card-flat, panel
    │   ├── forms.css            # Inputs, labels, errors, file-upload
    │   ├── lists.css            # List, list-item, tool-row
    │   ├── badges.css           # Badge, pill, status
    │   ├── toasts.css           # Toast container + toast styling
    │   └── editor.css           # CodeMirror integration
    └── 30-utilities.css         # ENDAST atomic utilities
```

**Principer:**
- Numrerade prefix = explicit cascade-ordning
- Komponenter i egen mapp = skalbar struktur
- Utilities = sista steget, inga component-styles

### B. JavaScript-modularisering
**Mål:** Separata concerns, testbar kod, lös koppling.

```javascript
// Förslag: ES modules (om browser-support tillåter) eller namespaced objekt

// toast.js - Toast management
const HuleToast = {
  init(container) { ... },
  show(message, type) { ... },
  autoDismiss(element, delay) { ... }
};

// codemirror-integration.js - Editor management
const HuleEditor = {
  editors: new Map(),
  init(textarea) { ... },
  syncToTextarea(editor) { ... },
  refreshAll() { ... },
  destroy(textarea) { ... }
};

// htmx-hooks.js - HTMX lifecycle management
const HuleHtmx = {
  init() { ... },  // Registrera alla listeners
};

// file-input.js - Custom file input
const HuleFileInput = {
  init(input) { ... }
};

// app.js - Orchestrator
document.addEventListener('DOMContentLoaded', () => {
  HuleToast.init(document.getElementById('toast-container'));
  HuleHtmx.init();
  // etc.
});
```

### C. Template-konsolidering
**Mål:** DRY templates, tydlig partial-hierarki.

1. **Extrahera gemensam run_result**:
   ```
   partials/
   └── run_result.html           # Gemensam, med flagga för admin-mode
   ```

2. **Standardisera HTMX-patterns**:
   - Alla partials som används med OOB-swap följer samma namnkonvention
   - Toast-injection via en enda partial

### D. Layout-robusthet
**Mål:** CSS Grid/Flexbox utan JS-sizing, fungerar cross-browser.

**Editor-layout specifikt:**
```css
.huleedu-editor-page {
  display: grid;
  grid-template-columns: 1fr 360px;
  grid-template-rows: 1fr;
  gap: var(--huleedu-space-4);
  height: 100%;
  min-height: 0; /* Kritiskt för nested scroll */
}

.huleedu-editor-code {
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.huleedu-editor-sidebar {
  display: flex;
  flex-direction: column;
  gap: var(--huleedu-space-4);
  overflow-y: auto;
}
```

---

## Särskilda Fokusområden

### A. Modern CSS Review

Granska användningen av modern CSS och identifiera möjligheter:

**Nuvarande brister:**
- Inkonsekvent användning av CSS Custom Properties (tokens finns men används inte överallt)
- Äldre layouttekniker blandas med moderna (float-rester? onödiga clearfix?)
- `calc()` används för viewport-beroende storlekar istället för moderna alternativ

**Granska och rekommendera:**
- **Container Queries** (`@container`) - för responsiva komponenter oberoende av viewport
- **`:has()` selector** - för parent-baserad styling utan JS
- **`dvh`/`svh`/`lvh`** - dynamiska viewport-units för mobil
- **`gap` i flexbox** - istället för margin-hacks
- **`aspect-ratio`** - för proportionella element
- **`clamp()`** - för fluid typography/spacing
- **Logical properties** (`margin-inline`, `padding-block`) - för RTL-ready kod
- **`@layer`** - för explicit cascade-kontroll

### B. Kritiskt Problem: Inkonsekvent Panel/Card-bredd

**Symptom:** Huvudsidornas paneler och kort har olika bredd beroende på sida, vilket skapar visuell dissonans och känns oprofessionellt.

**Drabbade sidor:**
- `/browse/*` - profession/category/tools-listor
- `/tools/{slug}/run` - verktygsexekvering
- `/my-tools` - användarens verktyg
- `/suggestions/*` - förslagsflöde
- `/login` - inloggning

**Önskad lösning:**
- EN konsekvent max-width för single-column layouts
- Använd CSS Custom Property: `--huleedu-content-width: 42rem` (eller liknande)
- Alla `.huleedu-panel` och `.huleedu-card` på huvudsidor ska respektera samma bredd
- Centrering med `margin-inline: auto`

**Leverabel:** Konkret CSS-fix som löser detta en gång för alla.

### C. Kritiskt Problem: CodeMirror Editor-sidan

**Symptom:** Script editor-sidan (`/admin/tools/{id}`) är komplex, bräcklig och svår att underhålla. Nuvarande implementation använder nested grid/flex med `min-height: 0`-hacks för scroll-containment.

**Nuvarande struktur:**
```
.huleedu-editor-page (grid: 1fr 360px)
├── .huleedu-editor-code (flex-column, overflow)
│   ├── toolbar
│   └── CodeMirror (måste fylla resterande höjd)
└── .huleedu-editor-sidebar (flex-column, overflow-y: auto)
    ├── metadata-card
    ├── version-list
    └── run-result
```

**Problem:**
- CodeMirror kollapsar/expanderar oförutsägbart efter HTMX-swaps
- Sidebar-scroll och main-scroll interfererar
- Toolbar ska vara sticky men CodeMirror ska scrolla
- Browser-beroende beteende

**Alternativ att utvärdera:**

#### Alternativ 1: Ren CSS Grid med `grid-template-areas` + `fr`

```css
.editor-layout {
  display: grid;
  grid-template-areas:
    "toolbar  sidebar"
    "editor   sidebar";
  grid-template-columns: 1fr 360px;
  grid-template-rows: auto 1fr;
  height: 100dvh; /* eller calc(100dvh - header) */
}

.editor-toolbar { grid-area: toolbar; }
.editor-code { grid-area: editor; overflow: auto; }
.editor-sidebar { grid-area: sidebar; overflow-y: auto; }
```

**Fördelar:** Rent CSS, ingen JS för layout, explicit områden
**Nackdelar:** CodeMirror kräver fortfarande JS-refresh vid resize

#### Alternativ 2: Vue + Vite SPA för Editor-sidan

**Koncept:** Bygg editor-sidan som en fristående Vue 3 SPA medan resten av applikationen förblir HTMX-driven.

**Implementation:**
```
src/skriptoteket/web/
├── static/
│   └── editor/           # Vite-byggd Vue-app
│       ├── index.js      # Entry point
│       └── assets/       # Bundlade CSS/JS
└── templates/
    └── admin/
        └── script_editor.html  # Minimal shell som mountar Vue-appen
```

**Template:**
```html
{% extends "base.html" %}
{% block content %}
<div id="editor-app"
     data-tool-id="{{ tool.id }}"
     data-version-id="{{ version.id }}"
     data-api-base="/api/admin"></div>
<script type="module" src="/static/editor/index.js"></script>
{% endblock %}
```

**Vue-komponenter:**
- `EditorLayout.vue` - Grid-container
- `CodeEditor.vue` - CodeMirror-wrapper med proper lifecycle
- `VersionSidebar.vue` - Versionshantering
- `RunResult.vue` - Exekveringsresultat
- `MetadataForm.vue` - Verktygsmetadata

**Fördelar:**
- Proper state management (Pinia)
- CodeMirror-integration via `@codemirror/vue` eller liknande
- Reaktiv UI utan HTMX-timing-problem
- Testbar med Vitest
- Hot module replacement under utveckling

**Nackdelar:**
- Introducerar byggtool (Vite)
- Två parallella frontend-paradigm
- API-endpoints behövs (JSON istället för HTML-partials)
- Ökad komplexitet i deployment

**Rekommendation:** Utvärdera om komplexiteten i editor-sidan motiverar Vue-overhead. Om ja, isolera det till ENDAST editor-sidan.

#### Alternativ 3: Hybrid - CSS Grid + Minimal Alpine.js

Behåll server-rendered HTML men använd Alpine.js för reaktiv state:

```html
<div x-data="editorState()" class="editor-layout">
  <div class="editor-code">
    <div x-ref="codemirror"></div>
  </div>
  <div class="editor-sidebar">
    <template x-if="runResult">
      <div x-html="runResult"></div>
    </template>
  </div>
</div>
```

**Fördelar:** Lättare än Vue, ingen byggprocess
**Nackdelar:** Ännu ett JS-ramverk att underhålla

---

## Önskade Leverabler

### 1. Analys-rapport
- Identifiera alla duplicerade styles
- Mappa CSS-beroenden mellan filer
- Lista alla JS-funktioner och deras korsningar
- Dokumentera HTMX-dataflöden
- **Modern CSS audit** - vilka moderna features saknas/bör användas?

### 2. Refactoring-plan
- Prioriterad ordning för ändringar
- Breaking changes vs bakåtkompatibla steg
- Migrationsstrategi (fil för fil eller big bang?)
- **Panel/card-bredd:** Konkret lösning med CSS
- **Editor-sidan:** Motiverad rekommendation (CSS Grid vs Vue vs Hybrid)

### 3. Implementeringsförslag
- Konkreta kodsnuttar för nyckelproblem
- Alternativa lösningar med trade-offs
- Teststrategier för CSS/JS-ändringar
- **Om Vue rekommenderas:** Skiss på komponentstruktur och API-kontrakt

---

## Constraints & Begränsningar

1. **Ingen SPA-migrering** - Behåll server-rendered + HTMX-arkitekturen
2. **Inga externa beroenden** - Vendored assets, ingen npm/bundler
3. **Browser-support** - Moderna browsers (Safari 15+, Chrome 90+, Firefox 90+)
4. **Inkrementella ändringar** - Måste kunna deployas stegvis
5. **Svensk UI** - All copy är på svenska, ändra inte texter

---

## Filer i paketet

### CSS (9 filer)
- `huleedu-design-tokens.css` - Design tokens
- `app.css` + `app/*.css` - Applikations-CSS

### JavaScript (1 fil)
- `app.js` - All klient-logik

### Templates (15 filer)
- `base.html` - Root template
- `home.html`, `login.html` - Grundsidor
- `browse_*.html` - Katalog
- `tools/*.html` - Verktygsexekvering
- `admin/*.html` - Admin-gränssnitt

### Backend (16 filer)
- `pages/*.py` - Route-handlers (kontext för templates)
- `templating.py`, `toasts.py`, `ui_text.py` - Stödmoduler

### Dokumentation (2 filer)
- `handoff.md` - Aktuell projektkontext
- `CLAUDE.md` - Projektregler och arkitektur

---

## Kontakt

Vid frågor om domänlogik eller backend-integration, eskalera till projektägaren.
Frontend-ändringar ska följa HuleEdu Design System-specifikationen ovan.
