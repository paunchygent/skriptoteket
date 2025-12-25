---
id: "045-huleedu-design-system"
type: "implementation"
created: 2025-12-15
updated: 2025-12-25
scope: "frontend"
references:
  - ADR-0027
  - ADR-0032
  - EPIC-11
---

# 045: HuleEdu Design System (SPA Edition)

Skriptoteket adopts the HuleEdu Brutalist design system. This document covers the **Vue 3 SPA implementation** using Tailwind CSS v4 with `@theme` design tokens.

> **Legacy SSR/HTMX**: Cutover is complete (EPIC-11). SSR/HTMX is deleted; do not re-introduce it.

---

## 0. Styling Rules (Alignment)

These rules keep our docs, skills, and implementation aligned (ADR-0032):

- **Tokens-first**: do not hardcode hex colors/spacing/shadows in Vue markup or CSS. Prefer mapped utilities
  (`bg-canvas`, `text-navy`, `shadow-brutal-sm`, etc.) or CSS variables (`var(--color-*)`, `var(--huleedu-*)`).
- **No Tailwind defaults leakage**: avoid Tailwind’s default palette/spacing in product UI; the design language must come
  from HuleEdu tokens via the theme bridge.
- **Single CSS entry point**: `frontend/apps/skriptoteket/src/assets/main.css` is the SPA styling entry. Import Tailwind,
  tokens, and the theme bridge there; do not sprinkle extra Tailwind imports elsewhere.
- **Keep the bridge minimal**: `tailwind-theme.css` should map `--huleedu-*` → Tailwind theme vars via `@theme inline`,
  not introduce new bespoke design constants.
- **Vue `<style>` blocks**: prefer Tailwind utilities in templates. If custom CSS is unavoidable, prefer CSS variables.
  Tailwind v4 note: separately bundled CSS (Vue SFC `<style>`, CSS modules) may not see theme/custom utilities; avoid
  `@apply` unless necessary, and use `@reference` when you must apply shared utilities.

---

## 1. Token Architecture

```
src/skriptoteket/web/static/css/huleedu-design-tokens.css  ← Canonical HuleEdu tokens
        ↓ (imported by)
frontend/apps/skriptoteket/src/styles/tokens.css           ← SPA import wrapper
        ↓ (consumed by)
frontend/apps/skriptoteket/src/styles/tailwind-theme.css   ← @theme mapping to Tailwind
        ↓ (imported by)
frontend/apps/skriptoteket/src/assets/main.css             ← App entry point
```

**Rule**: Never modify `huleedu-design-tokens.css` directly. It is the shared source of truth with HuleEdu.

---

## 2. Tailwind Theme Mapping

The `@theme inline` block in `tailwind-theme.css` maps HuleEdu tokens to Tailwind utilities:

```css
@theme inline {
  /* Fonts */
  --font-sans: var(--huleedu-font-sans);
  --font-serif: var(--huleedu-font-serif);
  --font-mono: var(--huleedu-font-mono);

  /* Core brand colors → use as text-navy, bg-burgundy, etc. */
  --color-canvas: var(--huleedu-canvas);
  --color-navy: var(--huleedu-navy);
  --color-burgundy: var(--huleedu-burgundy);

  /* Feedback colors */
  --color-success: var(--huleedu-success);
  --color-warning: var(--huleedu-warning);
  --color-error: var(--huleedu-error);

  /* Shadows → use as shadow-brutal-sm */
  --shadow-brutal: var(--huleedu-shadow-brutal-sm);      /* 4px offset */
  --shadow-brutal-sm: var(--huleedu-shadow-brutal-xs);   /* 2px offset */
}
```

**Usage in Vue templates**:
```vue
<div class="bg-canvas text-navy border border-navy shadow-brutal-sm">
  Content with HuleEdu tokens via Tailwind
</div>
```

---

## 3. Color System

| Token | Tailwind Class | Hex | Usage |
|-------|----------------|-----|-------|
| `--huleedu-canvas` | `bg-canvas`, `text-canvas` | #FAFAF6 | Background, button text on dark |
| `--huleedu-navy` | `bg-navy`, `text-navy`, `border-navy` | #1C2E4A | Primary text, borders, functional buttons |
| `--huleedu-burgundy` | `bg-burgundy`, `text-burgundy` | #6B1C2E | CTA accent, errors, publish actions |
| `--huleedu-success` | `text-success`, `border-success` | #059669 | Success states |
| `--huleedu-warning` | `text-warning`, `bg-warning/20` | #D97706 | Attention, pending review |
| `--huleedu-error` | `text-error` | #DC2626 | Error states |

