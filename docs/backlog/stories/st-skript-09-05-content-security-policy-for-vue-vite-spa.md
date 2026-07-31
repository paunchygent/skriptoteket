---
type: story
id: ST-SKRIPT-09-05
title: Content-Security-Policy for Vue/Vite SPA
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: ready
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
epic: EPIC-SKRIPT-09
acceptance_criteria:
- Given HTTPS responses, when headers are inspected, then CSP is present and enforced.
- Given CSP report-only mode, when core SPA flows are exercised, then no new violations
  appear.
- Given the editor uses CodeMirror, when editing tools, then no CSP violations occur.
- Given external assets are required, when pages render, then they load without CSP
  errors.
- Given API and websocket usage, when CSP is enforced, then only expected origins
  are allowed.
retired_ids:
- ST-09-05
---

## Context

ST-09-02 is closed as superseded. The stack is now a Vue/Vite SPA with a CodeMirror-based editor,
so CSP must be scoped to the actual Vite build output and runtime behavior.

## Epic Contract Slice

- Production CSP header applied via nginx (ADR-0021).
- SPA asset pipeline (hashed JS/CSS from Vite) and editor runtime (CodeMirror).
- External assets (fonts, images, CDNs) only if required; prefer self-hosting.
- API + websocket connections used by the SPA (including HMR in dev if we keep CSP active).

## ADR Coverage

No separate material is recorded in the source snapshot.

## Contract Inputs

No separate material is recorded in the source snapshot.

## Live Verification Plan

No separate material is recorded in the source snapshot.

## Non-Goals

No separate material is recorded in the source snapshot.

## Notes

### Context

ST-09-02 is closed as superseded. The stack is now a Vue/Vite SPA with a CodeMirror-based editor,
so CSP must be scoped to the actual Vite build output and runtime behavior.

### Scope

- Production CSP header applied via nginx (ADR-0021).
- SPA asset pipeline (hashed JS/CSS from Vite) and editor runtime (CodeMirror).
- External assets (fonts, images, CDNs) only if required; prefer self-hosting.
- API + websocket connections used by the SPA (including HMR in dev if we keep CSP active).

### Proposed approach

1) Inventory
   - Enumerate all script/style/font/image/connect/worker sources used in prod.
   - Confirm whether CodeMirror or other UI code injects inline styles.

2) Draft CSP
   - Start with a strict baseline (default-src 'self').
   - Allow only required sources for script-src, style-src, img-src, font-src, connect-src,
     frame-ancestors, worker-src, and object-src.
   - Avoid 'unsafe-inline' for scripts; only allow for styles if required by CodeMirror.

3) Rollout
   - Enable CSP in report-only mode first.
   - Exercise critical flows (browse, run tool, editor, admin) and capture violations.
   - Iterate until report-only is clean, then enforce.

### Notes

- If we must allow inline styles, keep the exception scoped to style-src only.
- If HMR needs CSP in dev, allow ws://localhost and ws://127.0.0.1 where applicable.
- Consider a CSP report endpoint if we want centralized violation tracking.

## Decision And Assumption Ledger

The source snapshot is the governing record for the decisions and assumptions stated above.

## Plan Document Review

No separate material is recorded in the source snapshot.

## Story Closeout Review

No separate material is recorded in the source snapshot.
