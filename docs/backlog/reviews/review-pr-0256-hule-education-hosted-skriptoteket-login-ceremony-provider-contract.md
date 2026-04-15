---
type: review
id: REV-PR-0256
title: "Review: PR-0256 Hule Education-hosted Skriptoteket login ceremony provider contract"
status: approved
owners: "agents"
created: 2026-04-12
updated: 2026-04-12
reviewer: "Codex ruthless-code-review"
prs:
  - PR-0256
adrs:
  - ADR-0083
links:
  - EPIC-28
  - ST-28-07
  - ST-28-08
  - ST-28-09
  - PR-0253
  - PR-0254
  - PR-0255
  - REV-ST-28-06
  - REF-hule-education-product-identity-realms-and-skriptoteket-standalone-identity
---

## TL;DR

`PR-0256` is approved. The original provider blockers are closed by HuleEdu `TASK-0313`,
`TASK-0314`, and approved `REV-TASK-0313-01`; Skriptoteket now points `/auth/login` at the
browser-navigable HuleEdu `GET /auth/login` ceremony with `app=skriptoteket`, default
`product_identity_realm=skriptoteket_standalone`, callback `return_to`, and safe route-level
`next`. `/auth/callback` resumes the intended protected route after shared-session bootstrap.

## Problem Statement

The story asks Skriptoteket to send signed-out users into one Hule Education-hosted
`app=skriptoteket` ceremony and then receive realm-aware gateway context. The provider side is now
publicly proved, so the remaining review question is whether Skriptoteket consumes that contract
without reopening local browser auth or moving `ST-28-09` projection work into this slice.

## Proposed Solution

Approve the consumer implementation because it:

- builds the ceremony URL from the retained HuleEdu `GET /auth/login` contract
- keeps `next` as a same-origin path and sends `return_to` to `/auth/callback`
- keeps `/auth/login` as a transition surface with no local credential form
- accepts additive realm-aware signed context fields without changing projection lookup yet
- proves the contract with focused Vitest, backend continuation tests, and a live Playwright proof

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-0256-st-28-07-hule-education-hosted-skriptoteket-login-ceremony-provider-contract.md` | Implementation package and provider-clearance evidence | 15 min |
| `docs/backlog/stories/story-28-07-hule-education-hosted-skriptoteket-login-ceremony.md` | Story acceptance and current status | 8 min |
| `docs/adr/adr-0083-hule-education-product-identity-realms-for-skriptoteket-login.md` | Accepted realm and ceremony contract | 10 min |
| `frontend/apps/skriptoteket/src/api/sharedAuth.ts` | Current temporary ceremony helper | 5 min |
| `frontend/apps/skriptoteket/src/components/auth/AuthLoginPanel.vue` | Current login handoff UI | 5 min |
| `frontend/apps/skriptoteket/src/composables/auth/authEntryNavigation.ts` | Safe `next` sanitation | 5 min |
| `src/skriptoteket/domain/identity/internal_identity_context.py` | Realm-aware additive context acceptance | 5 min |
| `scripts/playwright_pr_0256_auth_ceremony.py` | Live ceremony/callback proof | 10 min |
| HuleEdu `docs/reference/ref-shared-browser-session-consumer-conformance-v1.md` | Published provider endpoint contract | 5 min |
| HuleEdu `docs/reference/ref-internal-identity-context-v1-contract.md` | Published downstream context fields | 5 min |
| HuleEdu `TASK-0314` | Public provider proof closeout | 5 min |

**Total estimated time:** ~68 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Create `PR-0256` as the `ST-28-07` implementation package | Gives the login ceremony work a reviewable owner | [x] |
| Consume HuleEdu `GET /auth/login` with `app`, realm, `return_to`, and safe `next` | Matches the approved provider contract | [x] |
| Accept additive realm-aware downstream context before projection migration | Prevents verifier breakage while preserving `ST-28-09` scope | [x] |
| Keep `/auth/login?next=...` as a transition surface, not a local form | Preserves `PR-0253` hard-retirement and `ST-32-10` route semantics | [x] |
| Defer registration/password lifecycle and projection migration | Keeps `ST-28-08` and `ST-28-09` separate | [x] |

## Review Checklist

- [x] Scope is bounded to `ST-28-07`
- [x] Provider gap is closed by concrete HuleEdu artifacts
- [x] PR does not reintroduce local browser auth or bearer storage
- [x] PR does not implement `ST-28-08`, `ST-28-09`, or final `PR-0254` smoke
- [x] Verification plan includes focused Vitest, live Playwright, docs validation, and diff hygiene
- [x] Blocker is actionable rather than vague

## Review Feedback

**Reviewer:** `Codex ruthless-code-review`
**Date:** `2026-04-12`
**Verdict:** `approved`

### Required Changes

1. **resolved - HuleEdu provider has retained browser-navigable product-realm ceremony**

   File references:
   `docs/backlog/prs/pr-0256-st-28-07-hule-education-hosted-skriptoteket-login-ceremony-provider-contract.md`
   and HuleEdu `services/api_gateway_service/routers/auth_routes.py:30`.

   HuleEdu `TASK-0313` and `TASK-0314` now publish and publicly prove the browser ceremony route:
   `GET /auth/login` with `app=skriptoteket`, default
   `product_identity_realm=skriptoteket_standalone`, explicit `huleedu_school`, allowlisted
   `return_to`, and safe same-origin `next`.

   Proof: `scripts/playwright_pr_0256_auth_ceremony.py` verifies the `/auth/login` href points at
   `https://api.hule.education/auth/login`, never `/v1/auth/login`, and carries the expected app,
   realm, callback, and `next` parameters.

