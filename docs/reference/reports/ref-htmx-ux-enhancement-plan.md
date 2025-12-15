---
type: reference
id: REF-htmx-ux-enhancement-plan
title: "HTMX UX Enhancement: Developer Implementation Guide"
status: active
owners: "agents"
created: 2025-12-15
topic: "frontend"
links:
  - ADR-0001
  - ADR-0017
  - EPIC-05
---

## Executive Summary

This document provides a complete implementation guide for enhancing Skriptoteket's UX using HTMX. It serves as an alternative to the Vue SPA migration (see `ref-vue-spa-migration-assessment.md`), delivering SPA-like responsiveness while preserving the server-rendered architecture.

**Design system**: HuleEdu Brutalist design tokens (ADR-0017, EPIC-05)

**Estimated effort**: 15-25 hours (vs ~103h for Vue SPA)

**Key deliverables**:

1. Global `hx-boost` for seamless navigation
2. HTMX-powered forms with inline feedback (no full page reloads)
3. Loading indicators and smooth transitions
4. Improved form layouts (less blocky, better visual hierarchy)
5. HuleEdu design system integration for visual consistency with main platform

---

## Session Scope for Lead Developer

### Role

You are the lead developer and architect of **Skriptoteket**.

The scope of this session is: **HTMX UX enhancement across all web templates** - converting full-page-reload forms to partial updates, adding loading states, and improving form visual design while preserving the server-rendered architecture.

### Before Touching Code

From repo root, read:

1. **AGENTS.md** - Monorepo conventions, DI patterns, test structure
2. **.agent/rules/000-rule-index.md** - Index of all rules
3. **.agent/rules/040-fastapi-blueprint.md** - Web layer patterns, HTMX endpoint patterns
4. **.agent/rules/050-python-standards.md** - Code style requirements
5. **.agent/rules/070-testing-standards.md** - Testing approach

### Critical Files to Understand

| File | Purpose |
|------|---------|
| `src/skriptoteket/web/templates/base.html` | Base template with HTMX loading, CSS foundation |
| `src/skriptoteket/web/templates/admin/script_editor.html` | **Reference implementation** - existing HTMX patterns |
| `src/skriptoteket/web/pages/admin_scripting_support.py` | HTMX helpers: `is_hx_request()`, `redirect_with_hx()` |
| `src/skriptoteket/web/pages/admin_scripting_runs.py` | Pattern for conditional HTMX vs full-page responses |
| `docs/reference/reports/ref-vue-spa-migration-assessment.md` | Context on why HTMX over Vue SPA |

### Existing HTMX Patterns

The codebase already has HTMX infrastructure in `admin_scripting_support.py`:

```python
def is_hx_request(request: Request) -> bool:
    return request.headers.get("HX-Request") == "true"

def redirect_with_hx(*, request: Request, url: str) -> RedirectResponse:
    response = RedirectResponse(url=url, status_code=303)
    if is_hx_request(request):
        response.headers["HX-Redirect"] = url
    return response
```

**Use existing patterns; do not invent new abstractions if an equivalent pattern already exists.**

---

## Current State Analysis

### HTMX Usage (as of 2025-12-15)

HTMX is only used in the admin script editor (`script_editor.html`):

- Version list refresh: `hx-get` to `/admin/tools/{tool_id}/versions`
- Sandbox execution: `hx-post` to `/admin/tool-versions/{version_id}/run-sandbox`

### Forms Causing Full Page Reloads

| Form | Template | Pain Points |
|------|----------|-------------|
| Login | `login.html` | Full reload on error |
| Suggestion submit | `suggestions_new.html` | Large form, no inline validation |
| Suggestion review | `suggestions_review_detail.html` | Complex conditional fields, full reload |
| Tool publish/depublish | `admin_tools.html` | Button actions reload page |

### CSS Issues

- All styling inline in `base.html` (no external CSS)
- No design tokens (colors, spacing hardcoded)
- Checkbox groups use `<br>` for layout
- No loading state styles
- No toast/notification system

---

## Implementation Plan

### Phase 1: CSS Foundation (3-4h)

**Goal**: Integrate HuleEdu design system for visual consistency with the main platform.

See **ADR-0017** for design system decision and **EPIC-05** for full story breakdown.

#### Step 1.1: Create CSS Files

**File 1**: `src/skriptoteket/web/static/css/huleedu-design-tokens.css`

Full HuleEdu design tokens (colors, typography, spacing, shadows). This file is the single source of truth shared with HuleEdu.

**File 2**: `src/skriptoteket/web/static/css/app.css`

Imports tokens and adds Skriptoteket-specific extensions:

