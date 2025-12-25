---
type: adr
id: ADR-0037
title: "Tool slug lifecycle (draft-mutable, publish-final, post-publish immutable)"
status: accepted
owners: "agents"
deciders: ["user-lead"]
created: 2025-12-25
---

## Context

In the current system, `Tool.slug` is a unique string stored on the `tools` table and is used as the **public URL key**
for running tools:

- SPA route: `/tools/:slug/run`
- API endpoints: `GET /api/v1/tools/{slug}` and `POST /api/v1/tools/{slug}/run`

At the same time, the editor/admin tooling uses `tool.id` (UUID) routes, and draft tools churn frequently during
development. The system needs a slug policy that:

- supports fast iteration on drafts
- prevents publishing placeholder slugs like `draft-...`
- keeps v0.1 scope small (no alias/redirect machinery)

## Decision

### 1) Slug semantics

- `Tool.slug` remains the **public URL key** for user-facing tool routes and APIs.
- `Tool.id` is the internal canonical identifier and is used for admin/editor routing and persistence.
- No “public slug” vs “internal slug” split is introduced in v0.1.

### 2) Draft placeholder slug

All draft tools must use a placeholder slug at creation time:

- Format: `draft-<tool_id>`
- Rationale:
  - always unique
  - clearly non-final
  - enables a simple publish guard (`slug.startswith("draft-")`)

This applies to both:

- admin quick-create (bypassing suggestions)
- accepting a suggestion (ADR-0010) which creates a draft tool entry

### 3) Pre-publish slug mutability (admin-only)

- For unpublished tools, admins can update the slug.
- Slug updates must validate format and uniqueness.

Recommended constraints (v0.1):

- canonical form: trimmed and lowercased
- length: `1..128` characters
- allowed characters: lowercase `a-z`, digits `0-9`, and hyphen `-`
- structure: segments separated by single hyphens (no leading/trailing hyphen; no consecutive hyphens)
- reserved prefix: `draft-` is allowed for drafts but is not publishable
- regex: `^[a-z0-9]+(?:-[a-z0-9]+)*$`

Frontend UX:

- The backend validation is ASCII-only (the regex above).
- The frontend should provide a slug suggestion helper that transliterates Swedish characters from the title
  (e.g. `å/ä→a`, `ö→o`) to produce a valid default candidate.

### 4) Publish-time slug requirements

Publishing a tool must be rejected if:

- slug is a placeholder (starts with `draft-`)
- slug fails validation constraints
- slug is not unique

### 5) Post-publish immutability (v0.1)

- Once a tool is published, its slug is immutable in v0.1.
- v0.1 explicitly does not implement slug aliases or redirects.

## Consequences

- Admin authoring UX can iterate quickly on drafts without polluting the public URL space.
- Published URLs remain stable and predictable in v0.1.
- Follow-up roadmap (out of scope for v0.1):
  - allow post-publish slug renames
  - add `tool_slug_aliases` + lookup-by-alias + redirect/canonicalization behavior
