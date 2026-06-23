---
type: agent_session_long_term_memory_entry
id: session-2026-06-23-st-37-04-handoff-compaction
status: active
created: 2026-06-23
---

# Session 2026-06-23 ST-37-04 Handoff Compaction

## Scope

This entry retains ST-37-04 app presentation, public landing, dev-stack, and
route-proof history compacted out of `.codex/handoff.md` while PR-0376 and
PR-0377 became the active operator-proof focus.

## Retained State

- `PR-0366` aligned app-lane labels/descriptions in
  `frontend/apps/skriptoteket/src/components/home/homeWorkApps.ts`,
  `frontend/apps/skriptoteket/src/views/apps/ExamConverterAuthenticatedView.vue`,
  and `frontend/apps/skriptoteket/src/views/apps/ExamConverterPublicView.vue`
  without changing routes, app ids, registry metadata, or backend/API contracts.
- `PR-0367` presents `documents.conversion_hub` as
  `Provhantering och ljudtranskribering` while retaining only the active
  `exam_converter` public capability.
- `PR-0370` approved the public landing image direction and final copy under
  `docs/mockups/pr-0370-public-landing-authenticated-app-preview/`.
- `PR-0371` removed `LandingFeaturedClassroom` from public home and implemented
  the approved `När du loggar in` three-panel preview with the authenticated
  app symbols. Review fixes made the preview images eager, synchronous, and
  high-priority after the first retained mobile proof left lower symbols blank.
- `PR-0372` kept the signed-out header to brand + `Logga in` + `Hjälp`, removed
  the duplicate public `Klassrumskartan` link, and kept the small-screen header
  on one row.
- `PR-0373` defined and guarded the host Vite shared-auth proof lane:
  `pdm run dev-stack web-start` starts Docker `db`/`web` plus migrations
  without taking port `5173`, and `pdm run fe-dev-shared-auth` keeps protected
  `/api` on HuleEdu Gateway while public `/api/v1/public` stays on local
  Skriptoteket web.

## Retained Verification

- `PR-0368` red-first:
  `pdm run fe-test -- --run src/router/routes.spec.ts src/views/apps/ExamConverterAuthenticatedView.modeRoute.spec.ts src/views/apps/ConversionHubTranscriptMode.spec.ts src/App.spec.ts`
  failed with expected missing canonical routes and tab-presentation failures.
- `PR-0368` focused green:
  the same command passed with 27 tests;
  `pdm run fe-test -- --run src/views/HomeView.spec.ts` passed with 5 tests;
  `pdm run fe-type-check` passed.
- `PR-0368` live proof passed through HuleEdu auth integration using
  `pdm run python -m scripts.authenticated_app_identity_split --base-url http://localhost:5173`
  with retained artifact
  `.artifacts/playwright-pr-0368-presentation-identity-split/20260622T215450Z/`.
- `PR-0374` red-first:
  `pdm run fe-test -- --run src/router/routes.spec.ts src/App.spec.ts src/views/apps/ExamConverterAuthenticatedView.modeRoute.spec.ts src/views/apps/conversionHubModeRoute.spec.ts src/views/HomeView.spec.ts src/components/layout/AuthSidebar.spec.ts`
  failed because `mode=transcript` still selected the transcript host.
- `PR-0374` focused green: the same command passed with 35 tests after the
  mode-query selector and helper were retired.
- `PR-0374` close-out gates passed:
  `pdm run fe-type-check`, `pdm run fe-lint`,
  `pdm run test tests/unit/scripts/test_playwright_script_surface.py`, and
  `pdm run python -m scripts.authenticated_app_identity_split --base-url http://localhost:5173`.
  Live proof artifact:
  `.artifacts/playwright-pr-0368-presentation-identity-split/20260622T221450Z/`.
- `PR-0374` follow-up: `scripts/audio_transcription_parity_live.py` opens
  `/apps/audio-transcription` directly and no longer clicks the retired
  mode-tab selector. Full transcript parity proof was not rerun in that session
  because it is the heavy STT/upload/export live lane.
