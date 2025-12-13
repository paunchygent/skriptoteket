---
type: adr
id: ADR-0003
title: "Script taxonomy: professions + task-flow categories"
status: accepted
owners: "agents"
deciders: ["user-lead"]
created: 2025-12-13
---

## Context

The MVP must optimize for teachers finding the right script quickly, while supporting additional roles later.

## Decision

Adopt a curated taxonomy where scripts are tagged with:

- one or more **professions** (allowlist, expandable)
- one or more **task-flow categories** (allowlist; ordered per profession for navigation)

Scripts may be cross-listed across professions and categories.

## Consequences

- Taxonomy changes become a governance topic (admins/reviewers).
- UI can present “Profession → Category” navigation with predictable ordering.
