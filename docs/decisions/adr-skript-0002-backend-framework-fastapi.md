---
type: adr
id: ADR-SKRIPT-0002
title: 'Backend framework: FastAPI'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: accepted
deciders:
- user-lead
retired_ids:
- ADR-0002
---

## Context

### Context

We need a Python web framework that supports a server-driven UI, file uploads, and a straightforward path to add tools and validation.

### Decision

Use FastAPI as the backend framework.

### Consequences

- Typed request/response models and a clear routing structure.
- Works well with file upload handling and background evolution if needed later.

## Decision

The retained source material above records the accepted decision and its consequences.

## Non-Decisions

This record does not authorize implementation beyond the retained decision.

## Consequences

The retained source material above records the accepted decision and its consequences.
