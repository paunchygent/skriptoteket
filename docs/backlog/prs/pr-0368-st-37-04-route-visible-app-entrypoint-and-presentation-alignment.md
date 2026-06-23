---
type: pr
id: PR-0368
title: "ST-37-04 route-visible app entrypoint and presentation alignment"
status: done
owners: "agents"
created: 2026-06-18
updated: 2026-06-22
stories:
  - "ST-37-04"
tags:
  - frontend
  - routing
  - curated-apps
dependencies:
  - "PR-0362"
  - "PR-0363"
  - "PR-0364"
  - "PR-0365"
  - "PR-0366"
  - "PR-0367"
  - "REF-app-presentation-decomposition-and-naming-plan-v1"
acceptance_criteria:
  - "Given the compatibility deep-link bridge and app-first shell are in place, when route-visible app presentation is revisited, then Exam Converter and Audio Transcription are presented as separate teacher-facing app identities rather than organized as tabs in one compatibility host."
  - "Given the authenticated Sir Convert edge is fragile and security-sensitive, when presentation work begins and closes, then the implementation reuses the shared authenticated runtime shell and retains HuleEdu Gateway browser-session, CSRF, signed identity, route-grant, server-side Sir key injection, replay, artifact, and formatter assumptions under live shared-auth Docker/Playwright proof."
  - "Given Document Converter still lacks a real host, when this slice runs, then no Document Converter route, alias, host, or runtime link is created."
  - "Given route-visible app entrypoints are changed, when the slice closes, then focused router or host-view tests plus live shared-auth browser proof cover every changed protected route surface while the public Exam Converter route remains unchanged."
---

# PR-0368: ST-37-04 Route-Visible App Entrypoint And Presentation Alignment

## Problem

After the compatibility deep-link bridge and shell realignment ship, the repo
still presents Exam Converter and Audio Transcription inside the same
`documents.conversion_hub` compatibility host. That tabbed presentation is no
longer a truthful product structure because the lanes will grow into dissimilar
full app workflows.

The split is also sensitive because the existing Sir Convert flows depend on a
carefully proven HuleEdu Gateway auth edge. Prior regressions around malformed
signed behavior, replay, and artifact access showed that small changes can cause
expensive debugging unless live Docker-service Playwright proof is retained
throughout implementation.

## Goal

Present Exam Converter and Audio Transcription as separate teacher-facing app
identities while reusing the shared authenticated runtime shell, preserving the
authenticated Sir Convert edge, and avoiding a false Document Converter lane.

## Non-goals

- No backend/API decomposition unless the route-visible work proves it is
  necessary.
- No Sir Convert, HuleEdu, QTI, or DOCX contract change.
- No public Exam Converter route, public capability, or public route-contract
  change.
- No auth-edge rewrite, browser-authored identity headers, browser API keys,
  credential POST shortcuts, direct cookie proof, host-only backend shortcut, or
  browser-direct Sir Convert calls.
- No duplicated per-app auth-edge handling or unnecessary backend/runtime shell
  duplication.
- No long-term legacy compatibility commitment; any retained compatibility route
  is cutover-only and must be removed by the follow-up cleanup slice.
- No fake Document Converter implementation, route, alias, host, or runtime
  link.

## Review gate

`REV-PR-0368` must be approved before code implementation begins.

## Implementation plan

1. Start by creating the retained auth-edge inventory and proof-plan artifact
   at
   `docs/reference/ref-pr-0368-auth-edge-inventory-and-proof-plan.md` before
   editing presentation routes or hosts. The artifact must list:
   - HuleEdu browser-session and CSRF ceremony.
   - Gateway `/sir-convert` proxy behavior.
   - Server-side Sir Convert key injection.
   - Signed `InternalIdentityContextV1`, route grants, and prefix stripping.
   - Skriptoteket runtime clients/composables for exam conversion, correction
     replay, transcript submission, formatter replay, polling, and artifact
     download.
   - Existing Playwright auth helpers and shared-auth trust-lane preflight
     scripts.
   - The exact red/green Playwright proof script or script update planned for
     the route-visible app identity split.
2. Add focused red router, host-view, or navigation tests proving the current
   tabbed `documents.conversion_hub` presentation is not the accepted durable
   app structure for Exam Converter and Audio Transcription.
3. Add separate route-visible app identities for Exam Converter and Audio
   Transcription. Shared runtime clients/composables, shared authenticated
   shell infrastructure, and shared backend logic are preferred below the
   presentation boundary; shared teacher-facing tabs are not.
4. Remove `ConversionHubModeTabs` from normal authenticated app flow. Only
   temporary cutover handling or tests may reference it until `PR-0374` removes
   compatibility remnants.
5. Preserve the current public Exam Converter route and public capability
   without changes.
6. Keep Document Converter visually and route-wise inert; it must not gain a
   route, alias, host, runtime link, or proof target in this slice.
7. Record the cutover-only compatibility route removal in
   `PR-0374`; do not treat compatibility as a long-term supported product
   surface.
8. Stop and return to planning if route-visible truth cannot be achieved
   without new backend/API contract work; that handoff belongs to `PR-0369`.

## Test plan

