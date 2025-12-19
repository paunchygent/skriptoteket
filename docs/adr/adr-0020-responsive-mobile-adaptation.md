---
type: adr
id: ADR-0020
title: "Responsive mobile adaptation strategy"
status: accepted
owners: "agents"
deciders: ["user-lead"]
created: 2025-12-18
---

## Context

Skriptoteket's frontend was developed with desktop-first assumptions. Three critical usability issues have been identified on smaller screens (tablets and phones):

1. **Header navigation inaccessible** – `flex-wrap: nowrap` causes nav items to overflow horizontally on viewports <768px
2. **CodeMirror collapses** – `min-height: 0` combined with flex shrink causes the editor to shrink to zero height
3. **Script editor two-column layout broken** – Fixed 320px sidebar leaves insufficient space for main content on narrow screens

The primary user base (teachers) uses desktop/laptop browsers, but mobile/tablet access is expected for browsing and lightweight tasks.

## Decision

Adopt an **adaptive mobile strategy** (Option A from analysis) rather than a full mobile-first rewrite:

### Breakpoint Standardization

Define consistent breakpoints in design tokens:

| Token | Value | Usage |
|-------|-------|-------|
| `--huleedu-bp-sm` | 640px | Compact mobile adjustments |
| `--huleedu-bp-md` | 768px | Tablet/header collapse |
| `--huleedu-bp-lg` | 1024px | Editor layout collapse |

**Note:** Plain CSS `@media` queries cannot reference CSS custom properties. Until a CSS build step is introduced (e.g. via `@custom-media`), media queries will continue to use literal pixel values; the tokens are for documentation consistency and potential JS usage.

### Header Adaptation

- Add collapsible hamburger menu at `<768px`
- Navigation links move to a dropdown panel (simple, minimal JS)
- Brand logo and logout remain visible

### Accessibility

- Hamburger control is a real `<button>` with `aria-expanded` and `aria-controls`
- Mobile menu remains keyboard-operable (focusable controls, visible focus)

### CodeMirror Floor

- Enforce `min-height: 250px` on `.huleedu-editor-textarea-wrapper`
- Prevents collapse regardless of flex context

### Editor Layout Adaptation

- At `<1024px`: stack columns vertically
- Sidebar appears **above** main content (critical controls accessible without scrolling)
- Alternative: collapsible accordion sections for sidebar on mobile

### Touch Targets

- Audit all interactive elements for 44×44px minimum
- Add `.huleedu-btn-touch` variant if needed for mobile contexts

## Consequences

**Benefits**:

- Fixes critical usability issues on mobile/tablet
- Incremental changes, low regression risk
- Follows existing HuleEdu design patterns
- No new dependencies or architectural changes

**Tradeoffs**:

- Not a "mobile-first" approach – desktop remains primary design target
- Hamburger menu requires ~20 lines of JavaScript
- Some features (CodeMirror editing) remain suboptimal on mobile

**Risks / mitigations**:

- **CSS/JS coupling**: If mobile nav is hidden via CSS and JS fails, navigation can become inaccessible → mitigate with progressive enhancement (e.g. hide only when JS has initialized, or use a no-JS-friendly pattern like `<details>`).
- **HTMX navigation**: `hx-boost` swaps page content on link navigation → ensure any menu-open state does not block navigation events.
- **Mobile viewport dynamics**: On-screen keyboards and small landscape heights can stress editor layout → test with keyboard open and in landscape.

**Why not mobile-first rewrite?**

- Primary users are desktop-based teachers
- CodeMirror code editing is inherently desktop-centric
- Existing ~400 LOC CSS would need full rewrite with marginal UX improvement
- HuleEdu design system itself appears desktop-first

## Related

- ADR-0001: Server-driven HTMX UI approach
- ADR-0017: HuleEdu design system adoption
- EPIC-05: HuleEdu design harmonization
