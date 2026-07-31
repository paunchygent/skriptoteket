---
type: reference
id: REF-SKRIPT-GENERAL-reference-toasts-and-system-messages-spa
title: 'Reference: Toasts and system messages (SPA)'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: active
reference_kind: general
retired_ids:
- REF-toast-system-messages
summary: 'Reference: Toasts and system messages (SPA)'
---

## Overview

The source does not provide a separate overview section; no additional overview is recorded.

## Facts And Semantics

The source does not provide a separate facts and semantics section; no additional facts and semantics is recorded.

### Source: Overview (what goes where)

| Kind | Use for | Lives where | Notes |
|------|---------|-------------|-------|
| **Toast** | transient action feedback (save/publish/submit) | overlay (fixed) | should not move layout |
| **Inline error** | validation + blocking states | in flow | sticky + dismissible (`×`) |
| **Typed UI outputs** | tool-run results (`notice`, `table`, `markdown`, etc.) | results area | not “toasts” |

See ADR-0037 for the decision and EPIC-13 for execution.

### Source: Toasts (standard)



### Source: When to use

Use a toast for feedback that is:

- triggered by a user action (button click / submit)
- meaningful but non-blocking (the user can keep working)
- expected to disappear automatically

Examples: “Sparat.”, “Version publicerad.”, “Inställningar sparade.”, “Kunde inte spara.”

### Source: When NOT to use

Do not use toasts for:

- initial page load failures (blocking state)
- validation errors tied to specific inputs
- tool-run errors/results that belong in the results timeline

### Source: Visual + semantics

Toasts are **overlay cards** with an icon + message, and **never push content**.

| Variant | Use for | Background | Icon |
|---------|---------|------------|------|
| `info` | neutral status | navy (90% opacity) | `i` / dot |
| `success` | completed positive outcome | pine green (`--huleedu-success`, 90% opacity) | check |
| `warning` | caution, attention | amber (`--huleedu-warning`, 90% opacity) | warning |
| `failure` | action did not complete | warm terracotta (`--huleedu-terracotta`, 90% opacity) | × |

Recommended durations (auto-dismiss):

- `info`: 6s
- `success`: 6s
- `warning`: 10s
- `failure`: 12s

All toast variants include a close (`×`) control.

### Source: Implementation contract (SPA)

The toast system is implemented per ADR-0037:

- a single toast host mounted once in the app shell (Teleport to `body`)
- a single API (`useToast()`) backed by global state
- styling primitives defined in `frontend/apps/skriptoteket/src/assets/main.css`

### Source: Inline errors (standard)

Inline errors remain the right choice for:

- blocking errors (cannot load required data)
- form-level validation that should remain visible near inputs
- system blocking states (e.g. lockouts / throttling)

Inline errors:

- are sticky until dismissed (no auto-dismiss)
- include a close (`×`) control
- should appear as close as possible to what caused the error (e.g. login errors inside `LoginModal.vue`)

### Source: UI primitives map (source-of-truth pointers)

This table is the “where do I change X?” map for the most common UI primitives.

| Primitive | Source of truth | Notes |
|----------|------------------|-------|
| Buttons | `frontend/apps/skriptoteket/src/assets/main.css` (`.btn-primary`, `.btn-cta`, `.btn-ghost`) | No ad-hoc button styling in templates |
| Fonts + tokens | `src/skriptoteket/web/static/css/huleedu-design-tokens.css` + `frontend/apps/skriptoteket/src/styles/tailwind-theme.css` | Tokens are canonical; Tailwind maps them via `@theme` |
| Grid background | `frontend/apps/skriptoteket/src/assets/main.css` (`body::before`) | Uses `--huleedu-grid-size` |
| Tables | `frontend/apps/skriptoteket/src/components/ui-outputs/UiOutputTable.vue` | Canonical table output style |
| Animations | Prefer Tailwind utilities (`animate-spin`) + Vue `Transition` CSS in components | Avoid custom keyframes unless necessary |
| Toasts + system messages | ADR-0037 + EPIC-13 + this doc | Implement as primitives + shared API |

## Decisions And Interpretation

The source does not provide a separate decisions and interpretation section; no additional decisions and interpretation is recorded.
