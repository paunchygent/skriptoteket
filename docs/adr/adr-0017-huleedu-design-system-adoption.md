---
type: adr
id: ADR-0017
title: "HuleEdu design system adoption for frontend harmonization"
status: proposed
owners: "agents"
deciders: ["user-lead"]
created: 2025-12-15
---

## Context

Skriptoteket will be integrated with HuleEdu, the main EdTech platform. The current Skriptoteket frontend uses minimal inline CSS with system fonts and lacks a cohesive design language. The planned HTMX UX enhancements (ref-htmx-ux-enhancement-plan.md) propose creating a generic CSS design system.

For seamless future integration with HuleEdu, Skriptoteket should adopt the HuleEdu design system instead of creating an independent design language. This ensures:

- Visual consistency when Skriptoteket becomes part of the HuleEdu ecosystem
- Reduced design debt and migration effort during integration
- Shared design vocabulary between development teams
- Brand coherence for end users

## Decision

Adopt the HuleEdu design system for all Skriptoteket frontend styling:

### Design Tokens

- **Colors**: Canvas (#F9F8F2), Navy (#1C2E4A), Burgundy (#6B1C2E)
- **Typography**: IBM Plex Sans/Serif/Mono via Google Fonts CDN
- **Shadows**: Brutalist style (hard offsets, no blur)
- **Layout**: Ledger frame pattern with 1px navy border

### Button Hierarchy

1. **Burgundy filled**: Primary CTA (e.g., "PUBLICERA")
2. **Navy filled**: Functional actions (e.g., "LOGGA IN", "SPARA")
3. **Navy outline**: Secondary actions (e.g., "AVBRYT")
4. **Text link**: Navigation with arrow indicator

### Status Indicators

- Burgundy dot: Requires action / active
- Navy dot: OK / published / stable
- Gray dot: Inactive / empty

### Toast Notifications

- Info: Navy background
- Success: Pine green background (`--huleedu-success`)
- Warning: Amber background (`--huleedu-warning`)
- Failure: Burgundy background
- Validation + blocking states: inline near the cause (not toast)

### Implementation

- Store full HuleEdu design tokens in `static/css/huleedu-design-tokens.css`
- Application-specific extensions in `static/css/app.css`
- All components use `huleedu-*` prefixed CSS classes

## Consequences

**Benefits**:

- Immediate visual coherence with HuleEdu product family
- Design tokens serve as single source of truth for both projects
- Reduced rework when integrating Skriptoteket into HuleEdu
- Professional, consistent appearance from day one

**Tradeoffs**:

- Dependency on external design tokens file (must stay in sync)
- Google Fonts CDN dependency for IBM Plex family
- Slightly larger CSS payload compared to minimal generic system

**Mitigations**:

- Version the design tokens file; update deliberately when HuleEdu evolves
- Preconnect hints for Google Fonts minimize latency
- CSS is still lightweight (~15KB uncompressed)
