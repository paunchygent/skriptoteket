---
type: pr
id: PR-0282
title: "ST-26-06 shared-link PDF download spinner contract"
status: done
owners: "agents"
created: 2026-05-03
updated: 2026-05-03
stories:
  - "ST-26-06"
  - "ST-29-11"
tags: ["frontend", "backend", "ux", "renderer", "klassrumskartan", "sharing", "pdf"]
dependencies:
  - "PR-0276"
  - "PR-0281"
acceptance_criteria:
  - "Given an active seating share link is opened, when the user activates `Ladda ner PDF`, then the download action has a stable processing affordance aligned with the `UiDenseSpinner` visual contract and does not shift the share-page header actions."
  - "Given an active grouping share link is opened, when the user activates `Ladda ner PDF`, then the same stable processing affordance is used without changing grouping share-page layout or PDF download semantics."
  - "Given product ownership approved scoped public-share JavaScript on 2026-05-03, when the user clicks `Ladda ner PDF`, then a narrowly targeted download controller sets persistent in-button busy state while preserving direct-download fallback when JavaScript is unavailable."
  - "Given the static share renderer cannot import Vue runtime components, when spinner markup, CSS, or the download controller is added to shared-link pages, then it reuses the `UiDenseSpinner` dimensions, motion, and accessible busy semantics without hydrating the page with Vue."
  - "Given the shared-link PDF action is busy, when the user attempts to activate `Ladda ner PDF` again, then the action presents the canonical disabled/busy visual state and suppresses duplicate activation until the PDF download has either handed off to the browser or the controller has recovered from failure."
  - "Given the public PDF route is requested, when the response is slow, successful, missing, revoked, or expired, then token authorization, slug behavior, cache/noindex policy, filenames, and export-backed PDF rendering remain unchanged."
  - "Given focused tests and visual proof run, when seating and grouping share pages are inspected at desktop and mobile widths, then the `Ladda ner PDF` action keeps reserved geometry in idle and busy states, contains no unexpected status pill or pop-in sibling, clears busy state on page lifecycle or focus recovery, and keeps public-share action chrome out of generated PDFs."
---

## Problem

`PR-0281` fixed the authenticated planner toolbar by moving export/share/revoke
processing feedback into existing dense controls with `UiDenseSpinner`. The
remaining visible mismatch is the public shared-link `Ladda ner PDF` action for
seating and grouping pages: it is still plain share-page chrome and does not
share the same processing affordance language.

This action is not part of the Vue toolbar. It is rendered as static public
share HTML by the backend share renderer, with the PDF path finalized through
share artifact chrome slots. Treating it as another Vue component adoption
would reopen the accepted static exported-artifact contract from `PR-0276`.

## Goal

Align the shared-link seating and grouping `Ladda ner PDF` action with the
`UiDenseSpinner` busy-feedback language while preserving public-share service
contracts:

- no header/action layout shift while the PDF action is busy
- no new status pill or pop-in sibling beside the action
- no repeat activation while the action is already busy
- no change to share-token, slug, revoke, expiry, cache, filename, or PDF
  renderer semantics
- no Vue hydration, API call, token logging, or broad public-share script

## Non-goals

- No redesign of the share-page body, seating map, grouping cards, or PDF body.
- No changes to the export-backed shared-link PDF renderer.
- No change to authenticated workspace `Exportera PDF` behavior.
- No share-token, owner, guest-helper, revoke, expiry, or slug contract changes.
- No import of Vue dense-control components into static share artifacts.
- No broad public-share JavaScript, route-coupled script, API polling, download
  interception service, or token-bearing telemetry.

## Service-Aligned Assessment

Product ownership approved a tiny public-share download controller on
2026-05-03 so `Ladda ner PDF` can show a real persistent in-button busy state
after click. This amends the earlier static/no-script default only for this
bounded action affordance.

The controller remains renderer-owned public share chrome, not Vue hydration and
not an application API workflow. It must be scoped to the download action, avoid
logging token-bearing hrefs, avoid polling or fetching the PDF route itself, and
preserve normal anchor behavior when JavaScript is unavailable or fails to load.

