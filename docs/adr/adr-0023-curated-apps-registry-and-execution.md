---
type: adr
id: ADR-0023
title: "Curated apps registry and execution (owner-authored apps)"
status: accepted
owners: "agents"
deciders: ["user-lead"]
created: 2025-12-19
updated: 2025-12-21
links: ["PRD-script-hub-v0.2", "ADR-0022", "ADR-0024", "EPIC-10"]
---

## Context

Skriptoteket supports user-authored tools that run in a locked-down container runner. This security model is
appropriate when contributors can edit and publish scripts via the tool editor workflow.

However, there is a separate need for **owner-authored “apps”** that:

- are curated and shipped from the repo (or a trusted package)
- can be richer and more integrated (e.g. deeper NLP workflows, multi-step flows)
- must still be safe to render for end users (teachers/admins)
- should NOT be editable via the tool editor UI
- should NOT be versioned through the `tool_versions` governance workflow

We need a way to run curated apps without weakening the constraints and UX model for user-authored tools.

## Decision

Introduce a **Curated Apps** concept as a first-class “subject kind”, separate from DB tool versions.

### 1) Curated apps are discovered via a registry

The app ships a curated app registry containing:

- `app_id` (stable key), `app_version` (content hash / git SHA), metadata (title/summary/tags)
- required minimum role
- UI profile (policy) for normalization and capability enablement
- initial actions/state (optional)

Curated apps are listed in Katalog alongside tools, but they are not editable.

Registry schema (sketch):

```json
{
  "app_id": "nlp.language-analysis",
  "app_version": "git:abc123",
  "title": "Language analysis",
  "summary": "Analyze a text and return readability metrics and findings.",
  "min_role": "teacher",
  "ui_policy_profile": "curated",
  "tags": ["nlp", "language", "analysis"]
}
```

Catalog integration:

- Curated apps appear in Katalog alongside tools, but are read-only.
- Each curated app receives a stable `tool_id` (e.g. derived deterministically from `app_id`) so that:
  - `tool_sessions` can persist per-user state (ADR-0024)
  - `tool_runs` can reference the same catalog entry regardless of DB resets

### 2) Curated apps execute via a dedicated executor

Curated apps execute via a `CuratedAppExecutor` (trusted code path) and return the **same Tool UI contract v2**
(ADR-0022) used by runner-based tools.

Curated apps may call internal services under platform control (observability, authz, quotas), but they still return
typed outputs/actions/state rendered by the platform UI.

### 3) Runs remain auditable

Curated app runs are persisted similarly to tool runs, but with `source_kind="curated_app"` and
`curated_app_id/curated_app_version` fields (rather than `tool_versions` linkage).

## Protocols (minimal, protocol-first seams)

Curated apps introduce two minimal protocols:

- `CuratedAppRegistryProtocol`
  - lists curated apps and resolves `app_id` → metadata + current `app_version`
  - provides the catalog-facing fields (title, role gating, tags, ui_policy_profile)
- `CuratedAppExecutorProtocol`
  - executes a curated app action and returns Tool UI contract v2 (ADR-0022)

Curated apps compose with:

- `BackendActionProviderProtocol` (ADR-0024): inject platform capability actions (policy-gated)
- `UiPayloadNormalizerProtocol` (ADR-0024): deterministic merge + allowlist/budget enforcement

## Action composition (curated app declared actions + backend injected actions)

Curated apps may declare actions in their returned contract payload (or via metadata), but the backend may also inject
capability actions (e.g. `cap.nlp.analyze_language`) depending on policy and authorization.

The merge is deterministic:

- Action IDs must be unique after merge; conflicts are treated as contract violations.
- Ordering is deterministic (e.g. source buckets then sort by `action_id`).
- Policy gates both:
  - which actions are allowed to be stored/rendered
  - which backend capabilities may be injected

This keeps curated apps powerful while preventing “scripts fighting the UI” and preventing untrusted tools from gaining
capabilities via action injection.

## Consequences

### Benefits

- Enables richer owner-authored apps without expanding the attack surface of user-authored tools.
- Keeps end-user rendering safe and consistent via typed outputs/actions.
- Separates governance and authoring workflows: curated apps are controlled by repo/package changes.

### Tradeoffs / Risks

- Introduces a second execution path (runner tools vs curated apps) which must share the same UI contract and policies.
- Requires careful authorization controls: curated apps may have powerful capabilities and must be role-guarded.
- Needs explicit operational ownership (where curated apps live, how they’re updated, how they’re tested).
