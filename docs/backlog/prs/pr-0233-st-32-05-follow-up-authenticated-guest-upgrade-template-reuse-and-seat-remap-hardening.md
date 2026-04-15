---
type: pr
id: PR-0233
title: "ST-32-05 follow-up: authenticated guest-upgrade template reuse and seat-remap hardening"
status: done
owners: "agents"
created: 2026-04-07
updated: 2026-04-07
stories:
  - "ST-32-05"
tags:
  [
    "backend",
    "klassrumskartan",
    "guest-upgrade",
    "import-policy",
    "remediation",
    "regression-hardening",
  ]
dependencies:
  - "ADR-0079"
  - "ST-32-04"
  - "ST-32-05"
  - "PR-0221"
acceptance_criteria:
  - "Given authenticated guest-upgrade preview sees existing account-owned room templates that do not exactly match the submitted guest template geometry, when reuse is evaluated, then the route does not select an unrelated template, does not raise `500 Internal server error`, and continues through the existing non-destructive import policy."
  - "Given the submitted guest template exactly matches an existing account-owned room template and seating drafts or checkpoints reference guest seat ids, when authenticated guest-upgrade preview or commit runs, then the route returns a structured `reused` template receipt and deterministically remaps seating draft/checkpoint seat ids to the reused server template without lookup failures."
  - "Given the authenticated Klassrumskartan host loads a real browser-owned guest snapshot containing roster, room template, seating draft, and export-backed checkpoint continuity, when the pending guest-upgrade preview runs, then the prompt no longer shows `Internal server error` and the canonical authenticated `/api/v1/apps/classroom.group-seating-studio/guest-upgrade` transport remains unchanged."
  - "Given `PR-0232` later adds guest export-backed checkpoint continuity on the public side, when this remediation lands, then the authenticated import seam accepts those non-toy template-bearing snapshots without introducing a new guest-only compatibility shape or reopening the public/auth boundary."
---

## Problem

The authenticated Klassrumskartan guest-upgrade prompt is currently broken for
real template-bearing snapshots. A live authenticated preview request against
`/api/v1/apps/classroom.group-seating-studio/guest-upgrade` reproduced
`500 Internal server error`, and the backend traceback now narrows the fault to
the room-template reuse seam:

- `guest_upgrade_assets.py` selects a reused template through a comparison that
  never actually fingerprints the existing server template geometry.
- that false-positive reuse path then tries to remap guest seat ids against
  unrelated template coordinates and raises `KeyError`.
- the bug stays latent in toy snapshots without templates, which is why the
  route-level happy-path tests and grouping-only live checks still passed.

This is pre-existing `PR-0221` debt, but it now matters more because
`PR-0232` depends on the same authenticated import seam for later guest export
continuity.

## Goal

Repair the authenticated guest-upgrade template reuse boundary so preview and
commit can safely process non-toy template-bearing snapshots, while preserving
the already approved route shape, import policy, and guest/public separation.

## Non-goals

- Redesigning the authenticated guest-upgrade prompt UX.
- Changing registration-vs-login import timing.
- Reopening `PR-0232` guest export/public route design in this remediation.
- Adding guest-only compatibility shims for malformed checkpoint payloads.
- Broadening the fix into a generic cross-app import framework.

## What shipped

1. [src/skriptoteket/application/curated_apps/classroom_planner/handlers/guest_upgrade_template_reuse.py](../../../src/skriptoteket/application/curated_apps/classroom_planner/handlers/guest_upgrade_template_reuse.py)
   now owns the exact-match room-template signature and deterministic seat-id
   remap helper logic so the authenticated asset importer stays under the repo
   size budget and compares guest templates to real persisted template geometry.
2. [src/skriptoteket/application/curated_apps/classroom_planner/handlers/guest_upgrade_assets.py](../../../src/skriptoteket/application/curated_apps/classroom_planner/handlers/guest_upgrade_assets.py)
   now reuses only exact template matches and no longer falls into the old
   false-positive reuse path that could raise `KeyError` during seating/checkpoint
   remap.