## Decision Checkpoints

1. **Approved path: add a tiny public-share download controller for persistent
   busy state.**
   The controller must be scoped to the `Ladda ner PDF` action, avoid API calls,
   avoid logging token-bearing hrefs, clear busy state on page lifecycle/focus
   recovery, and preserve direct-download fallback when JavaScript is
   unavailable.

2. **Still forbidden: hydrate the public share page with Vue or introduce a
   broader app script.**
   The static share artifact can include this bounded controller, but it must
   not become an SPA surface, fetch authenticated APIs, or change share-token,
   PDF-renderer, cache, slug, revoke, or expiry semantics.

## Implementation Plan

1. Inspect the static share chrome in
   `src/skriptoteket/infrastructure/curated_apps/apps/classroom_planner/share_renderer.py`
   and the owned PDF href slot finalization in
   `src/skriptoteket/application/curated_apps/classroom_planner/shares.py`.
2. Compare `UiDenseSpinner` sizing, animation, reduced-motion handling, and
   accessible busy semantics in
   `frontend/apps/skriptoteket/src/components/ui/UiDenseSpinner.vue`.
3. Add renderer-owned markup/CSS that reserves the spinner slot inside
   `.share-download-pdf` and mirrors the dense spinner geometry without
   importing Vue.
4. Add the smallest possible public-share download controller, targeted by a
   renderer-owned data attribute on the PDF action. The controller should set
   in-button busy state on click, preserve the anchor download, avoid token
   logging/API calls, and clear busy state on page lifecycle or focus recovery.
5. Add canonical disabled/busy styling and controller behavior so a busy
   `Ladda ner PDF` action communicates that it cannot be clicked again and
   suppresses duplicate activation until browser handoff, lifecycle/focus
   recovery, or timeout/failure recovery clears the state.
6. Apply the same action contract to both seating and grouping shared-link
   pages through the shared renderer path.
7. Extend renderer and route tests so share HTML includes only the approved
   bounded controller, both page types expose the stable action chrome, the
   no-JavaScript direct-download fallback remains intact, duplicate busy clicks
   are suppressed, and PDFs still omit web-only actions.
8. Capture desktop and mobile visual proof for active seating and grouping
   share pages, including idle, busy, and duplicate-click states.
9. Update this task, `ST-26-06`, and `.codex/handoff.md` with exact proof
   commands and artifact paths before closeout.

## Test Plan

- `pdm run pytest -q tests/unit/infrastructure/curated_apps/apps/classroom_planner/test_share_renderer.py tests/unit/web/apps/classroom_planner/test_share_pages.py`
- `pdm run pytest -q tests/unit/infrastructure/curated_apps/apps/classroom_planner/test_share_pdf_renderer.py`
- `pdm run typecheck`
- `pdm run lint`
- `pdm run docs-validate`
- `git diff --check`
- Browser/visual proof for active seating and grouping share pages at desktop
  and mobile widths, including a click proof that the in-button spinner appears,
  geometry stays stable, duplicate activation is suppressed during busy state,
  canonical disabled/busy styling is visible, and direct-download behavior still
  works.

## Rollback Plan

Revert the renderer-owned spinner/action chrome changes and any optional
public-share controller as one unit. The share PDF route and export-backed PDF
renderers should remain untouched, so rollback must restore only the public
share action presentation.

## Add-On Task: Canonical Disabled Busy State

Status: done as of 2026-05-03.

The first implementation made the spinner persistent and geometry-stable, but
the busy button still needs to adopt the canonical disabled/busy action state so
users can see that `Ladda ner PDF` cannot be clicked again while the PDF is
being generated or while the browser download handoff is in progress.

Implementation requirements:

- Add a disabled/busy visual treatment to `.share-download-pdf` that matches
  the dense-control disabled/busy language without adding a status pill or new
  action sibling.
- While `data-skriptoteket-share-pdf-download-state="busy"` is set, suppress
  duplicate activations from mouse, touch, keyboard, or nested target clicks.
