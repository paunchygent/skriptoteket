---
type: adr
id: ADR-0032
title: "Frontend styling: Tailwind CSS 4 with @theme design tokens"
status: accepted
owners: "agents"
deciders: ["user-lead"]
created: 2025-12-22
supersedes: ["ADR-0029"]
links: ["ADR-0017", "ADR-0027", "ADR-0029"]
---

## Context

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

- Use **Tailwind CSS 4** with `@tailwindcss/vite` plugin for SPA styling.
- Bridge existing HuleEdu design tokens via `@theme inline` to generate Tailwind utilities.
- **Prefer Tailwind utility classes** over `<style scoped>` blocks in Vue components.
- Fall back to scoped CSS only for complex animations, pseudo-elements, or patterns not expressible in utilities.

### Token mapping (tailwind-theme.css)

```css
@theme inline {
  --color-canvas: var(--huleedu-canvas);
  --color-navy: var(--huleedu-navy);
  --color-burgundy: var(--huleedu-burgundy);
  --shadow-brutal: var(--huleedu-shadow-brutal-sm);
  /* ... */
}
```

This generates utilities like `bg-canvas`, `text-navy`, `text-burgundy`, `shadow-brutal`, etc.

## Consequences

- **Faster development**: Utility classes reduce CSS authoring overhead.
- **Design tokens remain source of truth**: Imported from shared `huleedu-design-tokens.css`.
- **Consistent with HuleEdu design language**: No Tailwind defaults leak through; only mapped tokens are available.
- **Runtime theming possible**: CSS variables can be swapped at runtime (e.g., for dark mode).
- **Supersedes ADR-0029**: The "no Tailwind" stance is reversed; Tailwind 4's CSS-first approach addresses the original
  concerns.