```css
@import url('huleedu-design-tokens.css');

/* HuleEdu Design System - Key tokens */
:root {
  --huleedu-canvas: #F9F8F2;      /* Warm off-white background */
  --huleedu-navy: #1C2E4A;        /* Primary text, borders, functional buttons */
  --huleedu-burgundy: #6B1C2E;    /* CTA accent, error toasts */
  --huleedu-font-sans: "IBM Plex Sans", system-ui, sans-serif;
  --huleedu-shadow-brutal: 6px 6px 0px 0px var(--huleedu-navy);
}

/* Grid background pattern (24px, 4% opacity) */
body::before {
  content: '';
  position: fixed;
  inset: 0;
  background-image:
    linear-gradient(var(--huleedu-navy) 1px, transparent 1px),
    linear-gradient(90deg, var(--huleedu-navy) 1px, transparent 1px);
  background-size: 24px 24px;
  opacity: 0.04;
  pointer-events: none;
  z-index: -1;
}

/* Button hierarchy */
.huleedu-btn { /* Navy filled - functional actions */ }
.huleedu-btn (default burgundy) { /* Primary CTA - PUBLICERA */ }
.huleedu-btn-secondary { /* Navy outline - secondary actions */ }

/* Toast notifications */
.huleedu-toast-success { background: var(--huleedu-navy); }
.huleedu-toast-error { background: var(--huleedu-burgundy); }

/* Status dots */
.huleedu-dot-active { background: var(--huleedu-burgundy); }  /* Requires action */
.huleedu-dot-success { background: var(--huleedu-navy); }     /* OK/published */
```

See `static/css/app.css` for complete implementation with all component classes.

#### Step 1.2: Update base.html

```html
<head>
  <!-- Google Fonts: IBM Plex family -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">

  <!-- HuleEdu design system -->
  <link rel="stylesheet" href="/static/css/app.css">
</head>
<body class="huleedu-base" hx-boost="true">
  <div class="huleedu-frame">
    <header class="huleedu-header">...</header>
    <main class="huleedu-main">{% block content %}{% endblock %}</main>
  </div>
  <div id="toast-container" class="huleedu-toast-container"></div>
</body>
```

**Checkpoint**: Confirm canvas background, IBM Plex fonts, and ledger frame are visible.

---

### Phase 2: Global hx-boost (1-2h)

**Goal**: Enable SPA-like navigation without full page reloads.

#### Step 2.1: Add hx-boost to base.html

```html
<body hx-boost="true">
```

This automatically converts all links and forms to AJAX requests, swaps body content, and preserves browser history.

#### Step 2.2: Exclude Specific Elements

```html
<a href="/download/file" hx-boost="false">Download</a>
<form method="post" action="/logout" hx-boost="false">...</form>
```

Exclude: file downloads, external links, logout form.

**Checkpoint**: Test navigation between all pages. Verify history works.

---

### Phase 3: Form HTMX Conversion (8-12h)

Implement in priority order:

#### 3.1: Login Form (2h)

**File**: `src/skriptoteket/web/templates/login.html`

- Add `hx-post`, `hx-target="#login-form"`, `hx-swap="outerHTML"`
- Create partial `templates/partials/login_form.html`
- Backend: Modify `auth.py::login()` to return partial on HTMX request
- Add loading indicator, inline error display

**Decision**: Successful login should use `HX-Redirect` to `/` (recommended).

#### 3.2: Suggestion Submit Form (3h)

**File**: `src/skriptoteket/web/templates/suggestions_new.html`

- Wrap form for swap target
- Create partial for form
- Backend: Modify `suggestions.py::submit_suggestion()`
- Success: Toast + reset form or redirect

**Decision**: On success, show toast and reset form (recommended) OR redirect?

#### 3.3: Suggestion Review Decision Form (3h)

**File**: `src/skriptoteket/web/templates/suggestions_review_detail.html`

Most complex form. Changes:

1. **Conditional field visibility** (client-side JS recommended):

```html
<script>
document.querySelectorAll('[name="decision"]').forEach(r => {
  r.addEventListener('change', () => {
    document.getElementById('accept-fields').style.display =
      r.value === 'accept' ? 'block' : 'none';
  });
});
</script>
```

2. Form submission via HTMX
3. Inline success feedback

**Decision**: Use simple JS for field toggle (no server round-trip needed).

#### 3.4: Tool Admin Actions (2h)

**File**: `src/skriptoteket/web/templates/admin_tools.html`

- Publish/depublish: `hx-post`, `hx-swap="outerHTML"` on row
- Create partial `templates/admin/partials/tool_row.html`
- Backend returns updated row HTML

---

### Phase 4: Loading States & Feedback (2-3h)

#### 4.1: Global Loading Indicator

```html
<body class="huleedu-base" hx-boost="true" hx-indicator="#global-loader">
<div id="global-loader" class="htmx-indicator huleedu-loader">
  <div class="huleedu-spinner"></div>
</div>
```

#### 4.2: Button Loading States

```html
<button type="submit" class="huleedu-btn huleedu-btn-navy">
  <span class="htmx-indicator"><span class="huleedu-spinner huleedu-spinner-light"></span></span>
  <span>Skicka</span>
</button>
```

#### 4.3: Toast Notifications (OOB Swap)

```html
<!-- In response, include: -->
<div id="toast-container" hx-swap-oob="beforeend">
  <div class="huleedu-toast huleedu-toast-success">Saved!</div>
</div>
```

