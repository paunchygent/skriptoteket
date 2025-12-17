---
type: reference
id: REF-frontend-expert-review-epic-05
title: "EPIC-05 Frontend expert review (repomix)"
status: active
owners: "agents"
created: 2025-12-17
topic: "frontend-review"
---

## 1. Analysrapport

Nedan är en sammanhållen frontend-review baserad på kontextpaketet (42 filer) med fokus på bräcklighet, kohesion, specifika UI-problem samt en konkret, stegvis refactor-plan som håller sig inom era constraints (server-rendered + HTMX, inga externa beroenden, inkrementella deployer).

### 1.1 CSS: duplicerade styles och överlappande concerns

#### A. “Design tokens”-filen är i praktiken ett globalt styles-lager (inte bara tokens)

`huleedu-design-tokens.css` innehåller inte bara CSS Custom Properties utan även **utilities**, **komponentklasser** och t.o.m. HTMX-relaterade states (t.ex. `.huleedu-header`, `.huleedu-dot`, `.huleedu-grid-bg`, `.huleedu-skip-link`, och `.htmx-request .huleedu-loading`).

Detta skapar två problem:

1. **Otydlig källa till sanning**: när en klass finns både i tokens-filen och i app-moduler (se nästa punkt) blir cascade beroende av importordning/override, vilket ökar bräcklighet.
2. **Arkitektur-mismatch mot målbild**: er målbild säger “tokens endast” i `huleedu-design-tokens.css`, men nuvarande fil beter sig som ett “design system bundle”.

#### B. Faktiska selector-krockar mellan tokens-filen och app-CSS (layout)

Ni har minst två centrala layout-selektorer definierade i *både* tokens-filen och app-layout:

* `.huleedu-frame` definieras i tokens-filen och i `layout.css`.
* `.huleedu-header` definieras i tokens-filen och i `layout.css`.

Konsekvens: små förändringar i en fil kan ge oväntade effekter, särskilt på höjd/scroll (som är ett av era uttalade problemområden).

#### C. Utilities-filen innehåller icke-atomära komponenter

`utilities.css` innehåller inte bara atomic utilities (gap/margins/max-width) utan även **listor, tabeller och “tool row”-layout** (`.huleedu-list`, `.huleedu-table`, `.huleedu-tool-row`, etc.). Det är komponent-ansvar, inte utilities-ansvar, vilket försvårar separation och återanvändning.

Det här är en av de tydligaste källorna till “duplicerade concerns” mellan `components.css` och `utilities.css` i praktiken: inte samma selektorer nödvändigtvis, men samma *komponent-domän* hamnar på flera ställen.

#### D. Kritisk CSS‑bugg: trasig toast‑regel (saknad `}`)

I `components.css` saknas en avslutande klammer för `.huleedu-toast-container`, vilket gör resten av blocket i praktiken opålitligt (och kan direkt förklara “toast överlappar header” och/eller märklig toast‑styling).

Detta är en “stop‑the‑line”‑bugg: fixa först, annars blir alla efterföljande slutsatser om toast‑layout delvis brus.

#### E. Små men viktiga “kvarvarande” inline styles

Ni har fortfarande inline styles i run-result‑partials och admin‑editor, bl.a. för iframe‑presentation och “border-color”.
Det här driver exakt den inkonsekvens ni beskriver (mix av utility-klasser och inline).

---

### 1.2 CSS: beroendekarta (import/cascade och vad som “äger” vad)

#### Importkedjan

`static/css/app.css` importerar först tokens-filen och därefter de modulära filerna i ordningen base → layout → buttons → forms → components → editor → utilities.

Det är i grunden en rimlig ordning, men kombinationen med att tokens-filen även innehåller komponent‑/utility‑CSS gör att den fungerar som ett extra “lager 0” som ibland konkurrerar med era modul-filer.

#### Nuvarande ansvarsfördelning (faktiskt, inte avsett)

