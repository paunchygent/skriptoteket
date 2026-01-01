---
type: story
id: ST-14-02
title: "Draft slug edit (admin-only) + publish guards (slug + taxonomy)"
status: done
owners: "agents"
created: 2025-12-25
epic: "EPIC-14"
acceptance_criteria:
  - "Given an admin viewing an unpublished tool in the editor, when they update the slug to a valid unique value and save, then the new slug persists and is shown in the UI."
  - "Given an admin edits a title containing Swedish characters (å/ä/ö), when they use the slug suggestion helper, then the suggested slug is ASCII-only and passes backend slug validation."
  - "Given a published tool, when an admin attempts to change its slug, then the change is rejected and the slug remains unchanged."
  - "Given an admin tries to publish a tool whose slug starts with draft-, when they publish, then publishing is rejected with a clear validation error."
  - "Given an admin tries to publish a tool without taxonomy (no professions or no categories), when they publish, then publishing is rejected with a clear validation error."
  - "Given an admin accepts a suggestion, when the draft tool is created, then the draft tool slug uses the placeholder format draft-<tool_id>."
---

## Context

Slug is the public URL key for tools, but drafts churn. v0.1 policy is:

- drafts: slug mutable (admin-only)
- publish: slug must be final (not placeholder) and valid
- post-publish: slug immutable

Additionally, tools must have taxonomy (at least one profession and one category) before publish to ensure they are
findable in the browse tree.

## Notes

- This story depends on ADR-0037.
- No slug aliases/redirects in v0.1.
- Slug validation should use a single canonical regex + length check (ASCII-only); the UI may transliterate from title
  for a good default suggestion.
- Slug uniqueness is enforced by the DB; map duplicate slug writes to a clean `DomainError` validation error.
