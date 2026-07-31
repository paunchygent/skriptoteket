---
type: adr
id: ADR-SKRIPT-0079
title: Public curated-app access profiles and guest-state boundaries
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: accepted
deciders:
- user-lead
retired_ids:
- ADR-0079
---

## Context

### Source: Context

Skriptoteket's curated apps already behave like first-class application modules,
but their entry and API boundaries are still effectively tied to authenticated
browser sessions:

- the SPA app host uses `/apps/:appId` with `requiresAuth`
- `GET /api/v1/apps/{app_id}` requires `require_user_api`
- current app-specific routes such as
  `/api/v1/apps/classroom.group-seating-studio/...`,
  `/api/v1/apps/chemistry.reagent_prep_chef/...`,
  `/api/v1/apps/documents.conversion_hub/...`, and
  `/api/v1/apps/games.flunk_out_frenzy/...` also require `require_user_api`

This means the current curated-app model does not distinguish between two
separate concerns:

- who is allowed to use the app once authenticated (`min_role`)
- whether the app may expose a narrower public/guest lane before login

Klassrumskartan now needs a non-auth demo path with browser-owned guest
persistence, direct-download export, server-side import preview, and a clean
upgrade into authenticated history later. That requirement should not be solved
as a one-off auth bypass inside the existing `/apps/:appId` or
`/api/v1/apps/{app_id}` seams because other curated apps have materially
different public-access shapes:

- some may remain fully authenticated-only
- some may allow public stateless compute
- some may allow public browser-owned runtime state
- some may allow browser-owned guest work that can later be imported into an
  account

We therefore need one reusable platform decision for public curated-app access
that preserves the current owner-scoped authenticated model, fails closed by
default, and allows Klassrumskartan to be the first consumer without baking its
storage/history/export assumptions into every curated app.

## Decision

### Source: Decision

### Post-Acceptance Amendment: ADR-SKRIPT-0085

`ADR-SKRIPT-0085` amends this ADR for one narrow case:
`documents.conversion_hub` may expose a public `exam_converter` capability with
profile `public_browser_runtime`.

The original matrix entry below remains true for general Conversion Hub
workloads. General conversion, route discovery, arbitrary file conversion,
batch conversion, owner-scoped job recovery, Vault/MyFiles handoff, and account
history remain authenticated-only. Only the bounded Exam Converter public lane
is opened, and it must be represented as a scoped public capability rather than
an unqualified app-wide public profile:

```yaml
public_capabilities:
  - scope: exam_converter
    profile: public_browser_runtime
```

### 1. Public curated-app access is a separate app capability, not an implication of `min_role`

Curated apps must declare an explicit public-access profile. `min_role`
continues to govern authenticated authorization only.

Default posture:

- all curated apps are `authenticated_only` unless explicitly opened

Approved profile family:

- `authenticated_only`
  - no guest/public entry
  - existing `/apps/:appId` and `/api/v1/apps/{app_id}` behavior remains the
    only supported path
- `public_stateless`
  - public entry is allowed
  - guest work is request-scoped or lightweight browser-only state
  - no durable guest-to-account import requirement
- `public_browser_runtime`
  - public entry is allowed
  - browser-owned local runtime/progress state is authoritative
  - no server-owned guest workspace rows are created
  - authenticated continuity is optional and app-specific
- `public_browser_workspace_with_upgrade`
  - public entry is allowed
  - browser-owned guest workspace state is authoritative
  - authenticated upgrade/import is an explicit first-class flow

This ADR approves the profile concept and boundary rules.

Canonical source of truth requirement:

- the curated-app definition/registry must carry one canonical public-access
  profile field
- that field defaults to `authenticated_only`
- SPA public routing, authenticated routing, public bootstrap/detail behavior,
  and public/authenticated API gating must all read from that one registry-owned
  field only

Exact field names may be finalized during implementation, but the source of
truth may not be split across router-only, frontend-only, or app-local flags.

### 2. The existing authenticated host and authenticated app APIs remain unchanged

Skriptoteket must not weaken the current authenticated seams through optional
auth branching.

Required boundary:

- `/apps/:appId` remains the authenticated curated-app host
- `GET /api/v1/apps/{app_id}` remains authenticated
- existing owner-scoped app-specific routes under `/api/v1/apps/{app_id}/...`
  remain authenticated unless a parallel public route is explicitly defined

If a curated app supports public access, it must use:

- a dedicated public SPA entry route outside `/apps/:appId`
- a dedicated public API namespace outside the existing authenticated
  `/api/v1/apps/{app_id}/...` seam

This keeps privilege review straightforward and prevents public-mode exceptions
from accreting inside owner-scoped handlers.

### 2a. Public helper namespaces must be cookie-agnostic and non-ambient

Public helper endpoints must behave as guest/public boundaries even when a
browser already has an authenticated session cookie.

Required rules:

- public helper routes must not depend on `require_user_api`
- public helper routes must not depend on `require_session_api`
- public helper routes must not depend on `require_csrf_token`
- public helper routes must ignore ambient account authority and account-scoped
  identifiers
- public helper routes must return the same guest semantics whether or not a
  session cookie is present

This prevents the public namespace from drifting back into optional-auth
behavior under a new URL.

### 3. Browser-owned guest state is authoritative for public browser profiles

For `public_browser_runtime` and
`public_browser_workspace_with_upgrade` profiles:

