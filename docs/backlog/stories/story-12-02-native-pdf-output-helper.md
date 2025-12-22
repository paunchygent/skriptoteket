---
type: story
id: ST-12-02
title: "Native PDF output helper"
status: blocked
owners: "agents"
created: 2025-12-21
epic: "EPIC-12"
acceptance_criteria:
  - "Given a script produces HTML output intended for printing, when it requests native PDF rendering, then the platform renders a PDF deterministically with a supported helper and stores it as an artifact"
  - "Given PDF rendering fails (invalid HTML/CSS, missing fonts, etc), when the run finishes, then the user receives a clear error message without exposing internal stack traces"
ui_impact: "Adds a simple “Download as PDF” outcome without requiring users to print-to-PDF manually."
data_impact: "Produces PDF artifacts in the existing artifact store; no new persistent user data."
dependencies: ["ST-11-13"]
---

## Context

Some tools should be able to generate printable PDFs (e.g., handouts, certificates, reports) without relying on the
browser’s print-to-PDF workflow.

## Blocker

This story is **blocked until EPIC-11 is complete (ST-11-13 cutover)** so PDF output UX is implemented once in the SPA
(not duplicated in SSR/HTMX).
