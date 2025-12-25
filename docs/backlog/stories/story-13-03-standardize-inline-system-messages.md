---
type: story
id: ST-13-03
title: "Standardize inline system messages"
status: done
owners: "agents"
created: 2025-12-25
epic: "EPIC-13"
acceptance_criteria:
  - "Given a view must display a blocking load error, when rendered, then the error uses a shared system message style/component"
  - "Given a form displays a non-blocking contextual warning, when rendered, then the message uses the shared system message style/component"
  - "Inline system messages remain in the normal document flow and are not used for transient action feedback"
  - "System message variants (info/success/warning/error) use HuleEdu tokens and match REF-toast-system-messages guidance"
ui_impact: "Reduces styling drift by consolidating inline message markup and classes."
data_impact: "None."
dependencies: ["ADR-0037", "ST-13-01"]
---

## Context

Even after migrating transient action feedback to toasts, the SPA still needs inline messages for blocking and
long-lived states (ADR-0037). Today these are implemented ad-hoc, leading to drift.

This story standardizes inline system message patterns (shared component or shared CSS primitives) and migrates the
remaining blocking/error banners to the shared approach.
