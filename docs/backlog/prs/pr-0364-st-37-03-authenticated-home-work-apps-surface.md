---
type: pr
id: PR-0364
title: "ST-37-03 authenticated home work-apps surface"
status: done
owners: "agents"
created: 2026-06-18
updated: 2026-06-19
stories:
  - "ST-37-03"
tags:
  - frontend
  - ux
  - dashboard
dependencies:
  - "PR-0361"
  - "PR-0362"
  - "PR-0363"
  - "REV-PR-0363"
  - "MOCK-pr-0364-authenticated-home-work-apps-surface"
  - "REF-service-shell-ux-realignment-plan-v1"
  - "REF-current-product-lanes-and-sir-convert-boundary-v1"
  - "REF-app-presentation-decomposition-and-naming-plan-v1"
acceptance_criteria:
  - "Given a teacher signs in, when `/` renders, then the first actionable signed-in work surface after any alert/greeting is the approved `Arbetsappar` shelf rather than favorites, recent tools, latest-used apps, run history, catalog, contributor/admin cards, or vanity highlight copy."
  - "Given the approved C2 mockup is the product direction, when the app shelf renders, then it presents `Klassrumskartan`, `Provkonverteraren`, `Ljudtranskribering`, `Dokumentkonverteraren`, and `Kodredigerare` as equal first-class app entries with identifying image identities and whole-card click targets."
  - "Given `Kodredigerare` is an app surface, when the authenticated home renders, then it is not demoted into a secondary create/develop form, suggestion card, or nested card."
  - "Given `Mina körningar` and latest-used rows are no longer part of the active home direction, when the authenticated home renders, then it does not present `Mina körningar`, run-count summaries, latest-used apps, or recent-used vanity rows on the home surface."
  - "Given `PR-0363` added direct conversion-lane mode links, when the signed-in home presents Provkonverteraren and Ljudtranskribering, then those entries link to `/apps/documents.conversion_hub?mode=exam` and `/apps/documents.conversion_hub?mode=transcript` respectively."
  - "Given Dokumentkonverteraren is approved as a visible product lane but still lacks a proven current route, when implementation reaches that card, then it must use a truthful reviewed route or stop and create/attach the required route-visible slice; it must not point teachers to Provkonverteraren, Ljudtranskribering, the current compatibility host under a false label, or a generic catalog dead end."
  - "Given nested cards are forbidden, when the secondary file/catalog/contribution affordances render, then they use flat ledger rows or equivalent un-nested structures, not cards inside panels/cards."
---

# PR-0364: ST-37-03 Authenticated Home Work-Apps Surface

## Problem

The signed-in dashboard still leads with favorites, recent tools, run history,
catalog, contributor cards, editor entrypoints, suggestions, and admin cards.
That preserves the old generic dashboard framing instead of centering the
current teacher productivity apps.

The first stable transcript lane and `PR-0363` conversion-mode deep links now
make the service-shell direction concrete enough to replace that first
impression with an approved app-first authenticated home.

## Goal

Make authenticated `/` app-first by implementing the approved C2 work-app
surface:

- `Arbetsappar` is the first actionable signed-in surface.
- `Klassrumskartan`, `Provkonverteraren`, `Ljudtranskribering`,
  `Dokumentkonverteraren`, and `Kodredigerare` are presented as app shelves.
- `Mina filer`, catalog, suggestions, and owned-tool management remain
  secondary flat ledger affordances below the app shelf.
- `Mina körningar`, latest-used app rows, recent-used vanity rows, and run
  summary cards are removed from this home surface.

## Approved Design

The approved mockup is retained under
[MOCK-pr-0364-authenticated-home-work-apps-surface](../../mockups/pr-0364-authenticated-home-work-apps-surface/README.md).

Canonical preview:
[docs/mockups/pr-0364-authenticated-home-work-apps-surface/index.html](../../mockups/pr-0364-authenticated-home-work-apps-surface/index.html).

Rendered approval screenshot:
[approved-c2-authenticated-home.png](../../mockups/pr-0364-authenticated-home-work-apps-surface/approved-c2-authenticated-home.png).

The deleted card-grid and service-foyer attempts remain rejected and must not
guide runtime implementation.

## Scope

In scope:

- authenticated `/` composition in `HomeView.vue`;
- a dedicated home work-app section/component and lane model if that keeps
  files small;
- removal of home-surface `Mina körningar`, latest-used, and recent-used
  vanity chrome;
