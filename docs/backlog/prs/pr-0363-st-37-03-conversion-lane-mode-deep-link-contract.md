---
type: pr
id: PR-0363
title: "ST-37-03 conversion lane mode deep-link contract"
status: done
owners: "agents"
created: 2026-06-18
updated: 2026-06-19
stories:
  - "ST-37-03"
tags:
  - frontend
  - ux
  - conversion
dependencies:
  - "PR-0361"
  - "PR-0362"
  - "REF-service-shell-ux-realignment-plan-v1"
  - "REF-current-product-lanes-and-sir-convert-boundary-v1"
  - "REF-app-presentation-decomposition-and-naming-plan-v1"
acceptance_criteria:
  - "Given the authenticated shell needs direct lane entrypoints before app-id decomposition, when `/apps/documents.conversion_hub?mode=exam` or `?mode=transcript` opens, then the current Conversion Hub host selects the matching bespoke mode without renaming the app id or route."
  - "Given a teacher switches between `Prov` and `Transkript`, when the tab changes, then URL query state stays synchronized without losing the current authenticated route context."
  - "Given invalid or absent mode query state, when the route loads, then Exam Converter remains the default and no public route, registry, Sir Convert, HuleEdu, QTI, or DOCX contract changes are made."
---

# PR-0363: ST-37-03 Conversion Lane Mode Deep-Link Contract

## Problem

The service shell needs direct entrypoints for Exam Converter and Audio
Transcription, but both currently live behind `documents.conversion_hub`.
`ExamConverterAuthenticatedView.vue` keeps the selected mode in a local ref, so
links cannot open transcript mode directly.

## Goal

Add a small route-query mode contract for the existing authenticated host.

## Non-goals

- No app-id split, route rename, registry rename, or public route change.
- No Document Converter implementation.
- No Sir Convert, HuleEdu Gateway, QTI, DOCX, or backend API contract change.

## Planning baseline

- `documents.conversion_hub` remains the technical compatibility app id until
  `ST-37-04` closes the app-presentation decomposition and naming package.
- `frontend/apps/skriptoteket/src/views/apps/ExamConverterAuthenticatedView.vue`
  currently owns `activeHubMode` as a local `ref`, so the authenticated route
  cannot open transcript mode directly.
- `frontend/apps/skriptoteket/src/router/routes.ts` already resolves
  `/apps/documents.conversion_hub` through the generic protected
  `/apps/:appId` route. Query state does not require a route-table change.
- Dev/test UI-inspection routes are already lane-specific:
  `/apps/documents.conversion_hub/exam-converter/ui-fixtures/:fixtureId` and
  `/apps/documents.conversion_hub/transcript/ui-fixtures/:fixtureId`.
- Vue Router guidance supports reading specific `route.query` keys through
  `useRoute()` and updating query state with `useRouter().replace(...)` while
  preserving unrelated query keys. Do not watch the whole route object for this
  small contract.

## Assumptions

- Shell links can point to
  `/apps/documents.conversion_hub?mode=exam` and
  `/apps/documents.conversion_hub?mode=transcript` before app-id decomposition.
- `mode` is an authenticated-host concern only. Public Exam Converter routes,
  curated-app registry metadata, Sir Convert calls, HuleEdu Gateway contracts,
  QTI/DOCX behavior, and backend APIs are unchanged.
- Absence of `mode` is legacy-compatible and means Exam Converter.
- Invalid, empty, repeated, or array-valued `mode` query values are not accepted
  as transcript intent. They render Exam Converter and do not rewrite the URL.
- Selecting a tab writes an explicit `mode=<selected>` query value and preserves
  any unrelated query keys already present on the current route.
- Exam Converter UI-inspection fixture routes remain exam-only even if a caller
  appends `?mode=transcript`, because transcript has its own inspection route.

## Options And Recommendations

