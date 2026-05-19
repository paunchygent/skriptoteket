---
type: pr
id: PR-0337
title: "ST-21-04 Correction-session browser and artifact proof"
status: ready
owners: "agents"
created: 2026-05-19
updated: 2026-05-20
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
  - "PR-0338"
  - "PR-0339"
  - "PR-0340"
  - "PR-0341"
acceptance_criteria:
  - "Given multiple supported corrections are committed with the bootstrap account, when the browser navigates between affected items and reloads the route, then the visible state is reconstructed from Skriptoteket readback and Sir Convert replay."
  - "Given committed corrections include points, choice keys, gap/open-cloze keys, item text, and candidate suppression where available, when replay runs, then the retained proof shows the complete persisted authoring/candidate-review set was submitted through the unified Sir Convert apply route without `review_decision`."
  - "Given replay returns corrected artifact references, when the proof opens `Filer`, then corrected download/save actions are enabled only for replay-scoped artifact references and no original-job artifact fallback is used."
  - "Given enabled corrected PDF/QTI downloads are proven, then artifact evidence shows corrected supported semantics and no internal diagnostics, raw overlay JSON, prompts, credentials, scores, student-result data, or identity markers leak."
  - "Given missing facit or poäng remains, when the proof inspects files and report state, then accepted-current-state export is absent and downloads stay blocked until real authoring corrections are saved."
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
  replay, route usage, artifact readiness, and enabled corrected file actions
  through replay artifact references.
- Prove local drafts do not unlock files and matching stays blocked.
- Update handoff with exact retained evidence paths.

## Non-Goals

- No new production behavior beyond proof hardening and minor testability
  support.
- No arbitrary shell Playwright snippets.
- No accepted-current-state export proof; `PR-0341` removes that as authoring
  state.
- No matching answer-key enablement.

## Prerequisite State

`PR-0341` is done. The proof must therefore exercise only the clean
authoring-to-replay-to-export path:

- no `review_decision` or accepted-current-state authoring intent;
- no `Skapa filer` shortcut for missing facit/poäng;
- corrected file actions enabled only from replay artifact references returned
  after real authoring corrections.

## Test Plan

- Canonical Playwright proof with retained route/readback/replay evidence and
  disabled corrected file-action evidence.
- Enabled corrected artifact download/save proof must use replay artifact
  references from the corrected replay result.
- Focused script-surface tests for the proof entrypoint.
- `fe-type-check`, `fe-lint`, `fe-build`, `docs-validate`,
  `handoff-validate`, and `git diff --check`.
