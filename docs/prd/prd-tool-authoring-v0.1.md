---
type: prd
id: PRD-tool-authoring-v0.1
title: "Tool authoring PRD v0.1 (admin draft creation + slug lifecycle)"
status: draft
owners: "agents"
created: 2025-12-25
product: "script-hub"
version: "0.1"
---

## Summary

Reduce friction for tool creation and iteration by enabling **admins** to create **draft tools** directly (without
going through the contributor suggestion flow), while enforcing a clean and stable **slug** model for published tools.

This PRD also defines the v0.1 slug lifecycle policy:

- Pre-publish (draft/unpublished): slug is mutable (admin-only).
- On publish: a final, valid slug is required (no placeholders).
- Post-publish: slug is immutable (no aliases/redirects in v0.1).

## Goals

- Admins can create a new draft tool in under 1 minute from `/admin/tools` (title-only is sufficient).
- Published tools have human-friendly, stable URLs.
- Contributor suggestion flow remains intact, but admins can bypass it for internal iteration.

## Non-goals

- Post-publish slug renames, slug aliases, or redirects (explicit v0.1 non-goal; may be added later).
- “Public slug” vs “internal slug” differentiation (use `tool.id` as internal identifier; `tool.slug` remains public).
- Tool deletion UX (scrapped tools remain unpublished).
- Changing the browse taxonomy model (profession/category tagging remains as-is).

## User roles

- **Admin**: can quick-create draft tools; can edit slug pre-publish; can publish/depublish.
- **Contributor**: can still propose tools via suggestions; does not get admin bypass paths.
- **User**: unaffected; only sees published tools.

## Requirements

### Draft creation (admin bypass)

- Admins can create a new draft tool from `/admin/tools` with:
  - Required: `title`
  - Optional: `summary`
  - Taxonomy: may be empty at creation time
- The created tool must:
  - Be unpublished (`is_published=false`)
  - Have a placeholder slug `draft-<tool_id>`
  - Set `owner_user_id` to the creating admin
  - Add the creating admin as a maintainer
  - Start with 0 versions (no script code yet)

### Slug lifecycle policy

- Slug is the public URL key used by:
  - `/tools/:slug/run` (SPA route)
  - `GET /api/v1/tools/{slug}` and `POST /api/v1/tools/{slug}/run` (API)
- Pre-publish:
  - Admin can update the slug for unpublished tools.
  - Backend validation is ASCII-only with canonicalization (trim + lowercase):
    - length: `1..128`
    - regex: `^[a-z0-9]+(?:-[a-z0-9]+)*$`
  - Frontend provides a slug suggestion helper that transliterates Swedish characters from the title
    (e.g. `å/ä→a`, `ö→o`) into an ASCII slug candidate.
- On publish:
  - Publishing must be rejected if slug is a placeholder (starts with `draft-`).
  - Publishing must be rejected if slug is invalid or already taken.
  - Publishing must be rejected if taxonomy is missing (at least one profession and one category must be set),
    since browse views require both for findability.
- Post-publish:
  - Slug cannot be changed for published tools.

### Contributor-requested tools (suggestions → accepted → draft tool)

- Accepting a suggestion continues to create a draft tool entry (ADR-0010).
- Draft tool created from acceptance uses the same placeholder slug convention: `draft-<tool_id>`.
- Admin must set a final slug before publishing.

### UI / UX constraints

- `/admin/tools` should remain visually unified: do not scatter semantically-related actions into multiple persistent
  cards. Prefer a modal/drawer or inline expansion within the existing admin tools page layout.

## Metrics

- Median time for an admin to create a draft tool: < 60 seconds.
- Publish failures due to missing slug finalization or taxonomy: visible and actionable (clear validation errors).

## Links

- ADR: `docs/adr/adr-0037-tool-slug-lifecycle.md`
- Epic: `docs/backlog/epics/epic-14-admin-tool-authoring.md`
