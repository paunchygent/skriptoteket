---
type: pr
id: PR-0273
title: "ST-26-06 public guest Klassrumskartan share links with TTL, supersede, and browser-owned revoke"
status: done
owners: "agents"
created: 2026-04-30
updated: 2026-05-01
stories:
  - "ST-26-06"
tags: ["frontend", "backend", "klassrumskartan", "public-access", "sharing"]
dependencies:
  - "PR-0274"
  - "ADR-0079"
  - "ADR-0080"
  - "ADR-0084"
  - "REV-ST-26-06"
  - "REV-PR-0273"
acceptance_criteria:
  - "Given `ADR-0084` is accepted, when implementation planning starts, then this public guest share slice stays inside the accepted exception and does not create any wider durable anonymous guest artifact path."
  - "Given a public guest opens the grouping or seating export menu, when they inspect export actions, then `Dela länk` appears beside PDF/Excel."
  - "Given a guest clicks `Dela länk`, when pending browser-owned state exists, then the public export preparation path flushes current draft and smart-rule state before share creation."
  - "Given the public helper receives a share request, when `expected_revision` does not match the browser-owned snapshot draft revision, then it rejects with the same strict conflict behavior as public export."
  - "Given the public helper creates a share, when the response returns, then the share has an expiry no later than 60 days and returns a public `/share/classroom/{token}/{slug?}` URL."
  - "Given the public helper creates a share, when the request attempts to set or persist a longer expiry, then the backend rejects it or clamps it to the 60-day ceiling with tested behavior."
  - "Given public guest sharing is implemented, when routes are registered, then creation stays on dedicated public helper routes and anonymous reads stay on the shared public token route without owner-scoped APIs, SPA shell fallback, or account authority."
  - "Given the browser still holds a previous guest share revoke secret for the same snapshot and draft kind, when a newer `Dela länk` succeeds, then the previous guest share is revoked or superseded."
  - "Given the browser does not hold a previous revoke secret, when a newer guest link is created, then the old link remains available only until its natural expiry."
  - "Given a guest later signs in, when authenticated guest-upgrade runs, then guest share links do not silently become account-owned artifacts unless a later explicit story adds that migration."
  - "Given public share creation stores anonymous artifacts, when limits are enforced, then share-specific request-byte caps, rendered-size caps, creation rate limits, active-share ceilings, purge cadence, and redacted metrics/log fields are tested."
  - "Given a browser retries or double-clicks `Dela länk`, when the same client operation is replayed, then share creation and previous-link supersede behavior are idempotent and race-safe."
  - "Given the browser still holds the current public guest share path and revoke secret, when the guest chooses remove/revoke from the public share popover, then the public helper revokes only that browser-owned link and the link disappears from the active popover list."
  - "Given public guest revoke/remove is implemented, when API routes are registered, then it stays on a narrow cookie-agnostic public helper route and does not add account-style share listing, dashboards, owner-scoped APIs, or server-side discovery of other guest links."
  - "Given the public guest removes a share link, when the public token URL is opened afterward, then the route handles it as revoked/unavailable and no longer renders the shared classroom artifact as active."
---

## Problem

Public Klassrumskartan users also need shareable digital links, but guest mode
cannot rely on account ownership, Vault, or owner-scoped APIs. The feature must
stay cookie-agnostic and browser-owned until explicit authentication.

## Goal

Add public guest share-link publishing through the public helper creation
boundary, reusing the authenticated share artifact/read model while applying a
guest-safe TTL ceiling, abuse controls, and browser-held supersede/revoke
behavior. `ADR-0084` is accepted; implementation must stay inside that accepted
exception and the retained `REV-ST-26-06` guardrails.

Reopened 2026-04-30 after the share-management UI review: the original
implementation shipped create/supersede but did not expose a current-link
remove/revoke action for public guest users. That gap is not a defensible UX
decision; it is a missing public helper lifecycle action under the same
browser-held revoke-secret model.

## Non-goals

- No account-style guest share dashboard.
- No indefinite guest links.
- No owner-scoped API fallthrough.
- No automatic migration of guest shares into an account.
- No public editing or live draft sharing.

## Implementation Plan

1. Add public helper endpoints:
   - `POST /api/v1/public/apps/classroom.group-seating-studio/grouping/share`
   - `POST /api/v1/public/apps/classroom.group-seating-studio/seating/share`
2. Reuse public export snapshot materialization and strict expected-revision
   validation; create no artifact when the revision guard fails.
3. Reuse the share artifact storage/read route from `PR-0274`, with
   `owner_user_id = null`, `source = public_guest`, and `expires_at` no later
   than `created_at + 60 days`.