- Preserve progressive enhancement: if JavaScript is unavailable, the anchor
  must still download normally.
- Do not add polling, fetch calls, route changes, token logging, or PDF job
  state APIs. Recovery remains bounded to browser handoff/lifecycle/focus
  recovery and timeout/failure fallback.
- Update browser proof so a second activation attempt during busy state does
  not trigger another download and the disabled/busy styling is visible without
  geometry shift.

## Implementation Evidence

- Added reserved spinner markup to the shared-link `Ladda ner PDF` anchor in
  `share_renderer.py`, including the `UiDenseSpinner`-aligned 12px loader
  geometry, in-button busy state, `aria-busy`, and a stable reserved slot so the
  action width does not change when processing starts.
- Added one bounded renderer-owned inline controller marked with
  `data-skriptoteket-share-pdf-download-controller="owned"`. It listens only
  for owned PDF-download anchor clicks, preserves normal anchor/download
  behavior, avoids API calls/fetching/token logging, and clears busy state on
  `pageshow`, window focus, visibility recovery, or timeout fallback.
- Kept public share route, token, slug, cache/noindex, filename, revocation,
  expiry, and export-backed PDF renderer semantics unchanged.
- Updated renderer tests so hostile user text still cannot create script tags
  while the single approved controller script, spinner CSS, no-fetch boundary,
  and both grouping/seating action chrome are covered.
- Focused backend tests passed:
  `pdm run pytest -q tests/unit/infrastructure/curated_apps/apps/classroom_planner/test_share_renderer.py tests/unit/web/apps/classroom_planner/test_share_pages.py tests/unit/infrastructure/curated_apps/apps/classroom_planner/test_share_pdf_renderer.py`.
- Browser proof passed:
  `pr-0282-browser-proof: ok artifacts=.artifacts/pr-0282-share-pdf-spinner-proof`.
  The proof generated grouping/seating share pages at desktop and mobile widths,
  clicked `Ladda ner PDF`, observed a real browser download event, verified the
  spinner became visible with `aria-busy="true"` and `aria-label="Förbereder
  PDF"`, and proved action x-position and width stayed unchanged.
- Closeout gates passed: `pdm run lint`, `pdm run typecheck`,
  `pdm run docs-validate`, `pdm run handoff-validate`, and `git diff --check`.
- Add-on pending: canonical disabled/busy state and duplicate-activation
  suppression are implemented in `share_download_action_renderer.py`. The busy
  state now sets `aria-disabled="true"`, uses the canonical disabled/busy visual
  treatment, temporarily removes `href` after browser handoff so duplicate
  mouse/keyboard activations cannot trigger a second download, and restores the
  direct-download link on lifecycle/focus/timeout recovery.
- SRP follow-up complete: the shared PDF download action CSS, markup, and
  scoped controller moved out of `share_renderer.py` into
  `share_download_action_renderer.py`, leaving `share_renderer.py` focused on
  document/header composition and grouping/seating body assembly.
- Refreshed browser proof passed:
  `pr-0282-browser-proof: ok artifacts=.artifacts/pr-0282-share-pdf-spinner-proof`.
  The proof now verifies grouping/seating at desktop and mobile widths, one
  real browser download after first click, `aria-disabled="true"`, `href` absent
  while busy, visible spinner, progress cursor, unchanged geometry, and exactly
  one download event after duplicate mouse and keyboard activation attempts.
- Live devstack route proof passed:
  `pr-0282-live-route-proof: ok manifest=.artifacts/pr-0282-live-route-proof/manifest.json`.
  The proof inserted a temporary share artifact into the running dev database,
  served it through `http://127.0.0.1:5173/share/classroom/...`, clicked the
  real public `Ladda ner PDF` action, observed the backend-generated PDF
  download, verified busy state (`aria-busy`, `aria-disabled`, no `href`,
  visible spinner, progress cursor), proved unchanged action geometry, and
  confirmed one download event after a duplicate activation attempt. The
  temporary share row was removed after the proof.