* `huleedu-design-tokens.css`: tokens + bas/utility/komponenter/animationer/HTMX‑states.
* `base.css`: reset + body‑typografi + bakgrund.
* `layout.css`: frame/header/main scroll‑containment och “fluid main”.
* `buttons.css`: varianter, states, loading, danger. (Bas-CTA ligger i tokens-filen.)
* `forms.css`: form layout, errors, file input‑pattern (screenreader-only native input).
* `components.css`: alerts + toasts + pills + tabs + HTMX loading states (blandat ansvar).
* `editor.css`: CodeMirror theme + editor layout (min-height/overflow‑val).
* `utilities.css`: utilities + list/table/tool-row komponenter + panel‑container.

---

### 1.3 JavaScript: funktioner, ansvar och korsningar

#### A. App.js är en monolit med minst 6 concerns

I `static/js/app.js` ligger:

* Vendor lazy‑load (CodeMirror CSS/JS)
* CodeMirror init/cleanup/refresh
* HTMX lifecycle listeners (`htmx:load`, `afterSwap`, `afterSettle`, `configRequest`)
* Toast auto‑dismiss + MutationObserver
* File input filename display (data‑attribute)
* Form sync (submit + HTMX configRequest)

Detta framgår tydligt av funktionerna och eventregistreringen.

#### B. Lista över centrala funktioner och korsningar (nuvarande)

Exempel på “korsningar” (cross‑cutting):

* **`init(root)`**: orchestrator som initierar *både* toasts, file inputs och CodeMirror samt cleanup, och används i *både* `DOMContentLoaded` och HTMX‑events.
* **CodeMirror ↔ HTMX**:

  * `htmx:configRequest` triggar `syncCodeMirrorFields()` så att textarea får rätt value före request.
  * `htmx:afterSwap`/`afterSettle` triggar `scheduleAllEditorsRefresh()` för att motverka “collapse” efter swap/timing.
* **Toast ↔ DOM**: MutationObserver sitter på `#toast-container` och auto‑dismissar nya toasts (inkl. OOB).
* **File input ↔ markup**: `data-huleedu-file-name-target` kopplar input till span med filnamn.

---

### 1.4 HTMX-dataflöden (dokumenterat)

#### A. Global navigation via `hx-boost`

`base.html` har `hx-boost="true"` på `<body>`, vilket gör att navigation och vissa submits sker via HTMX och därmed kräver re-init av JS efter swap.

Det här är den huvudsakliga orsaken till att CodeMirror‑init och andra UI‑hooks idag måste hänga på HTMX‑livscykeln.

#### B. Tools “run”-flöde (user)

`tools/run.html` använder `hx-post` till `/tools/{{ tool.slug }}/run` med `hx-target="#result-container"` och multipart‑encoding.
Responsen förväntas ersätta resultat‑container via `innerHTML`.

#### C. Admin editor “run sandbox”-flöde

`admin/script_editor.html` har ett run-form med `hx-post` till `/admin/tool-versions/{{ selected_version.id }}/run-sandbox`, `hx-target="#run-result"`, multipart, och indikator.

#### D. Toast‑pipeline (cookie → middleware → template → JS/OOB)

* Server sätter toast cookie (t.ex. `set_toast_cookie`) och kan läsa den (`read_toast_cookie`).
* Middleware läser cookie, sätter `request.state.toast_message` och rensar cookie efter request.
* `base.html` renderar toast DOM om `request.state.toast_message` finns.
* För HTMX‑fel finns `run_error_with_toast.html` som inkluderar toast-partial med `hx-swap-oob="beforeend:#toast-container"`.
* Frontend observer/dismiss hanterar auto‑dismiss.

Detta är funktionellt, men “lagerdjupet” gör det svårare att förändra eller felsöka.

---

### 1.5 Modern CSS audit (möjligheter och realism under er browser-baseline)

#### Redan bra / modern usage

* CSS custom properties (tokens) som grund.
* Grid + flex + `gap` används brett.
* `accent-color` för checkbox/radio.
* `:focus-visible` och SR-only‑pattern finns.
* `overscroll-behavior` används i editor-sidans sidebar‑container (minskar scroll chaining).

#### Risk/bugg kopplat till moderna viewport units

