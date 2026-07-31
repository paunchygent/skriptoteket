---
type: adr
id: ADR-SKRIPT-0003
title: 'Script taxonomy: professions + task-flow categories'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: accepted
deciders:
- user-lead
retired_ids:
- ADR-0003
---

## Context

### Source: Context

The MVP must optimize for teachers finding the right script quickly, while supporting additional roles later.

## Decision

### Source: Decision

Adopt a curated taxonomy where scripts are tagged with:

- one or more **professions** (allowlist, expandable)
- one or more **task-flow categories** (allowlist; ordered per profession for navigation)

Scripts may be cross-listed across professions and categories.

## Non-Decisions

The source does not authorize additional alternatives or scope beyond the decision above.

## Consequences

### Source: Consequences

- Taxonomy changes become a governance topic (admins/reviewers).
- UI can present “Profession → Category” navigation with predictable ordering.
