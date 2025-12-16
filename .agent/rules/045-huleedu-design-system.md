---
id: "045-huleedu-design-system"
type: "implementation"
created: 2025-12-15
scope: "frontend"
references:
  - ADR-0017
  - EPIC-05
  - REF-htmx-ux-enhancement-plan
---

# 045: HuleEdu Design System

Skriptoteket adopts the HuleEdu Brutalist design system for visual consistency with the main EdTech platform.

## 1. Design Token Files

| File | Purpose |
|------|---------|
| `src/skriptoteket/web/static/css/huleedu-design-tokens.css` | **Canonical HuleEdu design tokens** (colors, typography, spacing, shadows) |
| `src/skriptoteket/web/static/css/app.css` | Application CSS (imports tokens + Skriptoteket extensions) |

**Never modify `huleedu-design-tokens.css` directly.** It is the shared source of truth with HuleEdu. Add Skriptoteket-specific styles to `app.css`.

## 2. Core Design Tokens

```css
/* Colors */
--huleedu-canvas: #F9F8F2;      /* Warm off-white background */
--huleedu-navy: #1C2E4A;        /* Primary text, borders, functional buttons */
--huleedu-burgundy: #6B1C2E;    /* CTA accent, error toasts */

/* Typography */
--huleedu-font-sans: "IBM Plex Sans", system-ui, sans-serif;
--huleedu-font-serif: "IBM Plex Serif", Georgia, serif;
--huleedu-font-mono: "IBM Plex Mono", monospace;

/* Shadows (Brutalist) */
--huleedu-shadow-brutal: 6px 6px 0px 0px var(--huleedu-navy);
```

## 3. Button Hierarchy (MUST follow)

| Button Type | Class | Use Case |
|-------------|-------|----------|
| Primary CTA | `.huleedu-btn` (burgundy default) | PUBLICERA, ANMAL INTRESSE |
| Functional | `.huleedu-btn-navy` | LOGGA IN, SPARA, SKICKA |
| Secondary | `.huleedu-btn-secondary` | AVBRYT, VISA DETALJER |
| Text link | `.huleedu-link` | Navigation with arrow |

```html
<!-- Primary CTA (burgundy) -->
<button class="huleedu-btn">Publicera</button>

<!-- Functional action (navy) -->
<button class="huleedu-btn huleedu-btn-navy">Logga in</button>

<!-- Secondary/cancel (navy outline) -->
<button class="huleedu-btn huleedu-btn-secondary">Avbryt</button>
```

## 4. Status Indicators

| Status | Class | Color | Meaning |
|--------|-------|-------|---------|
| Action required | `.huleedu-dot-active` | Burgundy | Requires user attention |
| OK / Published | `.huleedu-dot-success` | Navy | Stable state |
| Inactive | `.huleedu-dot` | Gray | Empty / inactive |

```html
<span class="huleedu-dot huleedu-dot-active"></span> ATGARD
<span class="huleedu-dot huleedu-dot-success"></span> BEARBETAR
```

## 5. Toast Notifications

| Type | Class | Background |
|------|-------|------------|
| Success | `.huleedu-toast-success` | Navy |
| Error | `.huleedu-toast-error` | Burgundy |

**No green color.** Success uses navy (see design reference images).

## 6. Component Classes (Quick Reference)

| Element | Class |
|---------|-------|
| Page frame | `.huleedu-frame` |
| Card | `.huleedu-card` |
| Input/textarea | `.huleedu-input` |
| Label | `.huleedu-label` |
| Error text | `.huleedu-error` |
| Muted text | `.huleedu-muted` |
| Checkbox group | `.huleedu-checkbox-group` |
| List item | `.huleedu-list-item` |
| Table | `.huleedu-table` |
| Badge | `.huleedu-badge` |
| Spinner | `.huleedu-spinner` |

## 7. Template Structure

```html
<body class="huleedu-base" hx-boost="true">
  <div class="huleedu-frame">
    <header class="huleedu-header">...</header>
    <main class="huleedu-main">{% block content %}{% endblock %}</main>
  </div>
  <div id="toast-container" class="huleedu-toast-container"></div>
</body>
```

## 8. Google Fonts

Add to `<head>` in `base.html`:

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
```

## 9. Grid Background Pattern

The 24px grid at 4% opacity is applied via `body::before` in `app.css`. Do not remove.

## 10. Stories (EPIC-05)

- **ST-05-01**: CSS foundation + base.html
- **ST-05-02**: Simple templates (login, home, error)
- **ST-05-03**: Browse templates
- **ST-05-04**: Suggestion templates
- **ST-05-05**: Admin templates (script_editor)
- **ST-05-06**: Toast partial + HTMX loading

See `docs/backlog/epics/epic-05-huleedu-design-harmonization.md` for acceptance criteria.

## 11. HTMX Gotchas

### File Downloads with hx-boost

When `hx-boost="true"` is on the body, HTMX intercepts ALL link clicks and fetches them via AJAX. This breaks file downloads - the file content gets swapped into the page instead of triggering a download dialog.

**Fix:** Add `hx-boost="false"` and `download` attribute to download links:

```html
<!-- BAD: HTMX intercepts and swaps file content into page -->
<a href="/download/file.txt">Download</a>

<!-- GOOD: Native browser download behavior -->
<a href="/download/file.txt" hx-boost="false" download>Download</a>
```

This applies to all artifact/file download links in both user-facing and admin templates.
