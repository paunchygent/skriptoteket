---
type: review
id: REV-EPIC-08
title: "Review: Anchor/Patch-based AI Edit Ops v2"
status: approved
owners: "agents"
created: 2026-01-10
updated: 2026-01-11
reviewer: "lead-developer"
epic: EPIC-08
adrs:
  - ADR-0051
stories:
  - ST-08-24
---

## TL;DR

We are updating ADR-0051 to add a v2 edit-ops protocol that supports anchor/patch-based targeting so chat-driven edits
can apply deterministically without relying on cursor position. This review validates the decision scope, contract shape,
and the new story slice for EPIC-08.

## Problem Statement

Cursor/selection-only edit ops produce surprising inserts when the user has not explicitly placed a cursor or selection.
This undermines trust in the chat assistant and does not match expected coding-assistant behavior.

## Proposed Solution

- Extend ADR-0051 with v2 edit-ops targets (patch + anchor).
- Introduce ST-08-24 to implement the protocol and apply logic while reusing existing diff preview/apply UI.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/adr/adr-0051-chat-first-ai-editing.md` | v2 contract additions + guardrails | 8 min |
| `docs/backlog/stories/story-08-24-ai-edit-ops-anchor-patch-v2.md` | acceptance criteria + scope | 5 min |
| `docs/backlog/epics/epic-08-contextual-help-and-onboarding.md` | story list + scope alignment | 3 min |

**Total estimated time:** ~16 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Adopt patch ops (unified diff) as the primary v2 targeting mode | Deterministic apply without cursor reliance | [x] |
| Support anchor targets for insert/replace/delete | Enables “insert after/before this text” without offsets | [x] |
| Define v2 triggering + request semantics (explicit vs implicit selection/cursor) | Prevents v2 never engaging; avoids cursor-less insert failures | [x] |
| Use an AI-specific diff preview UI (reuse diff engine only) | Avoids noisy version-review UI and outdated design patterns | [x] |
| Controlled backend fuzz ladder (0→whitespace-tolerant→1→2) + safe-fail + regenerate | Fewer regen loops while staying bounded and reviewable | [x] |

## Review Checklist

- [x] ADR defines clear v2 contract boundaries
- [x] Story acceptance criteria are testable and complete
- [x] Scope stays within EPIC-08 goals
- [x] Risks are identified with mitigations

---

## Review Feedback

**Reviewer:** @lead-developer
**Date:** 2026-01-11
**Verdict:** approved

### Required Changes (resolved)

1) **Clarify v2 trigger + request semantics (must be unambiguous and testable)**
   - Frontend now treats “explicit cursor” as a TTL-gated user interaction; when not explicit it omits both `selection`
     and `cursor` (so v2 reliably triggers).
   - When a selection exists, the frontend includes both `selection` and `cursor` (cursor defaults to selection end).

2) **Define v2 JSON shapes**
   - Patch op: schema validates shape; backend sanitizes headers and rejects multi-file diffs; apply uses bounded fuzz
     ladder.
   - Anchor target: strict single-match resolution with user-actionable errors for missing/ambiguous anchors.

3) **AI diff preview UX must be purpose-built**
   - AI proposals render in an AI-specific diff surface (reuse diff engine only; no version-review chrome).

### Suggestions (Optional)

- Distinguish “chat disabled” vs “edit-ops disabled” in UI copy so “inte tillgänglig just nu” is actionable.
- Prefer a short, inline preview error with a single “Regenerera” CTA rather than large stacked error panels.

### Decision Approvals

- [x] Patch ops as primary v2 mode
- [x] Anchor targets for insert/replace/delete
- [x] V2 trigger + request semantics
- [x] AI diff preview uses AI-specific UI
- [x] Controlled fuzz ladder + safe-fail

---

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | ADR-0051 | Clarified v2 trigger semantics and patch/anchor contract boundaries. |
| 2 | ST-08-24 | Acceptance criteria updated/validated against implemented v2 behavior. |
| 3 | Backend | Patch/anchor ops supported; backend preview/apply endpoints; bounded fuzz ladder; safe-fail error mapping. |
| 4 | Frontend | Explicit cursor TTL; omit cursor/selection when implicit; AI-specific diff preview UI + regenerate path. |
