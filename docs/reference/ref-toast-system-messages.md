---
type: reference
id: REF-toast-system-messages
title: "Reference: Toasts and system messages (SPA)"
status: active
owners: "agents"
created: 2025-12-25
topic: "frontend-ui-feedback"
links:
  - ADR-0037
  - EPIC-13
  - ST-13-01
  - ADR-0032
---

This document defines **how Skriptoteket SPA communicates feedback** (success/error/warnings) to users without causing
layout shifts, and how this aligns with the broader HuleEdu UI primitives.

## Overview (what goes where)

| Kind | Use for | Lives where | Notes |
|------|---------|-------------|-------|
| **Toast** | transient action feedback (save/publish/submit) | overlay (fixed) | should not move layout |
| **Inline error** | validation + blocking states | in flow | sticky + dismissible (`×`) |
| **Typed UI outputs** | tool-run results (`notice`, `table`, `markdown`, etc.) | results area | not “toasts” |

See ADR-0037 for the decision and EPIC-13 for execution.

## Toasts (standard)

### When to use

Use a toast for feedback that is:

- triggered by a user action (button click / submit)
- meaningful but non-blocking (the user can keep working)
- expected to disappear automatically

Examples: “Sparat.”, “Version publicerad.”, “Inställningar sparade.”, “Kunde inte spara.”

### When NOT to use

Do not use toasts for:

- initial page load failures (blocking state)
- validation errors tied to specific inputs
- tool-run errors/results that belong in the results timeline

### Visual + semantics

Toasts are **overlay cards** with an icon + message, and **never push content**.

| Variant | Use for | Background | Icon |
|---------|---------|------------|------|
| `info` | neutral status | navy (90% opacity) | `i` / dot |
| `success` | completed positive outcome | pine green (`--huleedu-success`, 90% opacity) | check |
| `warning` | caution, attention | amber (`--huleedu-warning`, 90% opacity) | warning |
| `failure` | action did not complete | burgundy (90% opacity) | × |

Recommended durations (auto-dismiss):

- `info`: 6s
- `success`: 6s
- `warning`: 10s
- `failure`: 12s

All toast variants include a close (`×`) control.

### Implementation contract (SPA)

The toast system is implemented per ADR-0037:

- a single toast host mounted once in the app shell (Teleport to `body`)
- a single API (`useToast()`) backed by global state
- styling primitives defined in `frontend/apps/skriptoteket/src/assets/main.css`

## Inline errors (standard)

Inline errors remain the right choice for:

- blocking errors (cannot load required data)
- form-level validation that should remain visible near inputs
- system blocking states (e.g. lockouts / throttling)

Inline errors:

- are sticky until dismissed (no auto-dismiss)
- include a close (`×`) control
- should appear as close as possible to what caused the error (e.g. login errors inside `LoginModal.vue`)

## UI primitives map (source-of-truth pointers)

This table is the “where do I change X?” map for the most common UI primitives.

| Primitive | Source of truth | Notes |
|----------|------------------|-------|
| Buttons | `frontend/apps/skriptoteket/src/assets/main.css` (`.btn-primary`, `.btn-cta`, `.btn-ghost`) | No ad-hoc button styling in templates |
| Fonts + tokens | `src/skriptoteket/web/static/css/huleedu-design-tokens.css` + `frontend/apps/skriptoteket/src/styles/tailwind-theme.css` | Tokens are canonical; Tailwind maps them via `@theme` |
| Grid background | `frontend/apps/skriptoteket/src/assets/main.css` (`body::before`) | Uses `--huleedu-grid-size` |
| Tables | `frontend/apps/skriptoteket/src/components/ui-outputs/UiOutputTable.vue` | Canonical table output style |
| Animations | Prefer Tailwind utilities (`animate-spin`) + Vue `Transition` CSS in components | Avoid custom keyframes unless necessary |
| Toasts + system messages | ADR-0037 + EPIC-13 + this doc | Implement as primitives + shared API |