Ni använder `100dvh` i layout för `.huleedu-frame` (och `calc(100dvh - …)` i media query) utan explicit fallback till `100vh`.
Det är bra i nya mobila browsers, men om er faktiska baseline inkluderar äldre browsers blir det en kompatibilitetsrisk.

#### Rekommenderade “modern CSS”-förbättringar som är säkra inkrementellt

* **Fallback + override‑stacking** för viewport units: `height: 100vh; height: 100dvh;` (då ignoreras `dvh` där det saknas, men ni får alltid en fungerande höjd). (Se kod i implementeringsdelen.)
* **Logical properties**: byt `margin-left/right` till `margin-inline`, `top/right` till `inset-block-start/inset-inline-end` där det passar. Ni har redan flera ställen där detta ger tydligare intention (t.ex. `.huleedu-panel`).
* **`clamp()`**: använd för att göra padding/typografi “fluid” utan media queries. (Inom era constraints bör detta vara säkert.)
* **Progressive enhancement** för `:has()` och Container Queries via `@supports` (men inte som baseline). Detta kan ni lägga senare utan att bryta äldre browsers.

---

## 2. Refactoring-plan (prioriterad, inkrementell)

Nedan är en plan som kan deployas stegvis och där varje steg ger stabilitetsvinst utan att kräva “big bang”.

### Fas 0 — Stabiliserande hotfixar (0 risk, hög nytta)

1. **Fix: `.huleedu-toast-container` saknar `}`**
   Detta är akut; åtgärda innan ni försöker förbättra toasts eller layout.

2. **Lägg in `vh` fallback för `dvh`** i `layout.css` på `.huleedu-frame` (och ev media query).

3. **Flytta inline styles i run_result/iframes till CSS-klasser**

   * `tools/partials/run_result.html` har inline `style="border-color: …"` och iframe inline style.
   * `admin/partials/run_result.html` har iframe styling inline.

**Breaking?** Nej.

---

### Fas 1 — Panel/card-bredd (snabb visuell kvalitet, liten förändring)

**Mål:** En konsekvent single‑column max‑width över huvudflöden.

* Ni har redan `.huleedu-panel` med max-width `--huleedu-max-width-2xl`.
* Men `home.html` och `login.html` använder `huleedu-max-w-md huleedu-mx-auto` vilket ger smalare kort och skapar “dissonans”.

**Åtgärd:**

* Inför `--huleedu-content-width` som en app‑policy och låt `.huleedu-panel` alltid använda den.
* Uppdatera mallar (home/login + övriga single‑column pages i repo) att använda `.huleedu-panel` i stället för `huleedu-max-w-*` där panel‑konsekvens är önskad.

**Breaking?** Nej (CSS + klassjustering i templates).

---

### Fas 2 — CSS‑arkitektur: separera “utilities” från komponenter

**Mål:** Förutsägbar cascade och tydliga ägarskap.

1. **Flytta komponent‑styles ur `utilities.css`**

   * `.huleedu-list`, `.huleedu-table`, `.huleedu-tool-row` osv flyttas till nya komponentfiler (`lists.css`, `tables.css` eller `lists.css` som även inkluderar tool rows).
     `utilities.css` ska därefter bara innehålla atomic utilities och helpers.

2. **Split `components.css`** till komponentfiler:

   * `toasts.css` (toast container + toast)
   * `alerts.css` (huleedu-alert)
   * `pills.css` / `badges.css` (pills, badges)
   * `tabs.css`
   * (ev) `htmx.css` (loading states)

   Idag ligger alerts/toasts/pills/tabs/htmx states i samma fil.

3. **Numrerad importordning** (som ni föreslår) kan införas utan `@layer`
   Ni kan nå “explicit cascade” genom filnamn + importordning i `app.css` (t.ex. `00-reset.css`, `01-base.css`, `10-layout.css`, `20-components/...`, `30-utilities.css`) utan att kräva cascade layers.

**Breaking?** Låg, om ni gör det som “copy then delete”:

* Skapa nya filer + importera dem,
* låt gamla filer ligga kvar temporärt,
* flytta block för block och radera när coverage är 100%.

---

### Fas 3 — JavaScript modularisering (utan bundler)

