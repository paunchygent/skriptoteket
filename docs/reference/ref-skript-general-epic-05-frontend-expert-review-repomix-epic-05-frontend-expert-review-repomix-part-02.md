---
type: reference
id: REF-SKRIPT-GENERAL-epic-05-frontend-expert-review-repomix-PART-02
title: EPIC-05 Frontend expert review (repomix) — part 02
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
root: REF-SKRIPT-GENERAL-epic-05-frontend-expert-review-repomix
part: 2
---

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

### Source: 4. Teststrategi (praktisk och inkrementell)

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

### Source: Rekommenderad “nästa commit”-scope (minsta men högst effekt)

Om ni vill ha en konkret, låg-risk “första refactor PR” som ger tydlig ROI:

1. Fix toast CSS‑klammer + förbättra toast container responsivt.
2. Inför `--huleedu-content-width` + uppdatera `.huleedu-panel` + byt home/login till panel.
3. Flytta iframe/“error border” inline styles till CSS-klasser (run_result admin/tools).

Detta är inkrementellt, kräver inga nya beroenden, och löser 2 av era uttalade UI-problem direkt (toast-header overlap och panelbredd‑dissonans), samtidigt som det minskar bräckligheten.

## Decisions And Interpretation

No separate source material was recorded for this section.