**Opacity variants**: Use Tailwind opacity syntax: `text-navy/60`, `bg-burgundy/10`, `border-navy/20`

---

## 4. Button Patterns (Brutalist)

Use the shared SPA button primitives (defined in `frontend/apps/skriptoteket/src/assets/main.css`).
These standardize hover + press depth and reduce drift:

| Variant | Class | Default | Hover | Press |
|---------|-------|---------|-------|-------|
| Standard button | `btn-primary` | Navy | Burgundy fill | 4px |
| Critical CTA | `btn-cta` | Burgundy | Burgundy highlight (no navy fill) | 4px |
| No-fill table/action | `btn-ghost` | White/no-fill | Canvas fill + amber highlight | 4px |

Notes:

- Hover styles are gated behind `@media (hover: hover) and (pointer: fine)` to avoid sticky hover on touch devices.
- Do **not** use amber highlight on `btn-primary` / `btn-cta`.

### Examples

```vue
<button class="btn-primary">Spara</button>
<button class="btn-cta">Publicera</button>
<button class="btn-ghost">Redigera</button>
```

### Async (spinner) button

```vue
<button class="btn-cta" :disabled="isRunning">
  <span
    v-if="isRunning"
    class="inline-block w-3 h-3 border-2 border-canvas/30 border-t-canvas rounded-full animate-spin"
  />
  <span v-else>Kör</span>
</button>
```

---

## 5. Form Elements

### Input Field
```vue
<input class="w-full border border-navy bg-white px-3 py-2 text-sm text-navy shadow-brutal-sm"
       placeholder="T.ex. värde..." />
```

### Label
```vue
<label class="text-xs font-semibold uppercase tracking-wide text-navy/70">
  Fältnamn
</label>
```

### Input with Label (Stacked)
```vue
<div class="space-y-1">
  <label class="text-xs font-semibold uppercase tracking-wide text-navy/70">
    Ändringssammanfattning
  </label>
  <input v-model="value"
         class="w-full border border-navy bg-white px-3 py-2 text-sm text-navy shadow-brutal-sm"
         placeholder="T.ex. fixade bugg..." />
</div>
```

---

## 6. Cards and Containers

### Card with Shadow
```vue
<div class="border border-navy bg-white shadow-brutal-sm p-4">
  Card content
</div>
```

### Section Card (larger padding)
```vue
<div class="border border-navy bg-white shadow-brutal-sm p-5 space-y-3">
  Section content
</div>
```

### Error Message
```vue
<div class="p-4 border border-burgundy bg-white shadow-brutal-sm text-sm text-burgundy">
  {{ errorMessage }}
</div>
```

### Success Message
```vue
<div class="p-4 border border-success bg-success/10 shadow-brutal-sm text-sm text-success">
  {{ successMessage }}
</div>
```

---

## 7. List Patterns

### Standard List
```vue
<ul class="list-none m-0 p-0 border border-navy bg-white">
  <li v-for="item in items"
      :key="item.id"
      class="border-b border-navy/20 last:border-b-0">
    <div class="flex justify-between items-center p-4 hover:bg-canvas transition-colors">
      <span class="font-medium text-navy">{{ item.title }}</span>
      <RouterLink :to="item.href" class="...button classes...">
        Öppna
      </RouterLink>
    </div>
  </li>
</ul>
```

### List Item with Description
```vue
<li class="border-b border-navy/20 last:border-b-0">
  <div class="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-3 sm:gap-4 p-4">
    <div class="flex flex-col gap-1 min-w-0">
      <span class="font-medium text-navy">{{ item.title }}</span>
      <span class="text-sm text-navy/60 break-words">{{ item.summary }}</span>
    </div>
    <RouterLink class="shrink-0 ...button classes...">
      Kör
    </RouterLink>
  </div>
</li>
```

---

## 8. Loading & Empty States

### Loading Spinner
```vue
<div class="flex items-center gap-3 p-4 text-navy/60">
  <span class="inline-block w-4 h-4 border-2 border-navy/20 border-t-navy rounded-full animate-spin" />
  <span>Laddar...</span>
</div>
```

### Empty State
```vue
<div class="p-4 text-navy/60 italic">
  Inga verktyg hittades.
</div>
```

---

## 9. Typography Patterns

### Page Title
```vue
<h1 class="text-2xl font-semibold text-navy">
  Sidtitel
</h1>
```

### Section Label
```vue
<h2 class="text-xs font-semibold uppercase tracking-wide text-navy/70 mb-3">
  Sektionsrubrik
</h2>
```

### Status Line (IDE-style)
```vue
<p class="text-sm font-medium text-navy/70">
  Ej publicerad · v4 · Utkast
</p>
```

