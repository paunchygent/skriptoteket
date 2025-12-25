---
type: epic
id: EPIC-13
title: "SPA feedback: toast + system messages"
status: active
owners: "agents"
created: 2025-12-25
outcome: "All major user/admin actions provide consistent, non-layout-shifting feedback via a shared toast overlay, while blocking/long-lived states use standardized inline system messages."
dependencies: ["ADR-0037", "ADR-0032"]
---

## Scope

- Introduce a single toast system for transient action feedback (ADR-0037):
  - Global toast host mounted once in the SPA shell.
  - Shared API (`useToast()`) for success/error/info/warning messages.
  - Styling primitives in `frontend/apps/skriptoteket/src/assets/main.css` using HuleEdu tokens.
- Replace layout-shifting inline success/error blocks in key flows with toasts.
- Standardize remaining inline “system messages” used for blocking/long-lived states.
- Document the system and mapping in `REF-toast-system-messages`.

## Out of scope

- Typed UI contract outputs (e.g. `UiOutputNotice`, tables, markdown) rendered as part of run results.
- Introducing new runner/output message kinds.

## Stories

- [ST-13-01: Toast system primitives (SPA)](../stories/story-13-01-toast-system-primitives-spa.md)
- [ST-13-02: Replace inline action feedback with toasts](../stories/story-13-02-replace-inline-action-feedback-with-toasts.md)
- [ST-13-03: Standardize inline system messages](../stories/story-13-03-standardize-inline-system-messages.md)
- [ST-13-04: Toastify profile actions](../stories/story-13-04-toastify-profile-actions.md)

## Risks

- Hiding important feedback: some errors must remain inline (blocking states) to avoid “toast-only” failures.
- Mobile overlap: toast placement must not cover critical controls (especially on small viewports).
- Accessibility regressions if ARIA live regions are not implemented consistently.

## Dependencies

- ADR-0037 (toast + system message patterns)
- ADR-0032 (Tailwind 4 with @theme HuleEdu tokens)
- EPIC-11 is complete; implementation is SPA-only (no SSR/HTMX duplication).
