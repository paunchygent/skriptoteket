---
type: story
id: ST-32-10
title: "Dedicated auth-entry page and redirect-preserving login handoff"
status: done
owners: "agents"
created: 2026-04-08
updated: 2026-04-08
epic: "EPIC-32"
dependencies:
  ["ADR-0011", "ADR-0027", "ST-11-22", "ST-32-07", "ST-32-08", "ST-32-09"]
acceptance_criteria:
  - "Given a signed-out visitor starts auth from `/`, `/public/apps/classroom.group-seating-studio`, or the signed-out auth routes, when auth entry begins, then Skriptoteket navigates to the canonical dedicated auth-entry page `/auth/login` instead of opening an in-place modal on the current page."
  - "Given the auth-entry page replaces the overloaded signed-out modal seam, when it renders, then it preserves an explicit intended post-login destination through a route-level contract without depending on route-local modal state."
  - "Given Skriptoteket still needs launch-ready local auth now and HuleEdu SSO later, when this story ships, then the page-based auth-entry contract remains compatible with a future top-level HuleEdu-owned auth ceremony while keeping `/auth/login` as the only auth-entry route."
  - "Given this story changes the signed-out auth contract, when implementation begins and ships, then the landing shell, public-entry surfaces, and signed-out auth pages all use the same dedicated auth-entry handoff instead of mixing modal-first and page-first entry patterns."
ui_impact: "Yes (signed-out auth entry, redirect handoff, and login/start-auth page)"
data_impact: "No"
---

## Context

The current signed-out login modal was acceptable during the prototype phase, but it is now carrying
too many responsibilities:

- landing entry
- public-app upgrade entry
- signed-out auth-route recovery
- redirect preservation
- future SSO handoff pressure

That coupling makes the current contract harder to reason about and less suitable for launch.

The next step after `ST-32-09` should separate concerns cleanly: route recovery stays in the route
recovery slice, while auth entry becomes a dedicated page with an explicit redirect-preserving
handoff contract.

## Notes

- This is not a request to restore the old legacy `/login` page as it existed before `ST-11-22`.
- Treat the new auth-entry page as a fresh contract, not as a rollback.
- The canonical auth-entry route for new work is `/auth/login`.
- Do not reopen the old `/login` semantics.
- This story owns the `/auth/login` route contract; later auth-authority cutover work in `ST-28-02`
  consumes that contract rather than defining it.
- The durable intended destination should move onto the auth-entry route contract itself, with a
  route-level `next` destination as the default shape for this slice.
- Exact `/login` should remain outside the auth contract and fall through normal SPA
  recovery/not-found behavior instead of acting as a compatibility alias.
- The important invariant is destination preservation and auth-handoff clarity, not keeping every
  auth step inside a modal forever.
- The page must be usable for current local auth while staying structurally compatible with a future
  HuleEdu-owned top-level SSO ceremony.
- If richer app-specific route state is still needed for a polished return path, treat it as
  supplemental to the durable route-level destination rather than the only redirect truth.
- Keep route recovery and auth-entry redesign in separate PR slices; `PR-0240` should land first.
- `PR-0242` is now implemented locally and review-approved: `/auth/login` owns the auth-entry
  contract, exact `/login` receives no auth-specific compatibility handling, backend verify/reset
  email links preserve sanitized continuation, Klassrumskartan auth detours preserve the
  supplemental planner origin, and the canonical Playwright/browser proofs now follow the real
  `/auth/login` lane instead of the retired `/login`/modal seam.

## Planned PR slices

- [PR-0242: ST-32-10 dedicated auth-entry page and redirect-preserving login handoff](../prs/pr-0242-st-32-10-dedicated-auth-entry-page-and-redirect-preserving-login-handoff.md)

## References

- Epic parent:
  [EPIC-32](../epics/epic-32-public-curated-app-access-foundation-and-klassrumskartan-demo.md)
- Immediate predecessor route-recovery slice:
  [ST-32-09](story-32-09-canonical-public-route-recovery-and-spa-unmatched-state.md)
- Public landing baseline:
  [ST-32-07](story-32-07-public-landing-entry-hierarchy-and-mockup-grounded-cta-cutover.md)
- Public landing showcase baseline:
  [ST-32-08](story-32-08-featured-public-app-showcase-and-authenticated-value-previews.md)
- Legacy modal-only login decision being superseded:
  [ST-11-22](story-11-22-remove-login-route.md)
- Future SSO-compatible auth interruption constraints:
  [ST-28-02](story-28-02-auth-interruption-and-protected-route-handoff-on-huleedu-owned-session.md)
- Federation direction:
  [ADR-0011](../../adr/adr-0011-huleedu-identity-federation.md)
