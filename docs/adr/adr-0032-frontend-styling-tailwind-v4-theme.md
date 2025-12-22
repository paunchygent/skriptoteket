---
type: adr
id: ADR-0032
title: "Frontend styling: Tailwind v4 theme + HuleEdu design tokens"
status: accepted
owners: "agents"
deciders: ["user-lead"]
created: 2025-12-22
links: ["ADR-0017", "ADR-0027", "PRD-spa-frontend-v0.1", "ADR-0029"]
---

## Context

Skriptoteket’s UI should stay aligned with HuleEdu’s design system contract (ADR-0017): **CSS design tokens** are the
source of truth for colors, typography, spacing, and shadows.

We also need a styling approach that:

- scales to many SPA routes quickly (EPIC-11),
- stays modular and reusable across tool runs, my-runs, and curated apps,
- remains compatible with future HuleEdu integration (same login surface + shared look/feel),
- keeps “what to show” (typed outputs; ADR-0022/0024) separate from “how it looks”.

## Decision

Adopt **Tailwind CSS v4** in the SPA as a utility layer, backed by **HuleEdu design tokens**.

- **Tokens remain canonical**: define and maintain HuleEdu tokens as plain CSS variables (`--huleedu-*`).
- **Tailwind consumes tokens via theme variables**:
  - Keep a small bridging file that maps `--huleedu-*` → Tailwind theme vars (`--color-*`, `--font-*`, `--shadow-*`)
    using Tailwind v4 `@theme inline`.
- **Tailwind-first UI authoring**:
  - Prefer Tailwind utilities (`bg-canvas`, `text-navy`, `border-navy`, `shadow-brutal`, `font-sans`, etc.)
  - Avoid `<style scoped>` blocks except when unavoidable (complex animations or pseudo-elements).
- **No bespoke color constants**: UI components should not hardcode hex values for the core design language.

## Consequences

### Benefits

- Faster iteration for route parity (layout and state-heavy views).
- Clear modular styling surface: tokens define the design language; Tailwind defines composition.
- Easier reuse across “tool results”, “my-runs”, and curated apps because component styles are utility-based and
  token-driven.

### Tradeoffs / Risks

- Requires discipline to keep the theme bridge minimal and avoid ad-hoc utilities that bypass tokens.
- The design system contract must be kept stable (token renames are breaking changes).