**Mål:** Isolera concerns och minska HTMX‑coupling.

**Rekommenderad strategi inom constraints:**

* Behåll vanilla JS och inga npm‑beroenden.
* Skapa flera filer under `static/js/` (t.ex. `huleedu/toast.js`, `huleedu/editor.js`, `huleedu/file-input.js`, `huleedu/htmx.js`) och exponera dem via ett enda namespace (`window.HuleEdu`).
* Låt nuvarande `app.js` bli en liten orchestrator (eller ersätts av `app.js` som importerar/förutsätter namespace).

Det här är fullt kompatibelt med “inkrementella deployer” eftersom ni kan flytta en concern i taget utan att ändra resten.

**Breaking?** Låg (mest filstruktur + script includes).

---

### Fas 4 — Template‑konsolidering (DRY, men respektera säkerhetskrav)

#### Run result: säkerhetsdriven skillnad mellan admin och user

* User‑partial saknar stdout/stderr av säkerhetsskäl (uttalat i kommentaren).
* Admin‑partial visar stdout/stderr.

**Rekommendation:** Konsolidera till en gemensam partial, men med flagga `show_debug` (admin=true, tools=false), så att ni inte duplicerar markup. Detta ligger i linje med er målbild.

#### Run error with toast: duplicering som kan tas bort direkt

`tools/partials/run_error_with_toast.html` kan flyttas till `partials/` och användas från både admin/tools (om admin har motsvarande).

**Breaking?** Medel‑låg (uppdatera include-paths).

---

### Fas 5 — Editor-sidan: rekommendation och motivering

Ni bad explicit om att utvärdera alternativen. Med era constraints:

* **Alternativ 2 (Vue + Vite SPA)** faller på “ingen SPA‑migrering” och “inga externa beroenden/bundler”.
* **Alternativ 3 (Alpine.js)** introducerar ett nytt dependency (även om lätt), vilket bryter “inga externa beroenden”.

**Rekommendation: Alternativ 1 — Ren CSS Grid + tydliga scroll‑containrar, plus minimal JS‑refresh för CodeMirror.**
Det passar er arkitektur, kräver ingen ny toolchain och är deploybart inkrementellt.

#### Varför editorn är bräcklig idag

* Editorns textarea wrapper har `min-height: 500px` och `flex: 1 0 auto` (växer men krymper inte), samtidigt som run-result får expandera fritt (`max-height: none; overflow: visible`). Det gör höjd‑dynamik känslig när innehåll byts via HTMX.
* CodeMirror kräver refresh när container dimension ändras; ni kompenserar via HTMX hooks + timeouts.

**Förslag:** Lägg till ResizeObserver‑baserad refresh (se kod) och gör scroll‑ansvaret tydligt (en scroll container per kolumn) så att CodeMirror inte kollapsar vid HTMX‑swap.

---

## 3. Implementeringsförslag (konkreta kodsnuttar)

### 3.1 Konkret CSS-fix: konsekvent panel/card-bredd

Ni har redan `.huleedu-panel` men den använder `margin-left/right` och max-width‑token direkt.
Gör detta till en “policy”:

**Steg 1: definiera content width**
Placera i t.ex. `layout.css` eller en ny `01-base.css`:

```css
:root {
  --huleedu-content-width: 42rem; /* eller var(--huleedu-max-width-2xl) */
}
```

**Steg 2: gör `.huleedu-panel` canonical och logisk**
Ersätt nuvarande `.huleedu-panel` i utilities:

```css
.huleedu-panel {
  width: 100%;
  max-width: var(--huleedu-content-width);
  margin-inline: auto;
}
```

Detta uppfyller ert krav: “EN konsekvent max-width”, “CSS Custom Property”, “margin-inline: auto”. (Utgångsläget för `.huleedu-panel` finns redan i utilities.)

**Steg 3: uppdatera mallar som idag använder `max-w-md` för huvudpanel**

* `home.html`: byt `huleedu-max-w-md huleedu-mx-auto` → `huleedu-panel`
* `login.html`: byt `huleedu-max-w-md huleedu-mx-auto` → `huleedu-panel`

