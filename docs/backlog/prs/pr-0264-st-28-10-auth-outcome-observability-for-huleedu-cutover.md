---
type: pr
id: PR-0264
title: "ST-28-10 auth outcome observability for HuleEdu cutover"
status: done
owners: "agents"
created: 2026-04-13
updated: 2026-04-15
stories:
  - "ST-28-10"
adrs:
  - "ADR-0018"
  - "ADR-0019"
  - "ADR-0026"
  - "ADR-0083"
dependencies:
  - "PR-0254"
  - "PR-0263"
  - "REV-PR-0254"
  - "REV-PR-0263"
  - "PR-0258"
  - "PR-0260"
  - "PR-0261"
  - "PR-0262"
  - "REV-PR-0264"
tags: ["auth", "observability", "metrics", "logging", "huleedu"]
acceptance_criteria:
  - "Given Skriptoteket no longer owns browser sessions, when auth observability ships, then it does not recreate `skriptoteket_active_sessions` or infer active sessions from cookies, frontend state, or removed local session tables."
  - "Given protected browser `/api` traffic reaches Skriptoteket through the HuleEdu Gateway, when signed internal identity context is accepted or rejected, then Skriptoteket emits low-cardinality metrics and structured logs for verification success/failure with correlation id and sanitized reason only."
  - "Given product identity realms are active, when app-continuation resolves or rejects a realm-aware context, then projection outcomes distinguish `resolved`, `provisioned`, `missing`, `blocked_provisioning`, `linking_required`, and `unsupported_realm` without logging raw subject ids, emails, signed headers, cookies, CSRF tokens, or request bodies."
  - "Given local RBAC remains Skriptoteket-owned, when a protected app route denies access, then observability records the local RBAC decision using only bounded labels such as required role, actual local role, decision, and route pattern."
  - "Given CSRF and logout are HuleEdu Gateway/session authority, when operators triage CSRF/logout failures, then the Skriptoteket runbook separates HuleEdu-owned Gateway/session signals from Skriptoteket-owned app write/projection/RBAC signals."
  - "Given `PR-0254` retained the final cross-app proof, when the proof is rerun with a known `X-Correlation-ID`, then the runbook explains how to find the matching Skriptoteket logs/metrics and how to hand off the same id to HuleEdu Gateway logs."
  - "Given auth outcome metrics are added, when `/metrics` is scraped, then all new labels are bounded enum-like values and no metric label contains user id, realm subject id, email, raw URL, token, header payload, or free-form exception text."
  - "Given auth outcome logs are added, when tests exercise success and failure branches, then log assertions prove event names, outcome fields, correlation ids, and redaction policy without depending on implementation-private repositories."
---

## Problem

`PR-0254` and `PR-0263` prove the cross-app auth path works. Operators still lack a normal
operational view of what happened when that path succeeds or fails.

The old local browser-session metrics are intentionally gone. Recreating them inside Skriptoteket
would blur the new ownership boundary. The new signal surface must observe the cutover path as it
exists now:

- HuleEdu Gateway owns browser session, CSRF ceremony, logout authority, provider lifecycle, and
  product realm selection ceremony telemetry.
- Skriptoteket owns signed app-continuation verification, realm-aware projection resolution,
  provisioning-required outcomes, local `User.role` RBAC, and consumer-side proof/runbook evidence.

## Goal

Add the first narrow Skriptoteket-owned auth outcome observability slice for the HuleEdu cutover.
The slice should make app-continuation, projection, local RBAC, and consumer-side failure modes
visible without trying to instrument all HuleEdu provider/Gateway lifecycle behavior from this
repo.

## Non-goals

- Recreating local browser-session gauges or login attempt metrics from local session state.
- Instrumenting HuleEdu Gateway, HuleEdu Identity, provider registration, password reset,
  verification delivery, or browser-session lifecycle inside Skriptoteket.
- Adding high-cardinality labels, raw identity values, request bodies, signed header payloads, raw
  URLs, cookies, CSRF tokens, JWT/signature material, raw subjects, or emails to logs or metrics.
- Building Grafana dashboards or alerts in this first slice unless the implementation needs a tiny
  query example to prove the metric shape.
- Changing auth behavior, provisioning semantics, local roles, or the `PR-0254` proof contract.

## Review Gate

Implementation must not begin until `REV-PR-0264` is approved. The review should explicitly check
that this PR observes the new HuleEdu-owned browser auth model instead of smuggling local browser
auth/session ownership back into Skriptoteket.

## Ownership Split

