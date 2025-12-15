---
type: reference
id: REF-scripting-governance-deferred-options
title: "Scripting governance: deferred options (post-v0.1)"
status: active
owners: "agents"
created: 2025-12-15
topic: "scripting"
tags: ["governance", "notifications", "epic-05", "epic-06"]
links:
  - docs/backlog/epics/epic-04-dynamic-tool-scripts.md
  - docs/backlog/stories/story-04-04-governance-audit-rollback.md
  - docs/reference/ref-dynamic-tool-scripts.md
  - docs/reference/ref-scripting-api-contracts.md
  - docs/adr/adr-0009-auth-local-sessions-admin-provisioned.md
  - docs/adr/adr-0014-versioning-and-single-active.md
---

This document records governance/UX options that were intentionally **deferred from v0.1** (EPIC-04) to keep the
critical path small: publish an `IN_REVIEW` version (copy-on-activate), request changes, and ensure
`tools.active_version_id` is correctly maintained.

These options are candidates to attach to future EPIC-05 / EPIC-06 once those epics are defined.

## Option B: Hard reject (archive only)

**Meaning**

- An `IN_REVIEW` snapshot is rejected and considered dead; no new draft is created.

**Problems (relative to current EPIC-04 docs and UI permissions)**

- There is no dedicated place to store reviewer rationale without adding new storage:
  - `review_note` is conceptually the submitter’s note (draft → in_review), not a reviewer decision log.
- If the system archives the `IN_REVIEW` version and does not create a new draft, contributors can end up with **no
  visible versions** (contributors currently do not see `ARCHIVED`), losing their editing surface.

**Recommendation**

- Do not implement for v0.1 unless we also implement:
  - a decision/audit model to store reviewer rationale, and
  - a UX/path for the author to continue work after rejection (e.g., auto-create a new draft derived from the rejected
    version, or grant limited access to archived versions for the author).

**If revisited later**

- Define the desired end state for the author (continue editing vs explicitly “closed”).
- Introduce a persisted decision record (see “Minimal in-app decision log”).
- Update contributor visibility rules if “no new draft is created” remains a requirement.

## Option B: Dedicated review queue

**Meaning**

- A cross-tool admin page listing versions in `IN_REVIEW`, similar to the suggestions review queue.

**Pros**

- Scales better once many tools exist.
- Matches the established “review queue” mental model from suggestions.

**Cons**

- Adds new query + UI surface area (usually needs filtering, pagination, and “open in editor” affordances).
- Mostly a navigation/discoverability feature; it does not change the core correctness of publish/request-changes.

**Recommendation**

- Implement as a follow-up story only if/when volume makes editor-driven discovery insufficient.

**If revisited later**

- Add a query/handler that lists `tool_versions` where `state=in_review` plus tool metadata (title/slug, author, submitted
  timestamp).
- Add an admin page linking directly to `/admin/tool-versions/{version_id}` for review and decision.

## Option B: Minimal in-app “decision log”

**Meaning**

- Persist reviewer decisions (publish / request-changes / hard-reject) with rationale and timestamps, and show them to:
  - admins (for audit), and
  - authors (to understand what happened after an `IN_REVIEW` snapshot is consumed/archived).

**Why it’s non-trivial**

- Requires new persistence (similar to suggestions decisions) and new UI surfaces.
- Requires explicit rules on who can see what (especially if authors can’t view archived versions today).

**Recommendation**

- Valid direction, but treat as its own story/ADR (likely EPIC-06) rather than coupling it into the v0.1 publish path.

**If revisited later**

- Introduce a new entity/table (e.g., `tool_version_review_decisions`) with:
  - `decision_type`, `rationale`, `decided_by_user_id`, `decided_at`, `tool_id`, `version_id`
- Decide whether the log is append-only and whether multiple decisions per version are allowed.

## Option C: Email notifications

**Meaning**

- Notify the submitter/author when their version is published or rejected/requested-changes.

**Constraint**

- Conflicts with ADR-0009’s v0.1 ops goal of minimal dependencies (no email infrastructure).

**Recommendation**

- Defer to a later epic once we have a notification infrastructure (email and/or in-app notifications).
