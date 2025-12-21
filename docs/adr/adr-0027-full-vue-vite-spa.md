---
type: adr
id: ADR-0027
title: "Full Vue/Vite SPA as the Skriptoteket frontend"
status: accepted
owners: "agents"
deciders: ["user-lead"]
created: 2025-12-21
links: ["PRD-spa-frontend-v0.1", "ADR-0001", "ADR-0025"]
---

## Context

Skriptoteket was designed to move quickly with a server-rendered Jinja2 UI and HTMX-style enhancements (ADR-0001).
Later, SPA “islands” were introduced for high-complexity surfaces only (ADR-0025).

We now want:

- A single frontend paradigm across the entire product (including admin/contributor flows).
- A frontend stack aligned with HuleEdu, but with Skriptoteket owning its component styling and UX consistency.
- A clean break migration (remove legacy templates and HTMX instead of maintaining two paradigms).

## Decision

### 1) Adopt a single Vue/Vite SPA for the full product surface

- Vue 3 (Composition API) + Vite for the primary UI.
- Vue Router handles all client-side navigation for existing route paths.
- Admin/contributor views live in the same SPA, protected by route guards and server-enforced authorization.

### 2) Make the SPA the default (and only) UI after cutover

- Cutover is a clean replacement: legacy Jinja2 templates, HTMX assets, and SSR page routes are removed after parity.
- No redirect strategy is required; the SPA serves the same paths as today and owns routing.

### 3) Keep the backend architecture and security posture

- Domain/application architecture stays protocol-first DI and remains framework-agnostic.
- Authentication remains server-side sessions (ADR-0009).
- SPA uses cookie-based sessions and CSRF protection for mutating requests (details in ADR-0030).
- No tool-provided UI JavaScript; the typed UI contract and allowlists remain the rendering boundary (ADR-0022).

### 4) Supersede prior UI-paradigm ADRs

- ADR-0001 (server-driven HTMX UI) is superseded by this decision.
- ADR-0025 (embedded SPA islands) is superseded by this decision.

## Consequences

### Benefits

- One coherent UI architecture (routing, state management, component composition).
- Removes long-term cost of maintaining both templates and SPA islands.
- Enables consistent UX improvements across all pages, not only “complex” surfaces.

### Tradeoffs / risks

- Larger initial migration effort with higher cutover risk (mitigate with route parity + E2E coverage).
- New frontend toolchain becomes a production dependency (mitigate with CI checks and deterministic builds).
