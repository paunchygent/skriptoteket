---
type: adr
id: ADR-SKRIPT-0032
title: 'Frontend styling: Tailwind CSS 4 with @theme design tokens'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: accepted
deciders:
- user-lead
retired_ids:
- ADR-0032
---

## Context

### Source: Context

ADR-0029 mandated pure CSS with design tokens, explicitly removing Tailwind from the frontend toolchain. The rationale
was that the HuleEdu design language is not a Tailwind-first design system, and pure CSS would provide clearer
alignment with the existing token-based styling.

However, Tailwind CSS 4 (released late 2024) introduced the `@theme` directive, which fundamentally changes the
trade-off:

- **CSS-first configuration**: No JavaScript config file needed; tokens are defined in CSS.
- **Native CSS variables**: Theme values become CSS custom properties available at runtime.
- **Generated utilities**: Tailwind automatically creates utility classes from `@theme` tokens.
- **Single source of truth**: HuleEdu tokens remain authoritative; Tailwind consumes them.

This enables using Tailwind's utility-class productivity while keeping the HuleEdu design tokens as the canonical
source.

## Decision

### Source: Decision

- Use **Tailwind CSS 4** with `@tailwindcss/vite` plugin for SPA styling.
- Bridge existing HuleEdu design tokens via `@theme inline` to generate Tailwind utilities.
- **Prefer Tailwind utility classes** over `<style scoped>` blocks in Vue components.
- Fall back to scoped CSS only for complex animations, pseudo-elements, or patterns not expressible in utilities.
- Keep the design language **token-driven**: avoid Tailwind default palette/spacing for product UI; use only mapped
  token utilities (e.g. `bg-canvas`, `text-navy`, `shadow-brutal-sm`) or CSS variables.

### Source: Token mapping (tailwind-theme.css)

```css
@theme inline {
  --color-paper: var(--huleedu-paper);
  --color-canvas: var(--huleedu-canvas);
  --color-navy: var(--huleedu-navy);
  --color-terracotta: var(--huleedu-terracotta);
  --color-action: var(--huleedu-action);
  --color-critical: var(--huleedu-critical);
  --color-burgundy: var(--huleedu-burgundy);
  --color-button-primary-text: var(--button-primary-text);
  --shadow-brutal: var(--huleedu-shadow-brutal-sm);
  /* ... */
}
```

This generates utilities like `bg-canvas`, `text-navy`, `text-action`, `text-critical`, `shadow-brutal`, etc.
`burgundy` remains as a compatibility alias for older call sites and should not be used for new functional
action states.

### Source: Implementation (Skriptoteket)

We keep tokens as the source of truth and use a small bridge to expose them to Tailwind:

```
src/skriptoteket/web/static/css/huleedu-design-tokens.css  ← canonical `--huleedu-*`
frontend/apps/skriptoteket/src/styles/tokens.css           ← import wrapper
frontend/apps/skriptoteket/src/styles/tailwind-theme.css   ← `@theme inline` bridge
frontend/apps/skriptoteket/src/assets/main.css             ← single Tailwind + tokens entry
```

`frontend/apps/skriptoteket/src/assets/main.css` should import Tailwind once, then tokens + theme bridge:

```css
@import "tailwindcss";
@import "../styles/tokens.css";
@import "../styles/tailwind-theme.css";
```

Tailwind v4 note: Vue SFC `<style>` blocks / CSS modules may not see theme/custom utility definitions from other files.
Prefer utilities in templates and CSS variables in custom CSS; if you must use `@apply` or custom utilities there, use
`@reference` per Tailwind v4 docs.

## Non-Decisions

The source does not provide a separate non-decisions section; no additional non-decisions is recorded.

## Consequences

### Source: Consequences

- **Faster development**: Utility classes reduce CSS authoring overhead.
- **Design tokens remain source of truth**: Imported from shared `huleedu-design-tokens.css`.
- **Consistent with HuleEdu design language**: No Tailwind defaults leak through; only mapped tokens are available.
- **Runtime theming possible**: CSS variables can be swapped at runtime (e.g., for dark mode).
- **Supersedes ADR-0029**: The "no Tailwind" stance is reversed; Tailwind 4's CSS-first approach addresses the original
  concerns.

### Source: Palette note (2026-05-04)

The HuleEdu working palette separates brand, action, and alert semantics:

- Deep Navy `#082B4C` is the structural and long-text color.
- Warm Terracotta `#C94F32` is the brand accent, not a warning or destructive color.
- Verdigris Teal `#3F7F78` is the functional action/selection/focus color, not a warning color.
- Canvas/Paper `#FAFAF6` is the light warm surface; avoid red/saturated default page backgrounds.
- Warning remains amber/ochra; destructive and truly critical actions remain on the burgundy/error-family channel.

Surface composition should use the light canvas as a uniform base rather than placing repeated white panels
on top of canvas. Prefer canvas-toned panels and lighter row/object highlights for emphasis, with pure white
reserved for deliberate object contrast.