- the browser is the source of truth for guest state
- guest rosters, templates, drafts, runtime state, checkpoints, and similar
  guest artifacts must not be persisted into authenticated owner-scoped tables
  before login
- the server may only perform stateless helper work or direct rendering from
  guest-supplied payloads

Permitted server roles:

- import preview / parsing
- compute helpers such as smart grouping/seating
- direct-download rendering/export
- authenticated upgrade/import once the user has a real session

### 4. Guest export must stay direct-download and Vault/MyFiles-free

Public curated-app flows must not create guest-visible Vault/MyFiles artifacts
or recoverable guest export jobs.

Rules:

- guest export may stream bytes directly
- guest export may use transient buffers only
- guest export may not create durable guest artifacts in user vault/history
- resumable export-job recovery remains an authenticated-only capability unless
  a later ADR explicitly says otherwise

### 5. Guest-to-account migration is prompt-based and only applies to upgrade-capable profiles

For `public_browser_workspace_with_upgrade`:

- migration is offered only after the user has an authenticated session
- registration must not trigger immediate migration if registration does not
  establish a session cookie
- the user must get an explicit choice to import, discard, or postpone local
  guest work
- migration must be idempotent and non-destructive by default

Minimum contract requirements for upgrade-capable profiles:

- guest snapshots must carry a schema version
- guest snapshots must carry a stable snapshot identity, such as
  `snapshot_id` and/or a stable content hash
- migratable entities must carry per-entity fingerprints used for dedupe and
  import receipts
- import results must distinguish `created`, `reused`, `skipped`, and
  `conflicted`

Default conflict policy for workspace-style apps such as Klassrumskartan:

- rosters/templates dedupe by content fingerprint
- same-name/different-content assets import as separate assets
- active draft collisions import as historical drafts by default
- replacing the current active draft is an explicit opt-in path only
- checkpoints import additively with fingerprint dedupe
- upgrade-capable browser guest work is a one-time onboarding bridge, not a
  repeatable sync loop:
  - the first authenticated guest-upgrade commit consumes the browser snapshot
    for that app in that browser
  - later visits in the same browser must not reopen repeat-import prompts for
    that app
  - public guest re-entry after that bridge is a product decision rather than
    an automatic right to keep creating new upgrade-capable guest snapshots

Undo/redo stacks and other transient editing-state noise are not assumed to be
durable history unless an app-specific contract explicitly says so.

### 6. Each public curated app must publish a capability matrix and abuse controls

Opening a curated app publicly is an app-by-app product and security decision,
not a blanket platform flip.

Every public app must define:

- guest-allowed capabilities
- guest-altered capabilities
- guest-blocked capabilities
- storage profile
- upgrade behavior, if any
- rate limits, payload caps, time budgets, and validation rules for public
  endpoints
- privacy/telemetry posture

If the app has rules, checkpoints, drafts, or upgrade semantics, the capability
matrix must cover those surfaces explicitly rather than folding them into a
generic “history” or “workspace” bucket.

### 7. Initial classification for the current curated-app set

This ADR records the current canonical matrix for the current curated-app set.
Each app gets a `current_access_profile` now, and may optionally carry a
`future_target_profile` later.

- `classroom.group-seating-studio`
  - current_access_profile: `public_browser_workspace_with_upgrade`
  - first implementation consumer
- `games.flunk_out_frenzy`
  - current_access_profile: `authenticated_only`
  - future_target_profile: `public_browser_runtime`
  - browser-owned runtime and optional later authenticated leaderboard identity
- `chemistry.reagent_prep_chef`
  - current_access_profile: `authenticated_only`
  - future_target_profile: `public_stateless`
  - public compute/export may be reasonable, but authenticated saved defaults
    remain a separate decision
- `documents.conversion_hub`
  - current_access_profile: `authenticated_only`
  - remains authenticated-only because anonymous upload/conversion abuse
    and cost controls are a first-order concern
- `demo.counter`
  - current_access_profile: `authenticated_only`
  - operational note: dev/demo-only surface, not part of the production
    public-access rollout

Only `classroom.group-seating-studio` is opened by this package. The future
targets above are planning guidance, not automatic release commitments.

## Non-Decisions

The source does not authorize additional alternatives or scope beyond the decision above.

## Consequences

### Source: Consequences

### Benefits

- Klassrumskartan guest access can be implemented without weakening the current
  authenticated curated-app architecture.
- Future curated apps get one reusable entry/storage/upgrade vocabulary instead
  of ad hoc guest exceptions.
- The current app matrix becomes deterministic and fail-closed instead of mixing
  current policy with future intent.
- Public access becomes explicit and reviewable per app.
- MyFiles/Vault and owner-scoped persistence remain clearly authenticated-only.

### Tradeoffs

- The curated-app registry and SPA host model will need new metadata and route
  handling beyond `min_role` and `ui_mode`.
- Some apps will need two parallel surfaces: authenticated and public.
- Upgrade-capable guest flows introduce a new authenticated import/orchestration
  boundary that must be carefully designed.

### Non-goals

- This ADR does not open all curated apps by default.
- This ADR does not approve server-authoritative guest workspace rows.
- This ADR does not redefine authenticated `/apps/:appId` into a mixed guest
  route.
- This ADR does not grant anonymous access to Conversion Hub or Vault/MyFiles
  surfaces.
