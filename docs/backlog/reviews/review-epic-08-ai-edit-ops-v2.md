---
type: review
id: REV-EPIC-08
title: "Review: Anchor/Patch-based AI Edit Ops v2"
status: changes_requested
owners: "agents"
created: 2026-01-10
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
| Adopt patch ops (unified diff) as the primary v2 targeting mode | Deterministic apply without cursor reliance | [ ] |
| Support anchor targets for insert/replace/delete | Enables “insert after/before this text” without offsets | [ ] |
| Define v2 triggering + request semantics (explicit vs implicit selection/cursor) | Prevents v2 never engaging; avoids cursor-less insert failures | [ ] |
| Use an AI-specific diff preview UI (reuse diff engine only) | Avoids noisy version-review UI and outdated design patterns | [ ] |
| Controlled backend fuzz ladder (0→whitespace-tolerant→1→2) + safe-fail + regenerate | Fewer regen loops while staying bounded and reviewable | [ ] |

## Review Checklist

- [ ] ADR defines clear v2 contract boundaries
- [ ] Story acceptance criteria are testable and complete
- [ ] Scope stays within EPIC-08 goals
- [ ] Risks are identified with mitigations

---

## Review Feedback

**Reviewer:** @lead-developer
**Date:** 2026-01-10
**Verdict:** changes_requested

### Required Changes

1) **Clarify v2 trigger + request semantics (must be unambiguous and testable)**
   - Define “explicit selection/cursor” precisely (today the frontend effectively always sends a cursor/selection).
   - Require the frontend to **omit both `selection` and `cursor`** when the user did not explicitly target a location,
     so v2 reliably triggers.
   - When a selection exists, require the request to include **both** `selection` and `cursor` (cursor position must be
     explicitly defined) to avoid “markör men ingen markör finns” failures.

2) **Define v2 JSON shapes**
   - Patch op: required fields, unified diff header requirements (`a/<virtualFileId>` and `b/<virtualFileId>`), and
     strict apply behavior (no fuzzy matching).
   - Anchor target: required fields, match rules (exact + single match), and explicit error reasons for mismatch vs
     ambiguity.

3) **AI diff preview UX must be purpose-built**
   - Reuse the diff implementation capabilities (merge view / unified patch helpers), but do **not** reuse the existing
     “review/version diff” UI chrome (copy/download/patch controls) for AI proposals.
   - Avoid clunky nested shadow stacks in the AI proposal panel; keep the surface minimal and consistent with current
     SPA patterns.

### Suggestions (Optional)

- Distinguish “chat disabled” vs “edit-ops disabled” in UI copy so “inte tillgänglig just nu” is actionable.
- Prefer a short, inline preview error with a single “Regenerera” CTA rather than large stacked error panels.

### Decision Approvals

- [ ] Patch ops as primary v2 mode
- [ ] Anchor targets for insert/replace/delete
- [ ] V2 trigger + request semantics
- [ ] AI diff preview uses AI-specific UI
- [ ] Controlled fuzz ladder + safe-fail

---

## Changes Made

[Author fills this in after addressing feedback]

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | ADR-0051 | |
| 2 | ST-08-24 | |
