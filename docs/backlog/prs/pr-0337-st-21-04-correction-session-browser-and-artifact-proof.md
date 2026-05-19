---
type: pr
id: PR-0337
title: "ST-21-04 Correction-session browser and artifact proof"
status: ready
owners: "agents"
created: 2026-05-19
updated: 2026-05-19
stories:
  - "ST-21-04"
tags:
  - playwright
  - proof
  - frontend
  - backend
  - conversion-hub
  - exam-converter
dependencies:
  - "ADR-0087"
  - "PR-0336"
acceptance_criteria:
  - "Given multiple supported corrections are committed with the bootstrap account, when the browser navigates between affected items and reloads the route, then the visible state is reconstructed from Skriptoteket readback and Sir Convert replay."
  - "Given committed corrections include points, choice keys, gap/open-cloze keys, item text, review decisions, and candidate suppression where available, when replay runs, then the retained proof shows the complete persisted set was submitted through the unified Sir Convert apply route."
  - "Given artifacts are generated after replay, when PDF/QTI evidence is inspected, then corrected supported semantics are present and no internal diagnostics, raw overlay JSON, prompts, credentials, scores, student-result data, or identity markers leak."
  - "Given local drafts exist without submit, when the proof evaluates readiness and downloads, then drafts do not unlock artifacts."
  - "Given matching correction is still unsupported, when the proof inspects UI and requests, then no matching submit path or retired Task 324 route is used."
---

# PR-0337: ST-21-04 Correction-Session Browser And Artifact Proof

## Problem

The durable correction-session workflow is not complete until it is proven in
the live product path. The proof must show that visible state survives
navigation and reload because backend readback and Sir Convert replay drive the
projection, not because local component state happened to remain in memory.

## Scope

- Add or extend canonical Playwright proof scripts in the sanctioned script
  location.
- Use the authenticated HuleEdu/Skriptoteket browser-session ceremony and the
  real Gateway/Sir Convert route chain.
- Retain evidence for committed corrections, backend readback, complete-set
  replay, route usage, artifact readiness, and downloaded artifact inspection.
- Prove local drafts do not unlock files and matching stays blocked.
- Update handoff with exact retained evidence paths.

## Non-Goals

- No new production behavior beyond proof hardening and minor testability
  support.
- No arbitrary shell Playwright snippets.
- No matching answer-key enablement.

## Test Plan

- Canonical Playwright proof with retained artifacts.
- Focused script-surface tests for the proof entrypoint.
- `fe-type-check`, `fe-lint`, `fe-build`, `docs-validate`,
  `handoff-validate`, and `git diff --check`.
