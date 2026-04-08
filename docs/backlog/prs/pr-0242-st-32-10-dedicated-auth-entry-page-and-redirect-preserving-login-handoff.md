---
type: pr
id: PR-0242
title: "ST-32-10: dedicated auth-entry page and redirect-preserving login handoff"
status: ready
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
  - "ST-28-02"
acceptance_criteria:
  - "Given a signed-out visitor starts auth from the landing shell or public curated-app entry surfaces, when they choose `Logga in`, then Skriptoteket routes them to the canonical dedicated auth-entry page `/auth/login` instead of opening an in-place modal on the current page."
  - "Given the auth-entry page receives an intended destination, when login succeeds, then the visitor lands on the correct authenticated destination without relying on transient modal state."
  - "Given the current signed-out auth surfaces include `/`, `/register`, `/forgot-password`, `/reset-password`, and `/public/apps/classroom.group-seating-studio`, when this slice ships, then those entry points share the same auth-entry page contract instead of each wiring modal behavior independently."
  - "Given future HuleEdu SSO may require a top-level redirect or hosted ceremony, when this slice is implemented, then the new auth-entry contract is page-based and redirect-friendly rather than modal-coupled."
  - "Given the old `/login` route was deliberately removed, when this slice ships, then it does not reintroduce the old legacy `/login` page behavior; the new canonical auth-entry route is `/auth/login`."
---

## Problem

The current signed-out auth-entry behavior is spread across an overloaded modal contract that now
handles too many route-specific and redirect-specific concerns.

That was acceptable when the product was still in a more prototype-like phase, but it is becoming a
liability as launch approaches and as future HuleEdu SSO needs come into view.

## Goal

Introduce one dedicated, redirect-preserving auth-entry page that replaces the current signed-out
modal-first login entry pattern on public and signed-out surfaces.

## Non-goals

- Reopening `PR-0240` route recovery work in the same slice.
- Reintroducing the old legacy `/login` route/page as it existed before `ST-11-22`.
- Changing authenticated dashboard behavior beyond what is needed for redirect completion.
- Implementing HuleEdu SSO itself in this slice.

## Implementation plan

1. Define one canonical page-based auth-entry route and view at `/auth/login`.
2. Replace signed-out landing-shell and public-entry `Logga in` affordances so they navigate to the
   auth-entry page instead of opening the shared in-place modal.
3. Move redirect preservation onto an explicit route/page contract so destination intent survives
   refreshes, top-level redirects, and future external auth ceremonies more cleanly than the current
   modal-state approach.
4. Keep current local auth fully working through the new page while making the handoff contract
   compatible with a future HuleEdu-owned SSO ceremony.
5. Audit current signed-out entry surfaces and unify them onto the new pattern:
   - `/`
   - `/public/apps/classroom.group-seating-studio`
   - `/register`
   - `/forgot-password`
   - `/reset-password`
   - any remaining signed-out auth interruption entry points touched by the SPA shell
6. Add focused router/view/auth tests plus a live browser proof for entry, redirect, and return
   behavior.

## Test plan

- Focused router/view tests for the dedicated auth-entry route and redirect preservation.
- Focused auth-flow tests for signed-out entry points moving from modal-open to page navigation.
- Live browser proof on:
  - `http://127.0.0.1:5173/`
  - `http://127.0.0.1:5173/public/apps/classroom.group-seating-studio`
  - `http://127.0.0.1:5173/register`
  - `http://127.0.0.1:5173/auth/login`
- `pdm run fe-type-check`
- `pdm run docs-validate`

## Rollback plan

- Restore the current signed-out modal-entry behavior if the dedicated auth-entry route introduces
  redirect regressions, without undoing the separate `PR-0240` route-recovery work.
