---
type: adr
id: ADR-0002
title: "Backend framework: FastAPI"
status: accepted
owners: "agents"
deciders: ["user-lead"]
created: 2025-12-13
---

## Context

We need a Python web framework that supports a server-driven UI, file uploads, and a straightforward path to add tools and validation.

## Decision

Use FastAPI as the backend framework.

## Consequences

- Typed request/response models and a clear routing structure.
- Works well with file upload handling and background evolution if needed later.
