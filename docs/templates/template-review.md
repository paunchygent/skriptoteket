---
type: template
id: TPL-review
title: "Review template"
status: active
owners: "agents"
created: 2025-12-26
for_type: review
---

Copy, fill in, and save under `docs/backlog/reviews/`:

```markdown
---
type: review
id: REV-EPIC-XX
title: "Review: [Epic Title]"
status: pending
owners: "agents"
created: YYYY-MM-DD
reviewer: "lead-developer"
epic: EPIC-XX
adrs:
  - ADR-XXXX
  - ADR-XXXX
stories:
  - ST-XX-01
  - ST-XX-02
---

## TL;DR

[One paragraph summary of what's being proposed and why]

## Problem Statement

[What user or system problem does this solve?]

## Proposed Solution

[High-level approach — reference ADRs for architectural details]

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/adr/adr-XXXX-*.md` | [What to look for] | X min |
| `docs/backlog/epics/epic-XX-*.md` | Scope in/out | X min |
| `docs/backlog/stories/story-XX-*.md` | Acceptance criteria | X min |

**Total estimated time:** ~XX minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| [Decision 1] | [Why this choice] | [ ] |
| [Decision 2] | [Why this choice] | [ ] |
| [Decision 3] | [Why this choice] | [ ] |

## Review Checklist

- [ ] ADRs define clear contracts
- [ ] EPIC scope is appropriate
- [ ] Stories have testable acceptance criteria
- [ ] Implementation aligns with codebase patterns
- [ ] Risks are identified with mitigations

---

## Review Feedback

**Reviewer:** @[reviewer-name]
**Date:** YYYY-MM-DD
**Verdict:** [pending | approved | changes_requested | rejected]

### Required Changes

[List specific changes needed, or "None" if approved]

### Suggestions (Optional)

[Non-blocking recommendations]

### Decision Approvals

- [ ] Decision 1
- [ ] Decision 2
- [ ] Decision 3

---

## Changes Made

[Author fills this in after addressing feedback]

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | ADR-XXXX | [What was changed] |
| 2 | ST-XX-XX | [What was changed] |
```