- `Kodredigerare` promoted into the primary app shelf;
- flat secondary ledgers for files/catalog/contribution affordances;
- tests proving app-first ordering, route targets, and forbidden home content.

Out of scope:

- public landing rewrite;
- backend/API, Sir Convert, HuleEdu Gateway, QTI, DOCX, or document-converter
  implementation work;
- fake Dokumentkonverteraren routing;
- full persistent sidebar/mobile drawer implementation unless this PR is
  explicitly widened to absorb `PR-0365`;
- final copy-only polish beyond labels needed to express the approved
  structure; `PR-0366` owns final copy alignment.

## Planning Baseline

- `PR-0361` created the service-shell sequence and identified
  `frontend/apps/skriptoteket/src/views/HomeView.vue` as the signed-in home
  surface that still leads with generic dashboard sections.
- `PR-0362` records the app-presentation baseline and remains the naming/
  decomposition authority.
- `PR-0363` is done and approved. The current compatibility routes are:
  - `Klassrumskartan`: `/apps/classroom.group-seating-studio`
  - `Provkonverteraren`: `/apps/documents.conversion_hub?mode=exam`
  - `Ljudtranskribering`: `/apps/documents.conversion_hub?mode=transcript`
  - `Kodredigerare`: `/editor`
- `Dokumentkonverteraren` is approved as a visible product lane in the C2 shell
  direction, but the current codebase still has no proven truthful route for
  it. Implementation must stop rather than fake this link if no reviewed route
  target is available.

## Closed Decisions

| Decision | Source | Result |
|----------|--------|--------|
| `PR-0364` may proceed to review/implementation planning. | User approval on 2026-06-19 and approved C2 mockup. | Prior design block is resolved. |
| Authenticated home becomes app-first. | `EPIC-37`, `ST-37-03`, approved C2 mockup. | App shelf appears before files/catalog/contribution surfaces. |
| `Kodredigerare` is an app. | User approval notes on 2026-06-19. | Place it in the primary app shelf, not in a nested create/develop panel. |
| `Mina körningar` is no longer part of the home direction. | User approval notes on 2026-06-19. | Remove run-history/run-count cards from the authenticated home surface. |
| Latest-used/recent-used vanity rows are removed. | User approval notes on 2026-06-19. | Do not show latest-used apps or recent-used rows on the home surface. |
| App cards are whole-card click targets. | Approved C2 mockup. | Do not add separate `Öppna` links inside app cards. |
| Nested card layouts are forbidden. | User approval notes on 2026-06-19 and UI doctrine. | Secondary affordances use flat ledgers or equivalent un-nested layouts. |
| Exam and transcript links use the query-mode compatibility route. | `PR-0363`. | Use exact `mode=exam` and `mode=transcript` route targets. |
| Protected browser proof must use Docker-backed HuleEdu Gateway lane. | `AGENTS.md`, repo testing refs, `PR-0363` runtime breadcrumb. | Use Docker `skriptoteket_web`; do not use host Uvicorn for proof. |

## Remaining Implementation Decision

| Decision | Options | Recommendation |
|----------|---------|----------------|
| Dokumentkonverteraren target | A: use a reviewed truthful route if it exists by implementation time. B: stop and create/attach a route-visible document-lane slice. C: point to the current `documents.conversion_hub` or catalog. | Choose A only if the route exists and is truthful; otherwise choose B. Reject C because it breaks the approved product direction. |
| Persistent navigation scope | A: implement only home content in `PR-0364`, keeping sidebar changes for `PR-0365`. B: widen `PR-0364` to include sidebar realignment. | Choose A unless the user explicitly merges the scopes. The C2 mockup remains the shared target for both slices. |

## Implementation Plan

1. Add a red authenticated-home test in
   `frontend/apps/skriptoteket/src/views/HomeView.spec.ts` proving that the
   signed-in home currently renders old dashboard content before the approved
   app shelf and still exposes `Mina körningar`/recent chrome.
2. Add a small lane model module, for example
   `frontend/apps/skriptoteket/src/components/home/homeWorkApps.ts`, with a
   Google-style domain-purpose module docstring and closed entries for:
   - `Klassrumskartan` -> `/apps/classroom.group-seating-studio`
   - `Provkonverteraren` -> `/apps/documents.conversion_hub?mode=exam`
   - `Ljudtranskribering` -> `/apps/documents.conversion_hub?mode=transcript`
   - `Kodredigerare` -> `/editor`
   - `Dokumentkonverteraren` -> only a truthful reviewed route; otherwise stop.
