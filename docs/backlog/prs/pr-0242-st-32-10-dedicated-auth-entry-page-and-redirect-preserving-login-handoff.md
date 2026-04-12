---
type: pr
id: PR-0242
title: "ST-32-10: dedicated auth-entry page and redirect-preserving login handoff"
status: done
owners: "agents"
created: 2026-04-08
updated: 2026-04-08
stories:
  - "ST-32-10"
tags: ["frontend", "auth", "routing", "public-access", "ux"]
dependencies:
  - "ST-32-10"
  - "PR-0240"
  - "ST-11-22"
acceptance_criteria:
  - "Given a signed-out visitor starts auth from the landing shell or public curated-app entry surfaces, when they choose `Logga in`, then Skriptoteket routes them to the canonical dedicated auth-entry page `/auth/login` instead of opening an in-place modal on the current page."
  - "Given the auth-entry page receives an intended destination, when login succeeds, then the visitor lands on the correct authenticated destination through an explicit route-level redirect contract rather than transient modal-local state."
  - "Given the current signed-out auth surfaces include `/`, `/register`, `/forgot-password`, `/reset-password`, `/verify-email`, and `/public/apps/classroom.group-seating-studio`, when this slice ships, then those entry points share the same auth-entry page contract instead of each wiring modal behavior independently."
  - "Given the HuleEdu shared browser-session/product-realm ceremony requires a top-level redirect or hosted ceremony, when this slice is implemented, then the new auth-entry contract is page-based and redirect-friendly rather than modal-coupled."
  - "Given the old `/login` route was deliberately removed, when this slice ships, then it does not act as any auth alias or compatibility path and instead falls through normal SPA recovery/not-found behavior."
---

## Result

`PR-0242` is now implemented locally and review-approved.

The shipped slice makes `/auth/login` the only auth-entry contract, removes any auth-specific
handling for exact `/login`, preserves sanitized `next` across register/forgot/reset/verify detours
plus backend-generated verification/reset links, and keeps Klassrumskartan's
`classroomPlannerEntryOrigin` as supplemental route state without letting it become the durable
redirect truth.

The canonical frontend/browser verification trail for this slice is now also green and recorded in
`.agents/handoff.md`, including the focused auth Vitest sweep plus the canonical `ui-smoke`,
`ui-editor-smoke`, `ui-runtime-smoke`, and Flunk-Out Frenzy route proof on `http://127.0.0.1:5173`.

## Problem

The current signed-out auth-entry behavior is spread across an overloaded modal contract that now
handles too many route-specific and redirect-specific concerns.

That was acceptable when the product was still in a more prototype-like phase, but it is becoming a
liability as launch approaches and as the HuleEdu shared browser-session/product-realm ceremony needs come into view.

## Goal

Introduce one dedicated, redirect-preserving auth-entry page that replaces the current signed-out
modal-first login entry pattern on public and signed-out surfaces.

This slice is the owner of the `/auth/login` route contract that later
HuleEdu-session cutover work consumes.

## Redirect Contract To Implement

- The canonical auth-entry route is `/auth/login`.
- The durable intended destination must live in the route contract, with `next` as the default
  query parameter shape for this slice.
- `next` must only preserve same-origin absolute app paths (for example `/profile` or
  `/apps/classroom.group-seating-studio`). External URLs, malformed values, and auth-entry loops
  such as `/auth/login` or removed legacy placeholders such as `/login` must be ignored or
  normalized to the safe default destination.
- The route-level destination is the authoritative post-login target. No required redirect truth
  should remain inside `useLoginModal()` state or other route-local modal-only state after this
  slice lands.
- If a flow still needs richer app-specific navigation nuance than a path alone can carry
  (currently the known example is Klassrumskartan entry-origin state), that nuance may remain
  supplemental, but the durable destination itself must still be recoverable from the auth-entry
  route contract.
- Exact `/login` visits must not receive any auth-specific compatibility handling in this slice; they
  should fall through the normal SPA recovery/not-found path.

## Non-goals

- Reopening `PR-0240` route recovery work in the same slice.
- Reintroducing the old legacy `/login` route/page as it existed before `ST-11-22`.
- Changing authenticated dashboard behavior beyond what is needed for redirect completion.
- Implementing the HuleEdu provider ceremony itself in this slice.

## Implementation plan

1. Define one canonical page-based auth-entry route and view at `/auth/login`.
2. Replace signed-out landing-shell and public-entry `Logga in` affordances so they navigate to the
   auth-entry page instead of opening the shared in-place modal.