2. **resolved - downstream identity context carries the realm fields required by `ADR-0083`**

   File references:
   `docs/adr/adr-0083-hule-education-product-identity-realms-for-skriptoteket-login.md`
   and HuleEdu `docs/reference/ref-internal-identity-context-v1-contract.md:60`.

   HuleEdu `InternalIdentityContextV1` now includes optional additive `active_app`,
   `active_product_identity_realm`, `realm_subject_id`, and `linked_identity_ids` fields.
   Skriptoteket accepts those fields and optional standalone org/tenant context while keeping
   projection lookup by existing subject until `ST-28-09`.

   Proof: `tests/unit/web/test_profile_app_continuation_api.py` accepts standalone realm context
   without org/tenant and rejects blank realm fields or linked identity ids.

3. **resolved - query/hash continuation was dropped on auth success**

   File reference:
   `frontend/apps/skriptoteket/src/composables/auth/authEntryNavigation.ts`.

   The original implementation returned `{ path: sanitizedNextPath }` for normal auth-success
   destinations. Vue Router normalizes an object `path` without parsing embedded query/hash, so a
   route such as `/admin/tools?status=draft#review` could resume as `/admin/tools`.

   Fix: normal auth-success destinations now return the sanitized route string directly. Focused
   tests exercise both the guard/view return value and Vue Router normalization through an in-memory
   router. The live proof now resumes `/editor?draft=head#debug`.

4. **resolved - ceremony helper accepted unsafe `next` values**

   File reference:
   `frontend/apps/skriptoteket/src/api/sharedAuth.ts`.

   The exported ceremony helper now sanitizes its own `nextPath` input before writing the HuleEdu
   URL. It drops absolute URLs, protocol-relative URLs, and auth-entry loops even if a future caller
   forgets to sanitize first. Focused tests cover hostile `next` values and safe query/hash
   preservation.

5. **resolved - realm fields were passively accepted without app/realm validation**

   File references:
   `src/skriptoteket/domain/identity/internal_identity_context.py` and
   `src/skriptoteket/application/identity/huleedu_app_projection.py`.

   App continuation now requires the signed context to be scoped to `active_app=skriptoteket`, one
   of the accepted realms (`skriptoteket_standalone`, `huleedu_school`), and a present
   `realm_subject_id` before local projection lookup. It still resolves the existing projection by
   `context.sub`; the realm-aware projection key migration remains `ST-28-09`.

### Suggestions (Optional)

- Prefer a provider parameter name that is explicit, such as `product_identity_realm`, unless
  HuleEdu publishes a different canonical name.
- Keep the current `VITE_HULEEDU_AUTH_ENTRY_URL` escape hatch for topology changes.
- If HuleEdu implements auto-handoff, keep an accessible pause/fallback state for popup blockers,
  navigation failures, or disabled JavaScript.

### Decision Approvals

- [x] Create `PR-0256` as the `ST-28-07` implementation package
- [x] Consume HuleEdu `GET /auth/login` with `app`, realm, callback, and safe `next`
- [x] Accept additive realm-aware downstream context before projection migration
- [x] Keep `/auth/login?next=...` as a transition surface, not a local form
- [x] Defer registration/password lifecycle and projection migration

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | HuleEdu provider clearance | Consumed `TASK-0313`, `TASK-0314`, and approved `REV-TASK-0313-01` as blocker closeout |
| 2 | `PR-0256` | Implemented the provider-approved ceremony URL, callback route, and realm-aware context acceptance |
| 3 | Review remediation | Preserved query/hash auth continuation, hardened helper-level `next`, and enforced app/realm context before projection lookup |
| 4 | `ST-28-07` | Marked the story done after focused tests and live Playwright proof |
| 5 | `EPIC-28` | Updated the implementation summary and next sequence |
| 6 | `.codex/handoff.md` | Updated current lane, verification, known risk, and next step |