4. Generate a browser-held revoke secret for public guest shares and store only
   its hash server-side.
5. Let the browser pass the previous revoke secret for the same guest
   snapshot/draft kind so the server can revoke/supersede the older guest link.
6. Store latest public guest share metadata locally in the browser per snapshot
   plus draft kind.
7. Add a narrow public guest revoke helper that accepts the current
   `public_path` plus browser-held `revoke_secret`, hashes both values
   server-side, revokes only the matching active `public_guest` artifact, and
   ignores ambient cookies or account identity.
8. Add guest export-menu UI for `Dela länk`, copy-link feedback, expiry
   messaging, and newest-link replacement behavior.
9. Wire the public share popover to the browser-owned active share artifact:
   created links appear immediately, copy uses the same row affordance as the
   authenticated popover, remove/revoke calls the public helper, and successful
   removal clears the row instead of showing an archive of dead links.
10. Add client operation ids or idempotency keys so retries, double-clicks, and
   two-tab races do not create contradictory "newest link" state.
11. Model previous-link supersede as an atomic conditional update keyed by
   previous token hash plus revoke-secret hash. Invalid previous secrets should
   not block new share creation, but must be logged through redacted reason
   codes and must not claim the older link was revoked.
12. Add share-specific abuse-control settings and repository constraints:
    - maximum request bytes
    - maximum rendered artifact bytes
    - maximum share creations per IP/window
    - maximum active guest shares per snapshot fingerprint or coarse IP bucket
      where feasible
    - expired-row purge command or scheduled operator path
    - metrics/log counters that avoid raw class, room, group, or student values
13. Ensure public helper logging/metrics use `public_helper_*` reason codes and
   do not retain raw student payloads.
14. Render from the canonical validated presentation model created by the
    export/snapshot materialization path. Persist renderer version,
    presentation schema version, presentation hash or immutable provenance, and
    content hash; never accept browser-supplied HTML, CSS, or preview metadata
    as the artifact source.

## Test Plan

- Backend tests for cookie-agnostic public share creation, payload caps,
  expected-revision conflicts, 60-day expiry ceiling, revoke-secret hashing, and
  supersede behavior.
- Backend tests asserting public guest shares cannot request or persist an
  expiry beyond the 60-day ceiling.
- Backend tests for payload-too-large, rendered-artifact-too-large,
  rate-limited, active-share ceiling, expired-share purge, no owner-scoped row
  creation, ambient-cookie ignoring, and rejected account identifiers.
- Route tests proving helper creation routes ignore ambient sessions and public
  token read routes avoid owner-scoped APIs, SPA shell fallback, and account
  authority.
- Renderer/provenance tests proving hostile class, room, group, and student
  values are escaped in body text, title, preview metadata, and CSS-adjacent
  contexts, with renderer/schema/hash fields persisted.
- Backend tests for retry idempotency, invalid previous secret fallback,
  double-create races, and active-link counting for the same snapshot/draft
  kind.
- Backend/web tests for public guest current-link revoke: matching
  `public_path + revoke_secret` revokes the active public guest artifact,
  invalid secrets do not revoke, ambient sessions are ignored, authenticated or
  owner-scoped APIs are not used, and revoked token URLs no longer render as
  active.
- Frontend tests for guest export menu placement, snapshot flush before share
  creation, copy-link UI, previous-link revoke payload, and
  missing-revoke-secret fallback.
- Frontend tests for the public share popover showing the newly created share
  immediately, using the aligned authenticated popover row/action layout,
  invoking public remove/revoke for the current browser-owned link, and removing
  the row after success without archive/dead-link UI.
- Anonymous browser proof for public grouping and seating share creation,
  popover copy/remove, opening links before and after revoke, and confirming no
  authenticated API calls occur.
- Regression proof that public PDF/Excel export behavior is unchanged.
- `pdm run lint`
- `pdm run typecheck`
- `pdm run docs-validate`
- `pdm run handoff-validate` if `.codex/handoff.md` records live UI proof.
- `git diff --check`

## Implementation Notes

Reopen note (2026-04-30): the shipped state below remains the baseline for
create/supersede, but the slice is reopened to add explicit public
current-link revoke/remove. The follow-up must not create a public guest share
dashboard or server-side listing surface.

- 2026-05-01 follow-up implemented the current-link browser-owned revoke path:
  `POST /api/v1/public/apps/classroom.group-seating-studio/share/revoke`
  accepts only `public_path` plus browser-held `revoke_secret`, hashes both
  server-side, revokes the matching active `public_guest` artifact, and returns
  the revoked artifact without adding any public listing/dashboard surface.
