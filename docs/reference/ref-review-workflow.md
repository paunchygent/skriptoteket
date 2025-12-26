---
type: reference
id: REF-review-workflow
title: "Review workflow for EPICs, ADRs, and Stories"
status: active
owners: "agents"
created: 2025-12-26
topic: "review-workflow"
---

# Review Workflow

This document defines how to create, conduct, and close reviews for proposed EPICs, ADRs, and Stories.

## When Reviews Are Required

All proposed implementations require review before work begins:

| Artifact | Trigger | Reviewer |
|----------|---------|----------|
| ADR | Status = `proposed` | Lead developer or architect |
| EPIC | Status = `proposed` | Lead developer |
| Stories | Part of proposed EPIC | Reviewed with EPIC |

## Review Document Structure

### Location

```
docs/backlog/reviews/review-{epic-id}-{short-name}.md
```

Example: `docs/backlog/reviews/review-epic-16-catalog-discovery.md`

### Required Sections

1. **TL;DR** — One paragraph summary of what's being proposed
2. **Problem Statement** — What user/system problem this solves
3. **Proposed Solution** — High-level approach (reference ADRs for details)
4. **Artifacts to Review** — Ordered list with estimated reading time
5. **Key Decisions** — Table of decisions requiring explicit approval
6. **Review Checklist** — Checkboxes for reviewer to complete

### Review Status

```yaml
status: pending | approved | changes_requested | rejected
```

## Reviewer Responsibilities

### Before Starting

1. Block ~30 minutes of uninterrupted time
2. Read artifacts in the order specified
3. Have the codebase open for reference

### During Review

For each artifact, evaluate:

| Criterion | Question |
|-----------|----------|
| **Alignment** | Does this solve the stated problem? |
| **Architecture** | Does it follow our DDD/Clean Architecture patterns? |
| **Scope** | Is scope appropriate (not too broad, not too narrow)? |
| **Testability** | Are acceptance criteria testable and complete? |
| **Risk** | Are risks identified and mitigations reasonable? |

### Recording Feedback

Add feedback directly to the review document under a `## Review Feedback` section:

```markdown
## Review Feedback

**Reviewer:** @lead-developer
**Date:** 2025-12-27
**Verdict:** changes_requested

### Required Changes

1. ADR-0041: Clarify cascade delete behavior when tool is unpublished (not deleted)
2. ST-16-03: Add acceptance criterion for empty filter state

### Suggestions (Optional)

- Consider adding pagination to flat catalog API for future scalability

### Approved Decisions

- [x] OR filter logic
- [x] Server-side favorites
- [x] ILIKE search (sufficient for current scale)
```

## Post-Review Actions

### If Approved

1. Update review doc status to `approved`
2. Update ADR status from `proposed` → `accepted`
3. Update EPIC status from `proposed` → `active`
4. Stories remain `ready` (unchanged)
5. Review doc is **retained** as decision record

### If Changes Requested

1. Update review doc status to `changes_requested`
2. Author addresses each required change in the artifacts
3. Author adds `## Changes Made` section to review doc documenting what was changed
4. Author requests re-review
5. Reviewer verifies changes and updates verdict

### If Rejected

1. Update review doc status to `rejected`
2. Reviewer documents rejection reason in feedback
3. ADRs remain `proposed` or move to `deprecated`
4. EPIC moves to `dropped`
5. Review doc is **retained** as decision record (why we didn't do this)

## Review Document Lifecycle

```
┌──────────┐     ┌──────────────────┐     ┌──────────┐
│ pending  │────▶│ changes_requested│────▶│ approved │
└──────────┘     └──────────────────┘     └──────────┘
     │                    │
     │                    ▼
     │           ┌──────────────────┐
     └──────────▶│    rejected      │
                 └──────────────────┘
```

**Retention:** Review docs are never deleted. They serve as:

- Decision records (why we approved/rejected)
- Onboarding context (what was considered)
- Audit trail (who approved what, when)

## Template

Use `docs/templates/template-review.md` when creating new reviews.

## Example Review Cycle

1. Agent creates EPIC-16 with 2 ADRs and 7 stories (status: `proposed`)
2. Agent creates `review-epic-16-catalog-discovery.md` (status: `pending`)
3. Lead developer reviews, requests 2 changes (status: `changes_requested`)
4. Agent updates ADR-0041 and ST-16-03, documents changes
5. Lead developer re-reviews, approves (status: `approved`)
6. ADRs → `accepted`, EPIC → `active`
7. Implementation begins with ST-16-01