| Outcome family | Owner | This PR scope |
|----------------|-------|---------------|
| Browser session valid/invalid | HuleEdu Gateway/Identity | Document handoff/correlation only |
| Product realm ceremony selection | HuleEdu Gateway/Identity | Document handoff; count only unsupported/missing realm after signed context reaches Skriptoteket |
| Provider lifecycle and continuation | HuleEdu Gateway/Identity | Document handoff; preserve consumer-side proof interpretation |
| Signed internal identity verification | Skriptoteket | Add sanitized logs/metrics |
| App continuation/projection resolution | Skriptoteket | Add sanitized logs/metrics |
| Provisioning-required/linking-required outcomes | Skriptoteket | Add sanitized logs/metrics |
| Local `User.role` RBAC decisions | Skriptoteket | Add sanitized logs/metrics |
| CSRF/logout failures | HuleEdu Gateway/session authority, with Skriptoteket writes as consumers | Document split and record only app-side reached outcomes |

## Proposed Signal Contract

The implementation should prefer one small protocol-first recorder over scattered ad hoc
`logger.info(...)` and metric calls. The recorder can live behind a protocol such as
`AuthOutcomeRecorderProtocol` and a concrete observability implementation wired through Dishka if
that keeps the auth dependencies small and testable.

Candidate metric families:

| Metric | Type | Bounded labels |
|--------|------|----------------|
| `skriptoteket_auth_context_verifications_total` | Counter | `outcome`, `reason` |
| `skriptoteket_auth_projection_outcomes_total` | Counter | `realm`, `outcome`, `reason` |
| `skriptoteket_auth_rbac_decisions_total` | Counter | `decision`, `required_role`, `actual_role`, `route_family` |

Candidate structured log events:

| Event | Level | Fields |
|-------|-------|--------|
| `auth.internal_identity.verified` | info | `outcome`, `reason`, `correlation_id` |
| `auth.internal_identity.rejected` | warning | `outcome`, `reason`, `correlation_id` |
| `auth.projection.resolved` | info | `realm`, `outcome`, `reason`, `correlation_id` |
| `auth.projection.rejected` | warning | `realm`, `outcome`, `reason`, `correlation_id` |
| `auth.rbac.denied` | warning | `required_role`, `actual_role`, `route_family`, `correlation_id` |

Allowed values must be enums or otherwise bounded. `reason` must come from existing `DomainError`
details or explicit constants, then be normalized into a bounded allowlist.

## Implementation Plan

1. Review the current observability and auth path before editing:
   - `src/skriptoteket/observability/metrics.py`
   - `src/skriptoteket/observability/logging.py`
   - `src/skriptoteket/web/middleware/correlation.py`
   - `src/skriptoteket/infrastructure/security/huleedu_internal_identity.py`
   - `src/skriptoteket/web/auth/huleedu_app_projection.py`
   - `src/skriptoteket/application/identity/huleedu_app_projection.py`
   - `src/skriptoteket/domain/identity/role_guards.py`
2. Add a small auth outcome recorder contract. Keep route/auth dependencies protocol-first and
   avoid coupling domain code to Prometheus, structlog, FastAPI, or SQLAlchemy.
3. Add Prometheus counters in `src/skriptoteket/observability/metrics.py`, using duplicate
   registration recovery like the existing metrics singleton and bounded labels only.
4. Record signed-context verification success/failure around the app auth dependency boundary.
   Preserve the verifier's fail-closed `DomainError` behavior.
5. Record projection/provisioning outcomes near the application resolver branch that already
   creates `identity_projection_events`, without duplicating raw identity data in logs or labels.
6. Record local RBAC denials at the central web `DomainError` boundary so dependency-level and
   route/application-handler role guard failures are both observed while domain role guards stay
   pure.
7. Update observability runbooks so the operator triage flow starts from a known
   `X-Correlation-ID`, then separates HuleEdu Gateway/session/lifecycle signals from
   Skriptoteket app-continuation/projection/RBAC signals.
8. Add focused tests for:
   - metric creation and duplicate registration behavior
   - no `skriptoteket_active_sessions` metric
   - bounded auth outcome labels
   - structured log event names and correlation ids
   - no raw subject/email/signed-header/CSRF values in emitted auth outcome fields
   - RBAC denial emits an outcome without changing authorization semantics

## Third-Party Library Notes

The planning pass checked current docs for the libraries already in this repo:

- Structlog context variables should be cleared and rebound at request boundaries, with
  `merge_contextvars` in the processor chain, matching the existing correlation middleware model.