Minimal mall‑diff (exempel):

```html
<!-- före -->
<div class="huleedu-card huleedu-stack huleedu-max-w-md huleedu-mx-auto">

<!-- efter -->
<div class="huleedu-card huleedu-stack huleedu-panel">
```

---

### 3.2 Toast: fixa buggen och gör layouten robust på smal viewport

**Steg 1: fixa saknad klammer**
I `components.css` måste `.huleedu-toast-container` stängas.

```css
.huleedu-toast-container {
  position: fixed;
  top: calc(var(--huleedu-space-4) + var(--huleedu-header-height));
  right: var(--huleedu-space-4);
  z-index: 2000 !important;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
} /* <-- saknas idag */
```

**Steg 2: gör toast container responsiv och mindre “header‑intrusive”**
Utöver buggen kan ni minska header‑krockar med:

* logical properties
* max-inline-size
* pointer-events policy (container none, toast auto)

```css
.huleedu-toast-container {
  position: fixed;
  inset-block-start: calc(var(--huleedu-space-4) + var(--huleedu-header-height));
  inset-inline-end: var(--huleedu-space-4);

  display: flex;
  flex-direction: column;
  gap: var(--huleedu-space-2);
  align-items: flex-end;

  /* gör att den aldrig “trycker” utanför viewport */
  max-inline-size: calc(100vw - (2 * var(--huleedu-space-4)));

  /* så headern går att klicka även om container täcker yta */
  pointer-events: none;
}

.huleedu-toast {
  pointer-events: auto;
  width: min(100%, var(--huleedu-content-width));
}
```

Toast DOM och auto-dismiss beteende finns redan i base + JS.

---

### 3.3 Layout: `dvh` med fallback

Ni använder `100dvh` i `.huleedu-frame`.
Gör det kompatibelt genom fallback‑stacking:

```css
.huleedu-frame {
  min-height: 100vh;
  height: 100vh;

  min-height: 100dvh;
  height: 100dvh;
}
```

Och i media query:

```css
@media (min-width: 768px) {
  .huleedu-frame {
    min-height: calc(100vh - var(--huleedu-space-8));
    height: calc(100vh - var(--huleedu-space-8));

    min-height: calc(100dvh - var(--huleedu-space-8));
    height: calc(100dvh - var(--huleedu-space-8));
  }
}
```

---

### 3.4 Editor-sidan: CSS Grid‑layout och scroll‑containment

Utifrån nuvarande markup (editor-layout + toolbar + run-result) och era problem, är målet att:

* göra editor-ytan deterministisk i höjd,
* isolera scroll per kolumn,
* undvika att run-result “trycker sönder” editorns höjd.

Ni har redan flera editor‑relaterade flex/höjd‑val (min-height 500px och run-result som expanderar fritt).

**Konservativ förbättring (ingen markup‑brytning):**

* gör `.huleedu-editor-code-card` till grid med `rows: 1fr auto auto` (editor, toolbar, runresult)
* låt CodeMirror‑wrappern ha `min-height: 0` och `overflow: hidden`
* gör run-result scroll‑capped (så editor inte kollapsar när resultatet blir långt)

Exempel:

```css
.huleedu-editor-code-card {
  display: grid;
  grid-template-rows: 1fr auto auto;
  min-height: 0;
}

.huleedu-editor-textarea-wrapper {
  min-height: 0;            /* ersätt/komplettera min-height:500px */
  overflow: hidden;
}

.huleedu-editor-run-result {
  max-height: 40vh;
  overflow: auto;
}
```

Detta är i linje med era egna observationer om nested scroll och min-height:0‑kritikalitet, men gör “run result” mindre destruktivt.

---

### 3.5 CodeMirror: decoupla från HTMX timing med ResizeObserver

Ni har redan refresh på HTMX events och timeouts.
Den robustaste “minimal JS”-lösningen (utan ny dependency) är att:

* refresha editor när dess wrapper ändrar storlek, oavsett *varför* (HTMX swap, panel expand, sidebar toggles, viewport).

Skiss (att lägga i editor‑modul):