3. Add a focused `HomeWorkAppsSection.vue` component that renders equal-height
   app shelves with identifying graphics, whole-card links, no separate
   `Öppna` links, and no hard per-card shadow treatment.
4. Recompose the authenticated home so the first actionable surface is the app
   shelf, followed by flat secondary ledgers for `Mina filer`, `Katalog`,
   `Föreslå verktyg`, and `Mina verktyg` where role gates allow them.
5. Remove home-surface `Mina körningar`, run-count summaries, latest-used app
   rows, and recent-used vanity rows. This does not delete the underlying
   route/API in this PR.
6. Keep signed-out landing behavior unchanged.
7. Preserve contributor/admin role gates for suggestion, owned-tool, and admin
   surfaces that remain below or outside the home-first app shelf.
8. Record browser proof screenshots and exact commands in `.codex/handoff.md`.

## Implementation Notes

- Implemented the authenticated home runtime in:
  - `frontend/apps/skriptoteket/src/views/HomeView.vue`
  - `frontend/apps/skriptoteket/src/components/home/HomeWorkAppsSection.vue`
  - `frontend/apps/skriptoteket/src/components/home/homeWorkApps.ts`
- Decoupled the authenticated `/` loader path from retired dashboard fetches by
  parameterizing `frontend/apps/skriptoteket/src/composables/home/useHomeDashboard.ts`
  so the default home load only requests contributor/admin ledger data that is
  still visible.
- Added focused behavioral coverage in
  `frontend/apps/skriptoteket/src/views/HomeView.spec.ts` and loader-boundary
  coverage in
  `frontend/apps/skriptoteket/src/composables/home/useHomeDashboard.spec.ts`.
- Signed-out landing behavior remains unchanged.
- `Dokumentkonverteraren` is rendered as a visible non-linkable lane with the
  explicit runtime contract `data-app-linkable="false"` because the current
  codebase still has no reviewed truthful route target.
- Post-deploy visual correction replaced the CSS-drawn graph-paper app-card
  panels with bitmap app identities. `Klassrumskartan` reuses the existing
  `classroom-map-symbol.png`; `Provkonverteraren`, `Ljudtranskribering`,
  `Dokumentkonverteraren`, and `Kodredigerare` use generated companion PNGs
  under `frontend/apps/skriptoteket/src/assets/home/work-apps/`.
- The authenticated home no longer renders favorites, recent-used sections,
  `Mina körningar`, or the old `dashboard-card`/`action-cards-grid` surface.
- `Kodredigerare` now lives in the primary app shelf and links directly to
  `/editor`.

## Red-To-Green Test Plan

Expected first red proof:

```bash
pdm run fe-test -- --run src/composables/home/useHomeDashboard.spec.ts
```

The focused loader-boundary test should fail because the current authenticated
home still calls `/api/v1/my-runs`, `/api/v1/favorites`, and
`/api/v1/me/recent-tools` on the default `/` load path.

Expected green proof:

```bash
pdm run fe-test -- --run src/views/HomeView.spec.ts src/composables/home/useHomeDashboard.spec.ts
```

Required coverage:

- authenticated home renders `Arbetsappar` before files/catalog/contribution
  surfaces;
- `Klassrumskartan` links to `/apps/classroom.group-seating-studio`;
- Exam entry links to `/apps/documents.conversion_hub?mode=exam`;
- transcript entry links to `/apps/documents.conversion_hub?mode=transcript`;
- `Kodredigerare` appears as a primary app entry and links to `/editor`;
- `Mina körningar`, latest-used app rows, and recent-used vanity rows are
  absent from authenticated home;
- the app shelf does not expose separate `Öppna` links;
- secondary surfaces are flat ledgers, not cards nested inside cards/panels;
- the default authenticated-home loader path does not call retired runs,
  favorites, or recent-tool endpoints;
- contributor/admin ledger fetches only occur when those ledgers are visible;
- signed-out home behavior remains unchanged;
- contributor/admin affordances remain role-gated below or outside the app
  shelf.

Close-out commands:

```bash
pdm run fe-test -- --run src/views/HomeView.spec.ts src/composables/home/useHomeDashboard.spec.ts
pdm run fe-type-check
pdm run fe-lint
pdm run docs-validate
pdm run handoff-validate
git diff --check
```

Browser proof:

- Use the HuleEdu browser-session ceremony through the Docker-backed Gateway
  lane.
- Start/reuse Docker `skriptoteket_web` on `hule-network` as
  `skriptoteket-web`; do not start host Uvicorn for this proof.