| Decision | Options | Recommendation |
|----------|---------|----------------|
| Entry contract | A: query `?mode=exam\|transcript`. B: route segments such as `/apps/documents.conversion_hub/transcript`. C: split app ids now. | Choose A. It gives truthful direct shell links without pre-empting `ST-37-04` route/app-id decisions. |
| Query key | A: `mode`. B: `lane`. C: `app`. | Choose A because the PR title, acceptance criteria, and current component state already use mode semantics. |
| Accepted values | A: closed enum `exam`, `transcript`. B: accept aliases such as `audio`, `stt`, `prov`. | Choose A. Alias handling belongs to future app-presentation routing, not this compatibility bridge. |
| Invalid or absent query behavior | A: render Exam Converter without URL canonicalization. B: replace invalid query with `mode=exam`. C: show an error. | Choose A. It preserves legacy links and avoids route rewrites on mount. |
| Tab navigation history | A: `router.replace`. B: `router.push`. | Choose A. Mode tabs are in-place view state; external shell links still create normal navigation entries. |
| Query preservation | A: preserve unrelated query keys. B: replace the whole query object. | Choose A so future continuation/debug keys are not lost by the mode toggle. |
| Implementation location | A: inline parser and query builder in the 443-line SFC. B: extract a tiny route-mode helper module and keep the SFC focused. C: introduce a store. | Choose B. It keeps the large host frame below the module-size pressure line and gives the parser red/green tests without heavy component mounting. |
| Fixture behavior | A: ignore `mode` when `inspectionFixtureId` is set. B: let query override the fixture lane. | Choose A. The exam fixture route should keep rendering exam inspection state; transcript inspection is already a separate route. |
| Browser proof lane | A: sanctioned HuleEdu browser-session proof. B: direct product-backend login or cookie shortcut. | Choose A. Protected route-visible proof must use the HuleEdu ceremony and repo helpers. |

## Remaining gates

- `PR-0362` is closed, so the prior dependency block is resolved.
- `REV-PR-0363` approved this implementation on 2026-06-19.
- Stop and return to planning if implementation requires app-id, registry,
  public-route, Sir Convert, HuleEdu Gateway, QTI, DOCX, or backend API changes.

## Review gate

`REV-PR-0363` approved the implementation on 2026-06-19.

## Implementation plan

1. Add a focused red helper/component test proving
   `/apps/documents.conversion_hub?mode=transcript` currently renders the Exam
   Converter branch.
2. Extract a small frontend helper module for the conversion-hub mode contract:
   closed mode type, default mode, route-query parser, query builder that
   preserves unrelated keys, and the required domain-purpose module docstring.
3. Import the shared mode type into `ConversionHubModeTabs.vue` so mode values
   have one source of truth outside the SFC.
4. In `ExamConverterAuthenticatedView.vue`, read `route.query.mode` via
   `useRoute()` and derive the active host branch from the helper parser.
5. Replace the direct `activeHubMode = $event` template assignment with a
   handler that calls `router.replace({ query: nextQuery })` for tab changes.
6. Guard exam UI-inspection fixtures so `inspectionFixtureId` forces exam mode
   and skips mode-query writes.
7. Leave `routes.ts`, `curatedAppHostRegistry.ts`, public routes, and backend
   contracts unchanged unless a test exposes a current regression unrelated to
   this PR; in that case stop and re-plan scope.

## Test plan

- Red first:
  `pdm run fe-test -- --run src/views/apps/ExamConverterAuthenticatedView.spec.ts`
- If a helper module is extracted, include its focused spec in the same red and
  green command.
- Component/helper coverage:
  - `mode=exam` renders Exam Converter.
  - `mode=transcript` renders the transcript host.
  - absent, invalid, empty, repeated, or array-valued mode renders Exam
    Converter without canonicalizing the URL.
  - clicking `Prov` and `Transkript` calls `router.replace` with the selected
    `mode` while preserving unrelated query keys.
  - exam UI-inspection fixtures ignore `mode=transcript`.
- Route coverage:
  - use `src/router/routes.spec.ts` only if implementation touches route
    definitions. The expected implementation should not need route-table
    changes.
- Green focused command:
  `pdm run fe-test -- --run src/views/apps/ExamConverterAuthenticatedView.spec.ts`