---

### Phase 5: Script Editor Enhancements (2h)

**File**: `src/skriptoteket/web/templates/admin/script_editor.html`

- Add loading spinner to sandbox run button
- Progress indication for long-running scripts
- Improved run result display with transitions

---

## Files Summary

### New Files

| Path | Purpose |
|------|---------|
| `src/skriptoteket/web/static/css/huleedu-design-tokens.css` | HuleEdu design tokens (shared) |
| `src/skriptoteket/web/static/css/app.css` | Application CSS with token imports |
| `src/skriptoteket/web/templates/partials/login_form.html` | Login form partial |
| `src/skriptoteket/web/templates/partials/suggestion_form.html` | Suggestion form partial |
| `src/skriptoteket/web/templates/admin/partials/tool_row.html` | Tool list row partial |
| `src/skriptoteket/web/templates/partials/toast.html` | Toast notification partial |

## HuleEdu Component Class Mapping

| Current | HuleEdu Class | Notes |
|---------|---------------|-------|
| `.card` | `.huleedu-card` | Brutal shadow, navy border |
| `button` | `.huleedu-btn` | Burgundy by default (CTA) |
| `button` (functional) | `.huleedu-btn-navy` | Navy filled for LOGGA IN, SPARA |
| `button` (secondary) | `.huleedu-btn-secondary` | Navy outline for AVBRYT |
| `input`, `textarea` | `.huleedu-input` | Navy border, canvas background |
| `.error` | `.huleedu-error` | Burgundy text |
| `.muted` | `.huleedu-muted` | Navy-60 text |
| checkbox group | `.huleedu-checkbox-group` | Flex wrap layout |
| list item | `.huleedu-list-item` | Row with hover state |
| status dot | `.huleedu-dot-active` | Burgundy for "requires action" |
| status dot | `.huleedu-dot-success` | Navy for "OK/published" |
| toast success | `.huleedu-toast-success` | Navy background |
| toast error | `.huleedu-toast-error` | Burgundy background |

### Modified Files

| Path | Changes |
|------|---------|
| `src/skriptoteket/web/templates/base.html` | CSS link, hx-boost, toast container |
| `src/skriptoteket/web/templates/login.html` | HTMX form |
| `src/skriptoteket/web/templates/suggestions_new.html` | HTMX form, checkbox styling |
| `src/skriptoteket/web/templates/suggestions_review_detail.html` | HTMX form, conditional fields |
| `src/skriptoteket/web/templates/admin_tools.html` | HTMX actions |
| `src/skriptoteket/web/pages/auth.py` | HTMX-aware response |
| `src/skriptoteket/web/pages/suggestions.py` | HTMX-aware responses |
| `src/skriptoteket/web/pages/admin_tools.py` | HTMX-aware responses |

---

## HTMX Idioms Reference

### Detect HTMX Request (Python)

```python
from skriptoteket.web.pages.admin_scripting_support import is_hx_request, redirect_with_hx

if is_hx_request(request):
    return templates.TemplateResponse("partials/form.html", context)
return templates.TemplateResponse("full_page.html", context)
```

### Smart Redirect

```python
return redirect_with_hx(request=request, url="/success")
```

### OOB Swap (Multiple Elements)

```html
<div id="main-content">Updated content</div>
<div id="toast-container" hx-swap-oob="beforeend">
  <div class="huleedu-toast huleedu-toast-success">Saved!</div>
</div>
```

### Form with Loading State

```html
<form hx-post="/endpoint"
      hx-target="#form-container"
      hx-swap="outerHTML"
      hx-indicator="#submit-spinner">
  <button type="submit" class="huleedu-btn huleedu-btn-navy">
    <span id="submit-spinner" class="htmx-indicator huleedu-spinner huleedu-spinner-light"></span>
    Submit
  </button>
</form>
```

### Re-bind After HTMX Swap

```javascript
htmx.on('htmx:afterSettle', function() {
  bindDecisionToggle();
});
```

---

## Testing Checklist

For each form converted:

- [ ] Form submits without full page reload
- [ ] Loading indicator shows during request
- [ ] Error messages display inline
- [ ] Success feedback appears (toast or inline)
- [ ] Browser back/forward works correctly
- [ ] Form works without JavaScript (graceful degradation)
- [ ] Keyboard navigation works
- [ ] Screen reader announces changes

---

## Session Completion Requirements

When done, you MUST:

1. **Update documentation**:
   - Update `ref-vue-spa-migration-assessment.md` to note HTMX implementation status
   - Add new patterns to `.agent/rules/040-fastapi-blueprint.md` if significant

2. **Update handoff**:
   - Update `.agent/handoff.md` with what was implemented, decisions made, remaining work

3. **Create instruction for next developer**:
   - If work continues, create similar scoped instruction with remaining tasks

4. **Verify**:
   - `pdm run docs-validate`
   - `pdm run lint` and `pdm run typecheck`
   - `pdm run test`