3. Move redirect preservation onto the explicit `/auth/login?next=...` route contract so
   destination intent survives refreshes, top-level redirects, and future external auth ceremonies
   more cleanly than the current modal-state approach.
4. Sanitize and normalize the `next` contract in one shared place:
   - allow only same-origin absolute app paths
   - reject auth-entry loops and malformed values
   - default to the safe authenticated home destination when no valid target remains
5. Keep current local auth fully working through the new page while making the handoff contract
   compatible with a HuleEdu-owned product-realm ceremony.
6. Preserve any still-needed richer app-specific route state only as a supplemental layer on top of
   the route-level destination contract, not as the sole redirect truth.
7. Keep `/auth/login` as the only auth-entry route and let exact `/login` fall through normal SPA
   recovery/not-found behavior instead of acting as an auth alias.
8. Audit current signed-out entry surfaces and unify them onto the new pattern:
   - `/`
   - `/public/apps/classroom.group-seating-studio`
   - `/register`
   - `/forgot-password`
   - `/reset-password`
   - `/verify-email`
   - any remaining signed-out auth interruption entry points touched by the SPA shell
9. Extract or reuse the existing local-password login form logic so the new auth-entry page remains
   the only signed-out auth-entry model and does not fork validation/recovery behavior.
10. Add focused router/view/auth tests plus a live browser proof for entry, redirect, and return
    behavior.

## Remediation Checklist (changes requested 2026-04-08)

- Remove exact `/login` compatibility support from the auth path entirely.
- Delete `LEGACY_LOGIN_PATH`, `isLegacyLoginPath`, and
  `buildLegacyLoginRecoveryLocation` from `authEntryNavigation.ts`.
- Remove the `/login` special-case branch from `index.ts`.
- Drop the `/login` compatibility tests from `index.spec.ts`.
- Let `/login` fall through to normal SPA recovery/not-found behavior instead of acting as an auth
  alias.
- Finish the type-safe redirect-contract cleanup in `authEntryNavigation.ts`.
- Fix `pdm run fe-type-check`; the current problems are the query-builder return type around line
  109 and the continuation-location typing around line 144.
- Fix the migrated auth tests so they match the new route-aware implementation instead of old
  assumptions.
- Update `ForgotPasswordView.spec.ts` so the router mock includes `useRoute()` and preserved
  `next`.
- Update `AuthLoginPanel.spec.ts` so it has real route context and named-route coverage for the
  forgot/register continuation links.
- Remove modal-era wording and breadcrumbs that will confuse future developers.
- Clean modal/compatibility wording out of `AuthLoginPanel.spec.ts`.
- Clean stale modal-auth notes out of `.agents/handoff.md`, including references to in-place modal
  login and the deleted `loginRedirects.ts`.
- Keep `/auth/login` as the single auth-entry contract. If `/login` compatibility is removed in
  code, keep that removal reflected in this PR doc and in `ST-32-10`.
- Re-prove that every signed-out auth surface only uses `/auth/login`:
  - `LandingLayout.vue`
  - `LandingAuthenticatedPreview.vue`
  - `RegisterView.vue`
  - `ForgotPasswordView.vue`
  - `ResetPasswordView.vue`
  - `VerifyEmailView.vue`
  - `App.vue` auth-drop interruption
- Close `PR-0242` only when the auth lane is single-model and green:
  - `pdm run fe-type-check`
  - focused Vitest for router/auth-entry/auth views
  - live browser proof for `/auth/login`, protected-route interruption, and return-to-origin
  - verification recorded in `.agents/handoff.md`

## Test plan

- Focused router/view tests for the dedicated auth-entry route, `next` sanitization, and redirect
  preservation.
- Focused auth-flow tests for signed-out entry points moving from modal-open to page navigation.
- Live browser proof on:
  - `http://127.0.0.1:5173/`
  - `http://127.0.0.1:5173/public/apps/classroom.group-seating-studio`
  - `http://127.0.0.1:5173/register`
  - `http://127.0.0.1:5173/verify-email`
  - `http://127.0.0.1:5173/auth/login`
- `pdm run fe-type-check`
- `pdm run docs-validate`

## Rollback plan

- Restore the current signed-out modal-entry behavior if the dedicated auth-entry route introduces
  redirect regressions, without undoing the separate `PR-0240` route-recovery work.