- The public guest share popover now keeps the authenticated copy/remove row
  pattern: newly created links appear immediately, copy uses the shared row
  affordance, remove calls the narrow public helper, and successful remove
  clears the row plus browser-held newest-link metadata.
- 2026-05-01 review-gap closure persists the newest browser-owned display row
  with the revoke metadata, hydrates it after a fresh SPA reload for the same
  snapshot/draft kind, and keeps old metadata usable for supersede even when it
  lacks the display row.
- The public revoke helper keeps capped raw-body parsing while exporting an
  explicit OpenAPI request body for `public_path` and `revoke_secret`.
- Added dedicated public guest share helper routes for grouping and seating under
  `/api/v1/public/apps/classroom.group-seating-studio/*/share`.
- Public guest share rows are stored as `source = public_guest` with no owner,
  draft, roster, or template authority; they persist browser-supplied
  idempotency/supersede controls only as bounded metadata and hashed revoke
  secrets.
- The backend enforces strict snapshot revision matching, a 60-day TTL policy,
  rendered-size caps, public-helper request caps/rate limits, active-link
  ceilings, and expired guest-share purge support.
- The guest UI now exposes `Dela länk` beside PDF/Excel, flushes browser-owned
  draft state through the same export-preparation path, copies the public URL,
  and stores latest browser-held revoke metadata per snapshot plus draft kind.
- Public guest export/share frontend calls use the public API client with
  `credentials: "omit"` and do not bootstrap shared-auth CSRF.

## Verification

- Retained implementation review: `REV-PR-0273` approved the remediation,
  including PostgreSQL integration proof for the advisory-lock
  create/reuse/supersede path under independent concurrent sessions.
- `pdm run lint`
- `pdm run typecheck`
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run pytest -q tests/unit/application/apps/classroom_planner/test_share_artifacts.py tests/unit/application/apps/classroom_planner/test_public_shares.py tests/unit/web/test_public_apps_classroom_planner_shares.py tests/unit/web/test_public_apps_classroom_planner_exports.py tests/unit/web/apps/classroom_planner/test_share_api.py`
- `pdm run pytest -q tests/integration/infrastructure/repositories/test_classroom_planner_share_artifacts.py tests/integration/infrastructure/repositories/test_classroom_planner_public_guest_share_concurrency.py`
- `pdm run fe-test -- --run src/views/apps/components/PlannerExportActionGroup.spec.ts src/views/apps/usePublicGroupingExportFlow.spec.ts src/views/apps/usePublicSeatingExportFlow.spec.ts`
- `pdm run pytest -q tests/unit/application/apps/classroom_planner/test_public_shares.py tests/unit/web/test_public_apps_classroom_planner_shares.py`
- `pdm run fe-test -- --run src/views/apps/classroomPlannerPublicShareFlow.spec.ts src/views/apps/components/PlannerShareLinksPanel.spec.ts src/views/apps/components/PlannerSeatingWorkspaceToolbar.overflow.spec.ts`
- `pdm run fe-gen-api-types`
- 2026-05-01 review-gap closure:
  `pdm run fe-test -- --run src/views/apps/classroomPlannerPublicShareFlow.spec.ts`
  covered fresh-flow localStorage hydration and revoke after reload;
  `pdm run pytest -q tests/unit/web/test_public_apps_classroom_planner_shares.py`
  covered the exported revoke request body; regenerated
  `frontend/apps/skriptoteket/src/api/openapi.d.ts` now exports
  `public_path` and `revoke_secret` instead of `requestBody?: never`.
- In-app browser proof on `http://127.0.0.1:5173/public/apps/classroom.group-seating-studio`:
  created a public seating share, confirmed the active popover row rendered,
  opened the public URL before revoke, revoked from the popover, confirmed the
  row disappeared, and reloaded the public URL to the unavailable-link page.
- `pdm run dev-stack ps`
- `curl -sSf http://127.0.0.1:8000/healthz`
- `curl -sSf http://127.0.0.1:5173/`
- `pdm run pytest -q tests/unit/test_docker_dev_shared_auth_contract.py tests/unit/web/test_profile_app_continuation_api.py tests/unit/web/test_profile_app_continuation_context_api.py`
- In-app browser route check:
  `http://127.0.0.1:5173/public/apps/classroom.group-seating-studio` loaded
  the public Klassrumskartan guest page with local HuleEdu login/register links
  and no app-local login route.

## Rollback Plan

Hide the public guest `Dela länk` action and disable public share creation.
Existing guest share artifacts can expire naturally or be administratively
revoked if the share route itself must be disabled.
