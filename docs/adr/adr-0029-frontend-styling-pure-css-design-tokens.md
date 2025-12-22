---
type: adr
id: ADR-0029
title: "Frontend styling: pure CSS design tokens (no Tailwind)"
status: superseded
superseded_by: ["ADR-0032"]
owners: "agents"
deciders: ["user-lead"]
created: 2025-12-21
links: ["ADR-0017", "ADR-0027", "PRD-spa-frontend-v0.1"]
---

## Context

Skriptoteket already includes a HuleEdu-aligned design token and component-class layer in CSS (ADR-0017).
The current SPA island toolchain uses Tailwind (dev dependency) for local experiments, but the HuleEdu design language is
not a Tailwind-first design system.

We want the component library (`@huleedu/ui`) to fully own its styling and stay faithful to the existing tokens and
class semantics.

## Decision

- Use **pure CSS** (design tokens + component class styling) as the primary styling approach.
- Remove Tailwind as a dependency from the frontend toolchain as part of the migration.
- Package tokens + base styles into the UI library so the SPA can import a single, versioned styling surface.

## Consequences

- More explicit CSS authoring and maintenance (no utility framework shortcuts).
- Clearer alignment with HuleEdu’s existing token-based styling language.
- Lower risk of global Tailwind resets/utility leakage across the app.