- Red first:
  `pdm run fe-test -- --run src/router/routes.spec.ts src/views/apps/ExamConverterAuthenticatedView.modeRoute.spec.ts src/views/apps/ConversionHubTranscriptMode.spec.ts src/App.spec.ts`
- Green:
  `pdm run fe-test -- --run src/router/routes.spec.ts src/views/apps/ExamConverterAuthenticatedView.modeRoute.spec.ts src/views/apps/ConversionHubTranscriptMode.spec.ts src/App.spec.ts`
- Add focused host-view, home, or navigation tests for every changed entry
  surface, including separate Exam Converter and Audio Transcription app
  identities.
- `pdm run fe-type-check`
- Live browser proof through the HuleEdu browser-session ceremony and
  shared-auth Docker service lane for each changed authenticated route. Extend
  or replace
  `scripts/playwright_pr_0363_conversion_mode_deeplink.py` as needed, and reuse
  `scripts/_playwright_auth.py` plus
  `scripts/_sir_convert_trust_lane_preflight.py`.
- Protected proof must not use direct cookie injection, credential POST
  shortcuts, host-only backend shortcuts, browser-authored identity headers, or
  browser-direct Sir Convert calls.
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Rollback plan

Remove the new route-visible presentation changes and keep the temporary
compatibility route plus shell copy sequence until `PR-0374` can safely remove
the compatibility path after cutover.

## Implementation evidence

Implemented on 2026-06-22 after `REV-PR-0368` approval.

- First artifact:
  `docs/reference/ref-pr-0368-auth-edge-inventory-and-proof-plan.md`
  inventories HuleEdu browser-session/CSRF, Gateway `/sir-convert`,
  server-side Sir Convert key injection, signed identity context, route grants,
  prefix stripping, shared runtime clients, and the retained Playwright proof
  lane before route/host edits.
- Added canonical protected route-visible identities:
  `/apps/exam-converter` and `/apps/audio-transcription`.
- Kept both identities on
  `frontend/apps/skriptoteket/src/views/apps/ExamConverterAuthenticatedView.vue`
  so the existing shared authenticated runtime host, Sir Convert Gateway
  client, transcript persistence/export clients, correction replay, polling,
  and artifact behavior are reused.
- Removed `ConversionHubModeTabs` from normal authenticated flow. Legacy
  `/apps/documents.conversion_hub?mode=exam|transcript` remains cutover-only
  compatibility for `PR-0374`.
- Updated authenticated home links to the canonical protected identity routes.
  Document Converter remains unlinked and inert.
- Updated `scripts/playwright_pr_0363_conversion_mode_deeplink.py` to prove
  the canonical PR-0368 identities while continuing to use
  `scripts/_playwright_auth.py` and retained artifacts.
- Hardened `pdm run fe-dev-shared-auth` so the documented local proof command
  uses PDM script env mapping for the local HuleEdu Gateway auth/proxy values
  instead of shell-prefix defaults that could be blanked before Vite served
  client env.

Verification:

- Red first:
  `pdm run fe-test -- --run src/router/routes.spec.ts src/views/apps/ExamConverterAuthenticatedView.modeRoute.spec.ts src/views/apps/ConversionHubTranscriptMode.spec.ts src/App.spec.ts`
  failed with expected missing canonical route and tab-presentation failures
  before production edits.
- Green:
  `pdm run fe-test -- --run src/router/routes.spec.ts src/views/apps/ExamConverterAuthenticatedView.modeRoute.spec.ts src/views/apps/ConversionHubTranscriptMode.spec.ts src/App.spec.ts`
  passed with 27 tests.
- Home link check:
  `pdm run fe-test -- --run src/views/HomeView.spec.ts` passed with 5 tests.
- Adjacent changed frontend specs:
  `pdm run fe-test -- --run src/views/apps/ExamConverterAuthenticatedView.spec.ts src/views/apps/conversionHubModeRoute.spec.ts src/views/HomeView.spec.ts src/router/routes.spec.ts src/views/apps/ConversionHubTranscriptMode.spec.ts src/App.spec.ts`
  passed with 51 tests.
- `pdm run fe-type-check` passed.
- `pdm run fe-lint` passed.
- `pdm run lint` passed after formatter adjustment.
- `pdm run test tests/unit/scripts/test_playwright_script_surface.py`
  passed with 3 tests.
- HuleEdu auth-integration check:
  `pdm run run-local-pdm auth-integration check` passed from the HuleEdu repo
  with Gateway session checks, HuleEdu login UI checks, and Gateway
  Skriptoteket proxy env alignment.
- Local shared-auth Vite wrapper check:
  `pdm run fe-dev-shared-auth` served `VITE_HULEEDU_AUTH_BASE_URL`,
  `VITE_HULEEDU_AUTH_ENTRY_URL`, protected `/api`, and `/sir-convert` proxy
  values on `http://localhost:5173` pointing at the local HuleEdu Gateway.
- Live PR-0368 browser proof:
  `pdm run python -m scripts.playwright_pr_0363_conversion_mode_deeplink --base-url http://localhost:5173`
  passed through the HuleEdu browser-session ceremony with retained artifact
  `.artifacts/playwright-pr-0368-presentation-identity-split/20260622T215450Z/`.
  The redacted manifest records `/apps/exam-converter` and
  `/apps/audio-transcription` captures with empty query strings.