```js
function attachAutoRefresh(editor) {
  let raf = 0;

  const refreshSoon = () => {
    if (raf) cancelAnimationFrame(raf);
    raf = requestAnimationFrame(() => {
      editor.refresh();
    });
  };

  // 1) ResizeObserver: refresh på layoutförändringar
  const ro = new ResizeObserver(refreshSoon);
  ro.observe(editor.getWrapperElement());

  // 2) Fallback: refresh när dokument blir synligt igen (Safari-quirks)
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) refreshSoon();
  });

  return () => ro.disconnect();
}
```

Då minskar ni beroendet av HTMX event‑timing (även om ni kan behålla hooks som extra säkerhetsnät). Detta adresserar direkt problemet “CodeMirror kan kollapsa efter HTMX‑swap om timing är fel”.

---

### 3.6 Template‑konsolidering: `run_result.html` med flagga

Ni har två `run_result.html`:

* tools: utan stdout/stderr (säkerhetskrav)
* admin: med stdout/stderr

**Rekommenderad struktur:**

`templates/partials/run_result.html`:

```jinja2
{# expects: run, artifacts, show_debug #}

<div class="huleedu-card huleedu-stack{% if run.error_summary %} huleedu-card--error{% endif %}">
  <div class="huleedu-muted">
    <span class="huleedu-pill{% if run.error_summary %} huleedu-pill-active{% endif %}">
      {{ run.status | run_status_label }}
    </span>
  </div>

  {% if run.error_summary %}
    <div>
      <strong class="huleedu-error">Ett fel uppstod</strong>
      <pre>{{ run.error_summary }}</pre>
    </div>
  {% endif %}

  {% if run.html_output %}
    <div>
      <strong>Resultat</strong>
      <iframe class="huleedu-run-iframe" sandbox srcdoc="{{ run.html_output | e }}"></iframe>
    </div>
  {% endif %}

  {% if show_debug %}
    {% if run.stdout or run.stderr %}
      <details>
        <summary>Teknisk output</summary>
        {% if run.stdout %}<pre>{{ run.stdout }}</pre>{% endif %}
        {% if run.stderr %}<pre>{{ run.stderr }}</pre>{% endif %}
      </details>
    {% endif %}
  {% endif %}

  {# artifacts-list etc... #}

</div>
```

I tools‑partial:

```jinja2
{% set show_debug = false %}
{% include "partials/run_result.html" %}
```

I admin‑partial:

```jinja2
{% set show_debug = true %}
{% include "partials/run_result.html" %}
```

Säkerhetskravet bibehålls (tools får aldrig debug), men markup dupliceras inte.

---

## 4. Teststrategi (praktisk och inkrementell)

### A. “Smoke checks” per deploy (utan nya verktyg)

* Verifiera att toasts renderas och auto-dismiss fungerar:

  * full page (cookie/middleware)
  * HTMX OOB (run_error_with_toast)
* Verifiera HTMX-run på tools och admin:

  * tools: `hx-post` och target container
  * admin: `hx-post` och `#run-result`
* Verifiera panelbredd: home/login använder `.huleedu-panel` och att `--huleedu-content-width` tar effekt.

### B. Cross‑browser fokus för editor (där ni har mest risk)

* Testa scroll‑interaktion (main vs sidebar), samt run-result med lång output.
* Testa HTMX navigation (hx-boost) in/ut från editor och att CodeMirror behåller storlek (ResizeObserver‑refresh).

---

## Rekommenderad “nästa commit”-scope (minsta men högst effekt)

Om ni vill ha en konkret, låg-risk “första refactor PR” som ger tydlig ROI:

1. Fix toast CSS‑klammer + förbättra toast container responsivt.
2. Inför `--huleedu-content-width` + uppdatera `.huleedu-panel` + byt home/login till panel.
3. Flytta iframe/“error border” inline styles till CSS-klasser (run_result admin/tools).

Detta är inkrementellt, kräver inga nya beroenden, och löser 2 av era uttalade UI-problem direkt (toast-header overlap och panelbredd‑dissonans), samtidigt som det minskar bräckligheten.
