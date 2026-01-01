---
type: sprint
id: SPR-2026-03-17
title: "Sprint 2026-03-17: Tool editor sandbox debug details"
status: planned
owners: "agents"
created: 2025-12-29
starts: 2026-03-17
ends: 2026-03-30
objective: "Make sandbox failures actionable for authors by exposing safe debug details (stdout/stderr) in the editor."
prd: "PRD-editor-sandbox-v0.1"
epics: ["EPIC-14"]
stories: ["ST-14-11", "ST-14-12"]
---

## Objective

Improve author iteration speed by making sandbox errors debuggable without server log access.

Reference context: `docs/reference/ref-tool-editor-dx-review-2025-12-29.md`

## Before / After

**Before**

- Sandbox failures surface a safe `error_summary`, but stdout/stderr are not available in the editor UI.
- Authors often need server-side logs (or trial-and-error) to diagnose Python errors.

**After**

- Authorized users can view **truncated** stdout/stderr for a sandbox run in an editor Debug panel.
- Users can copy a single “debug bundle” (ids + truncation flags + stdout/stderr) for support and future AI assistance.
- Non-authorized users never receive stdout/stderr.

## Scope (committed stories)

- [ST-14-11: Editor sandbox run debug details API (stdout/stderr, gated)](../stories/story-14-11-editor-sandbox-run-debug-details-api.md)
- [ST-14-12: Editor sandbox debug panel UX (copyable diagnostics)](../stories/story-14-12-editor-sandbox-debug-panel.md)

## Out of scope

- Showing full Python tracebacks to end users (keep safe error boundaries).
- Production run debug details (non-editor).

## Decisions required (ADRs)

- Confirm role gating policy for debug details (e.g. maintainer-only vs admin-only).

## Risks / edge cases

- Sensitive data leakage via stdout/stderr (even in sandbox): ensure caps, role gating, and no accidental exposure.
- Large logs: ensure truncation is visible and predictable.

## Execution plan (suggested)

## Pacing checklist (suggested)

- [ ] Extend editor run details response model to include `stdout`/`stderr` (truncated) with explicit truncation flags.
- [ ] Gate the new fields based on role/maintainer access, and keep logs metadata-only (never stdout/stderr content).
- [ ] Add a Debug panel UI in `SandboxRunner` to show/copy the details (including a single “copy bundle” action).

## Demo checklist

- Trigger a sandbox error (syntax error + runtime error) and show debug details.
- Verify that users without access do not see debug content.

## Verification checklist

- `pdm run docs-validate`
- `pdm run lint`
- `pdm run test`
- `pdm run fe-gen-api-types`
- Live functional check (backend + SPA dev); record steps in `.agent/handoff.md`.
