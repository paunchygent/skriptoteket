# Brutalist Academic UI Fundamentals

**Responsibility**: Core convictions and WHY decisions.

---

## 0. Skriptoteket Constraints (must follow)

- Vue 3 + Vite SPA; SSR/HTMX removed.
- Tailwind CSS v4 with `@theme inline` token bridge; prefer utilities in templates.
- Single CSS entry: `frontend/apps/skriptoteket/src/assets/main.css`.
- Token source of truth: `src/skriptoteket/web/static/css/huleedu-design-tokens.css` (do not edit).
- Use SPA primitives in `frontend/apps/skriptoteket/src/assets/main.css` for buttons, toasts, system messages, and
  status pills.
- No Tailwind default palette leakage (e.g. `bg-slate-*`, `text-gray-*`) in product UI.

---

## 1. The Grid Is Sacred

The grid is the skeleton. Not a suggestion.

- Use CSS Grid (Tailwind `grid`) for structural layout; use flex for 1‑dimensional alignment.
- Baseline grid exists globally (24px background grid); keep layout rhythm consistent with the 4px spacing scale.
- For editor-like routes (CodeMirror, drawers), enforce full-height layouts with `min-h-0` + explicit scroll regions.

```vue
<section class="grid grid-cols-12 gap-6">
  <aside class="col-span-12 lg:col-span-3">Filter</aside>
  <main class="col-span-12 lg:col-span-9">Content</main>
</section>
```

---

## 2. Typography Is The Interface

Type does 80% of the work. The interface is a reading environment.

### Font Stack

Use the token-mapped Tailwind font utilities:

- UI: `font-sans`
- Titles: `font-serif`
- Code/IDs: `font-mono`

### Micro-typography (editor/toolbars)

In dense “IDE” surfaces, use a deliberate micro scale:

- Labels: `text-[10px] font-semibold uppercase tracking-wide text-navy/60`
- Controls: `h-[28px]` with `text-[11px]` inputs/selects

---

---

## 3. Color Is Information

Color has semantic meaning or it doesn't exist.

### Use

- `bg-canvas` for app background
- `bg-white` for “paper” surfaces (cards/panels)
- `text-navy` for primary text; `text-navy/60`–`/80` for secondary
- `bg-burgundy` for critical CTA; `text-burgundy` for emphasis/errors
- `text-success`, `text-warning`, `text-error` for state

---

## 4. Hard Frames, Hard Shadows

Brutalist = hard edges. Academic = clear delineation.

```vue
<div class="border border-navy bg-white shadow-brutal-sm p-4">
  Card content
</div>
```

Rules of thumb:

- Prefer borders + brutal shadows (`shadow-brutal`, `shadow-brutal-sm`) over blurred shadows.
- Only the outermost surface gets a brutal shadow; nested panels/fields use `shadow-none` and thicker, uniform borders to
  avoid “stacked shadow” noise.
- Avoid large radii; brutalist surfaces are squared-off or minimally rounded.
- Don’t translate/scale hard-edged cards/panels on hover; prefer color/underline/opacity.

---

## 5. Whitespace Is Structure

Whitespace is architecture, not empty space.

- Tailwind spacing utilities are acceptable (4px base scale). Use token variables when you need exact semantic values
  (safe areas, sidebar widths, max widths).
- Section spacing > element spacing; keep consistent rhythm across screens.

---

## 6. No Decoration Without Function

Every visual element must do something.

### Banned

- Decorative gradients and blobs
- Soft shadows/backdrop blur
- Motion that doesn’t communicate state

### Allowed

- Borders and dividers
- Underlines to show interactivity
- Loading indicators (`animate-spin`) and clear state colors

---

## 7. Interactions Are Honest

Hover states communicate "this is interactive."

No bounces. No 3D transforms. No `scale(1.05)`. The user clicked a button, not launched a rocket.

Also:

- Hover styles should be gated for fine pointers to avoid sticky hover on touch devices.
- Prefer opacity-only transitions around hard shadows/borders (see route cross-fades in `main.css`).

---

## Success Criteria

A successful brutalist/academic interface:

1. Shows hierarchy through typography and structure (not decoration)
2. Uses tokens consistently (no hex, no default palettes)
3. Keeps hard edges stable (no shimmering transforms)
4. Keeps editor routes readable (width, full-height, right-side drawer surfaces)
5. Respects attention: fewer, clearer elements