- `pdm run fe-type-check`
- Authenticated browser proof through the HuleEdu browser-session ceremony:
  - start or reuse the sanctioned HuleEdu auth-integration lane;
  - run Skriptoteket shared-auth preflight/proof helpers when the local lane
    has not already been proven current;
  - navigate to `/apps/documents.conversion_hub?mode=exam` and verify the
    `Prov` tab and Exam Converter workspace are active;
  - navigate to `/apps/documents.conversion_hub?mode=transcript` and verify the
    `Transkript` tab and transcript workspace are active;
  - record exact commands, URLs, viewport, and artifact paths in
    `.codex/handoff.md`.
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Implementation Evidence

Implementation evidence was added on 2026-06-19 after the proof lane was
corrected to use the Docker Skriptoteket backend service instead of host
Uvicorn.

- Correct runtime: HuleEdu Gateway plus Skriptoteket Docker `web` service
  (`skriptoteket_web`, Docker alias `skriptoteket-web`) and host Vite.
- Root cause for the failed earlier proof attempt: HuleEdu Gateway resolves
  `API_GATEWAY_SKRIPTOTEKET_BACKEND_URL` as
  `http://skriptoteket-web:8000` on `hule-network`, so host Uvicorn on
  `127.0.0.1:8000` cannot satisfy Gateway app continuation for protected
  browser proof.
- Gateway-to-backend check passed:
  `docker exec huleedu_api_gateway_service curl -sS -i --max-time 10 http://skriptoteket-web:8000/healthz`.
- Authenticated browser proof passed:
  `pdm run python -m scripts.playwright_pr_0363_conversion_mode_deeplink`.
- Retained proof artifact:
  `.artifacts/playwright-pr-0363-conversion-mode-deeplink/20260618T225544Z/manifest.redacted.json`.
- The retained proof covers
  `/apps/documents.conversion_hub?mode=exam` and
  `/apps/documents.conversion_hub?mode=transcript` at viewport `1512x900`.
- The Docker-service breadcrumb was added to:
  `.codex/skills/skriptoteket-testing/references/browser-automation.md`,
  `.codex/skills/skriptoteket-testing/references/backend-pytest.md`,
  `docs/runbooks/runbook-testing.md`, and the shared
  `local-devops/references/skriptoteket.md`.

Validation passed on 2026-06-19:

- `pdm run fe-test -- --run src/views/apps/ExamConverterAuthenticatedView.spec.ts src/views/apps/ExamConverterAuthenticatedView.modeRoute.spec.ts src/views/apps/conversionHubModeRoute.spec.ts src/views/apps/ExamConverterAuthenticatedUiInspectionFixtures.spec.ts`
  passed with 4 files / 44 tests.
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run fe-build` passed with existing dynamic/static import and large-chunk
  warnings.
- `pdm run test tests/unit/scripts/test_playwright_script_surface.py` passed
  with 3 tests.
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `pdm run skills-validate`
- `git diff --check`
- Shared skill repository `pdm run skills-validate` and
  `pdm run docs-validate` passed for the `local-devops` breadcrumb update.
- Shared skill repository `git diff --check`

## Implementation Summary

Closed on 2026-06-19. The authenticated compatibility host now accepts a
closed `mode=exam|transcript` query contract on
`/apps/documents.conversion_hub`, defaults absent/invalid query state to the
Exam Converter lane without URL canonicalization, preserves unrelated query
keys when tabs change, and keeps exam UI-inspection fixtures exam-only.

The slice deliberately did not rename app ids, change route records, edit
curated-app registry metadata, alter public routes, or touch backend, Sir
Convert, HuleEdu Gateway, QTI, or DOCX contracts. The live proof and routed
testing docs now also encode the operational breadcrumb that protected
Gateway/browser-session proof uses Docker `skriptoteket_web` on `hule-network`
with alias `skriptoteket-web`, not host Uvicorn.

## Rollback plan

Remove the query-mode synchronization and return the host to local `exam`
default mode.
