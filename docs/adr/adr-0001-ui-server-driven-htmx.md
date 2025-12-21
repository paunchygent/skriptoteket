---
type: adr
id: ADR-0001
title: "Server-driven UI with HTMX-style partial updates"
status: superseded
owners: "agents"
deciders: ["user-lead"]
created: 2025-12-13
updated: 2025-12-21
links: ["ADR-0027"]
---

## Context

The MVP must be easy to maintain, accessible, and fast to iterate on without building a large SPA.

## Decision

Use server-rendered HTML and HTMX-style partial updates for forms and results.

## Consequences

- Minimal client-side JavaScript; simpler accessibility and deployment.
- Templates and server routes become the primary UI surface.
- Clear server-side error handling becomes critical for UX.

## Status note

This ADR is superseded by ADR-0027 (full Vue/Vite SPA migration).