- `prometheus_client` counters with labels are the right primitive for event outcomes, but labels
  must stay bounded and initialized deliberately where useful.
- OpenTelemetry span attributes/events are suitable for safe business-operation annotations, but
  this PR should only add tracing events if the implementation remains small and sanitized.

## Test Plan

- `pdm run pytest -q tests/unit/observability`
- `pdm run pytest -q tests/unit/web/test_profile_app_continuation_api.py`
- `pdm run pytest -q tests/unit/web/test_profile_app_continuation_context_api.py`
- `pdm run pytest -q tests/unit/application/auth/test_pr_0254_auth_cutover_manifest.py`
- `pdm run lint`
- `pdm run typecheck`
- `pdm run docs-validate`
- `git diff --check`

If implementation touches frontend logout/CSRF behavior or proof helpers, add:

- `pdm run fe-test -- --run src/stores/auth.csrf.spec.ts src/stores/auth.logout.spec.ts`
- `pdm run fe-type-check`
- `pdm run fe-lint`

If implementation changes live proof behavior, rerun:

- `pdm run pr-0254-auth-cutover --include-127-lane --require-127-lane`

## Runbook Requirements

Before this PR can close, update the relevant observability runbooks with:

- the new metric names and label meanings
- the new structured log event names
- a correlation-id based local triage command sequence
- a HuleEdu handoff section naming which Gateway/session/lifecycle outcomes are upstream-owned
- failure interpretation for signed-context verification, unsupported realm, missing projection,
  provisioning blocked, linking required, local RBAC denial, CSRF write rejection, and logout
  invalidation

## Implementation Summary

Implemented on 2026-04-15 after `REV-PR-0264` approval.

- Added `AuthOutcomeRecorderProtocol` and a Prometheus/Structlog implementation.
- Added bounded counters:
  `skriptoteket_auth_context_verifications_total`,
  `skriptoteket_auth_projection_outcomes_total`, and
  `skriptoteket_auth_rbac_decisions_total`.
- Added sanitized structured events for signed-context verification, projection/provisioning
  outcomes, and local RBAC denials.
- Wired the recorder through Dishka into the app auth dependency, central `DomainError` middleware,
  and projection resolver without changing auth behavior.
- Resolved the 2026-04-15 `changes_requested` follow-up by moving RBAC denial recording out of the
  dependency-only guard path and into the error boundary that also catches route/application-handler
  role guard failures after `require_app_user_api`.
- Addressed the latest 2026-04-15 review findings locally by routing eval-mode and draft-lock
  force-takeover role denials through role guard metadata, adding regression coverage for the
  direct route/application-handler RBAC path, and replacing new `Any` / `cast(...)` usage with
  narrow protocols and typed metric collector helpers.
- Updated logging and metrics runbooks with correlation-id triage and HuleEdu handoff guidance.

Verification:

- `pdm run pytest -q tests/unit/observability/test_auth_outcomes.py
  tests/unit/web/test_profile_app_continuation_api.py
  tests/unit/web/test_profile_app_continuation_context_api.py
  tests/unit/web/test_observability_routes.py
  tests/unit/web/test_error_handler_middleware.py` (pass; 48 tests).
- `pdm run pytest -q tests/unit/observability` (pass; 49 tests).
- `pdm run ruff check ...` on the touched implementation/test files (pass).
- `pdm run docs-validate` (pass).
- `pdm run typecheck` (pass).
- `pdm run lint` (pass).
- `pdm run pytest -q tests/unit/observability/test_auth_outcomes.py
  tests/unit/web/test_error_handler_middleware.py tests/unit/web/test_profile_app_continuation_api.py
  tests/unit/web/test_editor_inline_completion_api.py
  tests/unit/web/test_editor_edit_ops_preview_apply_api.py
  tests/unit/application/scripting/handlers/test_draft_lock_handler.py` (pass; 38 tests).
- `pdm run pytest -q tests/unit/web -x` (pass; 294 tests).
- `git diff --check` (pass).
- `pdm run pr-0254-auth-cutover --include-127-lane --require-127-lane` (pass; retained
  `.artifacts/playwright-pr-0254-auth-cutover/local-nonprod/20260415T092404Z/manifest.redacted.json`).

## Rollback Plan

Remove the recorder wiring, auth outcome metrics, and runbook additions together if the signal
contract proves too broad or leaks ownership. Keep `ST-28-10` open until the replacement plan
preserves the HuleEdu/Skriptoteket boundary without local session metrics.
