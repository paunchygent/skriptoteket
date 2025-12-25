---
type: adr
id: ADR-0037
title: "SPA feedback: toast + system message patterns"
status: proposed
owners: "agents"
deciders: ["user-lead"]
created: 2025-12-25
links:
  - ADR-0032
  - ADR-0017
  - EPIC-13
  - REF-toast-system-messages
---

## Context

Skriptoteket is now a full Vue/Vite SPA (ADR-0027). User feedback is currently implemented as **inline** `successMessage`
and `errorMessage` blocks scattered across views and composables. This causes:

- **Layout shift**: success/error blocks are part of the normal document flow, creating jumpy transitions.
- **Inconsistent UX**: styling and placement varies by view/component.
- **No shared API**: each view re-implements feedback state and dismissal behavior.

We already reduced drift for buttons by introducing shared button primitives (`btn-primary`/`btn-cta`/`btn-ghost`).
We need the same consolidation for feedback messages.

## Decision

### 1) Toasts for transient action feedback (overlay)

Implement a **single** toast system for transient feedback (save/publish/submit actions) in the SPA:

- **One global host** mounted once in the app shell (Teleport to `body`), so toasts never affect page layout.
- **One API** exposed to UI code: `useToast().success(...)`, `useToast().error(...)`, etc.
- **One styling source of truth** in `frontend/apps/skriptoteket/src/assets/main.css`, using HuleEdu tokens (ADR-0032).

Behavior:

- Toasts are **non-blocking overlays** (fixed position) with slide/fade animation.
- Toasts **auto-dismiss** (default duration), with support for overriding duration per toast.
- Toasts can **stack** (bounded) so rapid sequences remain readable.
- Toasts include a manual dismiss (`×`) control.

Visual semantics (HuleEdu alignment):

- **Info**: navy background (opacity 90%) with info icon.
- **Success**: pine green (use `--huleedu-success`) background (opacity 90%) with check icon.
- **Warning**: amber (use `--huleedu-warning`) background (opacity 90%) with warning icon.
- **Failure**: burgundy background (opacity 90%) with failure icon.

### 2) Inline errors for validation + blocking states

Inline errors remain the right choice for:

- blocking load failures (the view cannot proceed)
- field/form validation errors tied to specific inputs
- system “blocking” states (e.g. lockouts / throttling / required fields)

Inline error messages:

- are **sticky until dismissed** (no auto-dismiss)
- include a close (`×`) control
- appear close to what caused the error (e.g. login errors inside `LoginModal.vue`)

### 3) Accessibility

- Toasts MUST be announced via an appropriate ARIA live region so feedback is available without relying on color alone.
- Errors SHOULD use higher urgency than non-errors.

## Consequences

**Benefits**

- Removes layout shift for action feedback.
- Establishes a single feedback vocabulary and implementation path (similar to button primitives).
- Makes it easy to migrate existing views incrementally without redesigning every screen.

**Tradeoffs**

- Introduces global UI state for toasts.
- Requires discipline to avoid reintroducing ad-hoc inline success/error blocks.

**Follow-ups**

- Implement EPIC-13 (toast primitives + migrations).
- Maintain the mapping doc: `REF-toast-system-messages`.