### Breadcrumb
```vue
<nav class="flex items-center flex-wrap gap-2 text-xs uppercase tracking-wide text-navy/60">
  <RouterLink to="/browse" class="text-navy/70 border-b border-navy/40 pb-0.5 hover:text-burgundy hover:border-burgundy transition-colors">
    Yrkesgrupper
  </RouterLink>
  <span class="text-navy/30">/</span>
  <span>Current Page</span>
</nav>
```

---

## 10. Modal & Drawer Patterns

### Modal Backdrop + Container
```vue
<Teleport to="body">
  <Transition name="fade">
    <div v-if="isOpen"
         class="fixed inset-0 z-50 flex items-center justify-center bg-navy/40"
         role="dialog" aria-modal="true"
         @click.self="close">
      <div class="relative w-full max-w-lg mx-4 p-6 bg-canvas border border-navy shadow-brutal">
        <!-- Modal content -->
      </div>
    </div>
  </Transition>
</Teleport>
```

### Fade Transition
```css
.fade-enter-active,
.fade-leave-active {
  transition: opacity var(--huleedu-duration-default) var(--huleedu-ease-default);
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
```

### Right Drawer
```vue
<div class="fixed inset-y-0 right-0 w-full max-w-md border-l border-navy bg-canvas shadow-brutal overflow-y-auto">
  <!-- Drawer content -->
</div>
```

---

## 11. Status Badges

### Workflow State Badge
```vue
<span class="px-2 py-0.5 text-xs font-semibold uppercase tracking-wide border"
      :class="{
        'border-burgundy text-burgundy': state === 'active',
        'border-warning text-warning': state === 'in_review',
        'border-navy/40 text-navy/70': state === 'draft' || state === 'archived'
      }">
  {{ stateLabel }}
</span>
```

### Warning Badge (Pending Review)
```vue
<span class="inline-block px-2 py-1 text-xs font-medium bg-warning/20 text-warning border border-warning">
  Granskas
</span>
```

---

## 12. Grid Background

The 24px baseline grid is applied globally via `main.css`:

```css
body::before {
  content: '';
  position: fixed;
  inset: 0;
  background-image:
    linear-gradient(var(--huleedu-navy) 1px, transparent 1px),
    linear-gradient(90deg, var(--huleedu-navy) 1px, transparent 1px);
  background-size: var(--huleedu-grid-size) var(--huleedu-grid-size);
  opacity: 0.04;
  pointer-events: none;
  z-index: -1;
}
```

---

## 13. Vue Composable Patterns

### State Management
Use Pinia stores for global state, composables for component-scoped logic:

```typescript
// composables/editor/useScriptEditor.ts
export function useScriptEditor(options: UseScriptEditorOptions) {
  const isLoading = ref(true);
  const errorMessage = ref<string | null>(null);
  // ... logic
  return { isLoading, errorMessage, ... };
}
```

### API Calls
Use typed API client with error handling:

```typescript
import { apiGet, isApiError } from "../api/client";

try {
  const response = await apiGet<ListToolsResponse>("/api/v1/tools");
  tools.value = response.tools;
} catch (error: unknown) {
  if (isApiError(error)) {
    errorMessage.value = error.message;
  } else {
    errorMessage.value = "Det gick inte att ladda verktygen.";
  }
}
```

---

## 14. File Size Rule

All Vue files must be **<500 LoC**. Extract logic to composables, UI to child components.

---

## 15. Anti-Patterns (DO NOT)

| Don't | Do Instead |
|-------|------------|
| Scoped BEM CSS (`.my-component__item`) | Tailwind utility classes |
| Inline `style` attributes | Tailwind classes or CSS variables |
| English error messages | Swedish: "Det gick inte att..." |
| `rounded-sm` on buttons | Remove radius or use brutalist aesthetic |
| Ad-hoc feedback colors | Toasts: `info=navy`, `success=--huleedu-success`, `warning=--huleedu-warning`, `failure=burgundy` (90% opacity); validation/blocking errors stay inline |
| Custom `@keyframes` in `<style>` | Use `animate-spin`, `animate-pulse` utilities |

---

## 16. Reference Files

| Purpose | File |
|---------|------|
| Canonical tokens | `src/skriptoteket/web/static/css/huleedu-design-tokens.css` |
| Tailwind theme | `frontend/apps/skriptoteket/src/styles/tailwind-theme.css` |
| App entry CSS | `frontend/apps/skriptoteket/src/assets/main.css` |
| Well-aligned view | `frontend/apps/skriptoteket/src/views/admin/ScriptEditorView.vue` |
| List pattern | `frontend/apps/skriptoteket/src/views/admin/AdminToolsView.vue` |
