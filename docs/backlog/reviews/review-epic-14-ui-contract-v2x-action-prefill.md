---
type: review
id: REV-EPIC-14
title: "Review: UI contract v2.x action prefill defaults"
status: approved
owners: "agents"
created: 2026-01-15
reviewer: "lead-developer"
epic: EPIC-14
adrs:
  - ADR-0060
stories:
  - ST-14-23
---

## TL;DR

Add a backwards-compatible v2.x extension so tools can provide explicit defaults/prefill for `next_actions` fields via an
action-level `prefill` map, validated deterministically during normalization with actionable system notices for invalid
values.

ST-14-24 (file references) will be handled in a separate ADR.

## Problem Statement

Today, "prefilled action fields" can only be approximated in the client by remembering the last submitted values. Tools
cannot intentionally guide users by emitting default values derived from current `state` or prior outputs, and stored
`ui_payload` replay cannot preserve such guidance deterministically.

## Proposed Solution

Implement ADR-0060:

- Add optional `next_actions[].prefill` (`{[field_name]: JsonValue}`) on `UiFormAction`.
- Validate/strip invalid prefill deterministically during normalization and surface an actionable system notice.
- Update the SPA action form rendering to initialize matching fields from `prefill` while keeping current behavior when
  absent.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/adr/adr-0060-ui-contract-v2x-action-prefill.md` | Contract shape, validation rules, UI semantics | 10 min |
| `docs/backlog/stories/story-14-23-ui-contract-action-defaults-prefill.md` | Acceptance criteria and scope | 5 min |
| `docs/backlog/sprints/sprint-2026-06-09-tool-ui-contract-v2-action-defaults-and-file-refs.md` | Sprint linkage and risks | 5 min |

**Total estimated time:** ~20 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Defaults/prefill lives on `UiFormAction.prefill` (not field-level defaults) | Minimal contract surface; enables deterministic validation/stripping in normalizer | [x] |
| Invalid prefill is stripped + surfaced via system notice output | Deterministic, non-breaking rendering while still actionable | [x] |
| Separate ADR for ST-14-24 file references | Keeps this change shippable independently; avoids coupling to runner/security details | [x] |

## Review Checklist

- [x] ADR defines an additive, backwards-compatible contract extension
- [x] Invalid defaults behavior is deterministic and actionable
- [x] UI semantics are defined for both runtime and editor sandbox action rendering
- [x] Scope stays within ST-14-23 (file refs deferred to separate ADR)

---

## Review Feedback

**Reviewer:** @user-lead
**Date:** 2026-01-15
**Verdict:** approved

### Required Changes

None.

### Suggestions (Optional)

- Consider a follow-up story to improve UX when multiple actions share field names but want different defaults.

### Decision Approvals

- [x] Defaults location: action-level `prefill`
- [x] Invalid default handling: strip + system notice
- [x] ADR strategy: separate ST-14-23 and ST-14-24 ADRs