- Capture authenticated `/` at desktop and compact widths.
- Verify the app shelf is the first actionable signed-in work surface and no
  old run/latest/recent vanity rows appear.
- Record command, URLs, viewport sizes, and artifact paths in
  `.codex/handoff.md`.

## Verification Notes

- Red proof captured with:
  `pdm run fe-test -- --run src/composables/home/useHomeDashboard.spec.ts`
  The new loader-boundary tests failed because the default authenticated-home
  load path still called `/api/v1/my-runs`, `/api/v1/favorites`, and
  `/api/v1/me/recent-tools` before contributor/admin-only ledger requests.
- Green frontend gates passed with:
  - `pdm run fe-test -- --run src/views/HomeView.spec.ts src/composables/home/useHomeDashboard.spec.ts`
  - `pdm run fe-type-check`
  - `pdm run fe-lint`
  - `pdm run docs-validate`
  - `pdm run handoff-validate`
  - `git diff --check`
- `HomeView.spec.ts` was trimmed back to behavioral assertions only:
  app order, truthful route targets, non-linkable Dokumentkonverteraren, retired
  text absence, role-gated ledgers, and signed-out behavior remain covered;
  removed class-name and helper-call assertions moved to the dedicated loader
  boundary spec.
- Live browser proof passed through the Docker-backed HuleEdu Gateway lane:
  - Gateway-to-Skriptoteket Docker health passed:
    `docker exec huleedu_api_gateway_service curl -sS -i --max-time 10 http://skriptoteket-web:8000/healthz`
  - Started the missing HuleEdu login UI lane with:
    `pdm run run-local-pdm auth-integration fe-dev`
  - A first preflight used the wrong HuleEdu export artifact
    `local-verify-export.json` and failed with
    `missing_identity_projection` / `identity_linking_required`; read-only
    diagnosis showed the running HuleEdu Identity service uses
    `huleedu-local-postgres`, whose proof subjects match
    `local-shared-verify-export.json`.
  - Correct preflight passed with:
    `pdm run auth-edge-bootstrap-preflight --export-json /Users/olofs_mba/Documents/Repos/huleedu/.artifacts/skriptoteket-auth-bootstrap/local-shared-verify-export.json --output-json .artifacts/skriptoteket-auth-bootstrap/preflight-pr-0364-local-shared.json`
  - Retained browser proof passed with:
    `pdm run python -m scripts.playwright_pr_0364_authenticated_home_work_apps --base-url http://localhost:5173`
  - Retained artifact:
    `.artifacts/playwright-pr-0364-authenticated-home-work-apps-surface/20260619T102703Z/manifest.redacted.json`
  - Proof captured authenticated `/` at `1512x900` desktop and `390x844`
    compact widths and asserted app order, truthful route targets,
    non-linkable Dokumentkonverteraren, home-surface retired text absence, and
    app shelf position above secondary ledgers.
- Post-deploy visual identity proof passed with:
  `pdm run python -m scripts.playwright_pr_0364_authenticated_home_work_apps --base-url http://localhost:5173 --artifact-root .artifacts/playwright-pr-0364-authenticated-home-work-apps-surface-visual-identity`
  after the corrected preflight:
  `pdm run auth-edge-bootstrap-preflight --export-json /Users/olofs_mba/Documents/Repos/huleedu/.artifacts/skriptoteket-auth-bootstrap/local-shared-verify-export.json --output-json .artifacts/skriptoteket-auth-bootstrap/preflight-pr-0364-visual-identity.json`.
  Retained artifact:
  `.artifacts/playwright-pr-0364-authenticated-home-work-apps-surface-visual-identity/20260619T135320Z/manifest.redacted.json`.
  The proof asserts Swedish app-card labels, five image identities, truthful
  route targets, and absence of the English app-card labels.

## Stop Conditions

- Stop if no truthful Dokumentkonverteraren route target exists and the
  implementation would need to fake it with Provkonverteraren,
  Ljudtranskribering, generic catalog, or the current compatibility host.
- Stop if the work expands into route/app-id split, curated-app registry
  changes, backend/API changes, Sir Convert, HuleEdu Gateway, QTI, DOCX, or
  document-converter implementation.
- Stop if the work expands into persistent sidebar/mobile navigation without
  explicitly absorbing or replacing `PR-0365`.
- Stop if browser proof cannot use the HuleEdu ceremony and Docker
  `skriptoteket_web` service.

## Review Gate

`REV-PR-0364` must review the approved C2 mockup contract and this amended PR
slice before runtime code implementation proceeds.