3. Focused regressions now lock the seam in:
   - [tests/unit/application/apps/classroom_planner/test_guest_upgrade_template_reuse.py](../../../tests/unit/application/apps/classroom_planner/test_guest_upgrade_template_reuse.py)
   - [tests/unit/web/apps/classroom_planner/test_guest_upgrade_api.py](../../../tests/unit/web/apps/classroom_planner/test_guest_upgrade_api.py)
4. Live proof on 2026-04-07 passed both at the route seam and in the browser
   using the real local `SA24D` roster plus `G20` classroom fixtures:
   - authenticated `POST /api/v1/apps/classroom.group-seating-studio/guest-upgrade`
     preview returned `200 OK` with the template marked `reused`
   - authenticated `http://127.0.0.1:5173/apps/classroom.group-seating-studio`
     showed the guest-upgrade modal without the previous `Internal server error`
     message after injecting a non-toy guest snapshot into browser storage

## Implementation plan

1. Lock the failing seam in tests before code changes.
   - Add a focused application-level regression that reproduces the current
     false-positive template reuse path with at least one unrelated existing
     template plus one guest seating/template payload.
   - Add a route-level regression that proves authenticated preview returns a
     structured receipt instead of `500` for template-bearing snapshots.
   - Extend the current idempotency/remap coverage so seating drafts and
     export-backed checkpoints are exercised through the reused-template path,
     not only through created-template paths.

2. Replace the template reuse predicate with a canonical exact-match check.
   - Compare the guest template against actual existing server template
     geometry/fixtures/grid content instead of comparing the guest template to a
     mutated copy of itself.
   - Keep the decision boundary narrow: exact-content match => `reused`;
     otherwise continue with the existing non-destructive policy.

3. Harden seat remapping on reused templates.
   - Move the coordinate-key logic into one small helper so seat remap behavior
     is deterministic and testable.
   - Detect missing or ambiguous coordinate matches explicitly and convert them
     into structured conflict/non-reuse behavior instead of uncaught
     exceptions.
   - Keep the handler protocol-first and contained inside the existing
     authenticated guest-upgrade collaborators.

4. Re-prove the live authenticated seam on non-toy data.
   - Re-run the authenticated route/prompt proof with the real local `SA24D`
     roster and `G20` classroom fixtures when available.
   - If those exact fixtures are unavailable in the active lane, create one
     similarly non-toy local snapshot fixture that includes:
     - a roster with multiple students
     - a reusable room template
     - a seating draft
     - at least one export-backed checkpoint descriptor
   - Record the exact route and live verification evidence in
     `.codex/handoff.md`.

## Test plan

- `pdm run pytest tests/unit/application/apps/classroom_planner/test_guest_upgrade_handler.py tests/unit/application/apps/classroom_planner/test_guest_upgrade_idempotency.py tests/unit/web/apps/classroom_planner/test_guest_upgrade_api.py -q`
- `pdm run fe-test -- --run src/views/apps/useClassroomPlannerGuestUpgrade.spec.ts src/views/apps/ClassroomPlannerEntryView.spec.ts`
- `pdm run fe-type-check`
- `pdm run docs-validate`
- Live authenticated proof on `http://127.0.0.1:5173` + `http://127.0.0.1:8000`
  using the real local `SA24D` / `G20` fixtures when available, otherwise one
  equivalent non-toy local fixture set

## Rollback plan

- Revert the template-reuse/remap hardening together if it unexpectedly changes
  the approved non-destructive import policy.
- Keep the rollback narrow: do not revert unrelated `PR-0232` guest export or
  public helper work that may land independently later.

## References

- Story owner:
  [ST-32-05](../stories/story-32-05-authenticated-upgrade-orchestration-and-idempotent-import-policy.md)
- Initial authenticated guest-upgrade foundation:
  [PR-0221](pr-0221-st-32-05-authenticated-upgrade-orchestration-and-idempotent-import-policy-foundation.md)
- Related guest continuity consumer now cross-linked after verified fix:
  [PR-0232](pr-0232-st-32-06-guest-local-draft-parity-direct-download-export-and-account-only-history-affordance-polish.md)
