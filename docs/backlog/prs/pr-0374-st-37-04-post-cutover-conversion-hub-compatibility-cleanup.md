---
type: pr
id: PR-0374
title: "ST-37-04 post-cutover conversion hub compatibility cleanup"
status: done
owners: "agents"
created: 2026-06-22
updated: 2026-06-23
stories:
  - "ST-37-04"
tags:
  - frontend
  - routing
  - cleanup
dependencies:
  - "PR-0368"
  - "REF-app-presentation-decomposition-and-naming-plan-v1"
acceptance_criteria:
  - "Given PR-0368 has proven separate Exam Converter and Audio Transcription app identities, when cleanup runs, then the temporary `documents.conversion_hub?mode=exam|transcript` presentation compatibility path is removed from normal routing, links, tests, and docs."
  - "Given the app identities share runtime machinery, when cleanup runs, then shared clients, backend logic, authenticated shell infrastructure, and HuleEdu Gateway auth-edge behavior remain centralized and covered by proof."
  - "Given legacy compatibility creates confusion, when cleanup closes, then no teacher-facing UI, copy, registry metadata, or app-host logic presents Conversion Hub as a durable product concept."
  - "Given route-visible entrypoints are changed, when the slice closes, then focused route/host tests and live shared-auth browser proof cover the canonical Exam Converter and Audio Transcription entrypoints."
---

# PR-0374: ST-37-04 Post-Cutover Conversion Hub Compatibility Cleanup

## Problem

`PR-0368` may retain the old `documents.conversion_hub?mode=exam|transcript`
entrypoints during cutover so the route-visible presentation split can land
without destabilizing the authenticated Sir Convert edge. That compatibility
must not become permanent product architecture.

## Goal

Remove the temporary Conversion Hub mode compatibility path after the separate
Exam Converter and Audio Transcription app identities are proven, while keeping
shared runtime/auth machinery centralized.

## Non-goals

- No backend/API decomposition unless the cleanup proves a concrete blocker.
- No duplicated auth-edge handling per app identity.
- No Document Converter implementation.
- No new compatibility surface replacing the removed mode query.

## Review gate

`REV-PR-0374` must be approved before code implementation begins.

## Implementation plan

1. Inventory all remaining mode-query and Conversion Hub presentation
   references after `PR-0368`, including router records, app-host selection,
   home/navigation links, tests, Playwright proof scripts, docs, and handoff.
   Classify each reference as shared backend/runtime authority, public Exam
   route authority, historical docs, active compatibility to remove, or
   canonical protected identity proof.
2. Add focused red tests for user-visible route behavior, not removed symbols:
   canonical `/apps/exam-converter` must render the Exam Converter workflow
   with no `mode` query or teacher-visible lane switch; canonical
   `/apps/audio-transcription` must render the Audio Transcription workflow
   with no `mode` query or teacher-visible lane switch; and
   `/apps/documents.conversion_hub?mode=transcript` must no longer select Audio
   Transcription as a normal product route.
3. Treat the old protected mode query as ignored cutover residue after cleanup:
   it may fall back to the shared default Exam Converter host for the
   `documents.conversion_hub` backend app id, but it must not redirect to,
   select, link to, or prove Audio Transcription or any other product identity.
4. Remove or retire mode-query routing helpers, tab components, compatibility
   test fixtures, and teacher-facing Conversion Hub copy that no longer serve a
   canonical entrypoint. Verify removed helper/component files by code search;
   do not keep active tests that only assert implementation-detail absence.
5. Preserve centralized shared clients, backend logic, authenticated shell
   infrastructure, and HuleEdu Gateway auth-edge proof.
6. Update docs and handoff so the only durable product language is Exam
   Converter, Audio Transcription, Document Converter, Klassrumskartan, and
   Kodredigerare.

## Test plan

- Red first:
  `pdm run fe-test -- --run src/router/routes.spec.ts src/App.spec.ts src/views/apps/ExamConverterAuthenticatedView.modeRoute.spec.ts src/views/apps/conversionHubModeRoute.spec.ts src/views/HomeView.spec.ts src/components/layout/AuthSidebar.spec.ts`
  after adding behavior assertions that the old mode query no longer selects
  Audio Transcription and canonical Exam/Audio routes remain query-free. This
  should fail on the current `PR-0368` state because `mode=transcript` still
  selects the transcript workflow through the compatibility host and the helper
  specs still preserve cutover parsing.
- Green:
  `pdm run fe-test -- --run src/router/routes.spec.ts src/App.spec.ts src/views/apps/ExamConverterAuthenticatedView.modeRoute.spec.ts src/views/apps/conversionHubModeRoute.spec.ts src/views/HomeView.spec.ts src/components/layout/AuthSidebar.spec.ts`
  after rewriting or retiring compatibility-preserving specs.
- Retained tests must prove:
  - `/apps/exam-converter` renders the Exam Converter workflow with an empty
    query and no teacher-visible lane switch.
  - `/apps/audio-transcription` renders the Audio Transcription workflow with
    an empty query and no teacher-visible lane switch.
  - `/apps/documents.conversion_hub?mode=transcript` no longer changes app
    identity to Audio Transcription.
  - Authenticated home, sidebar, and retained Playwright proof use only the
    canonical protected routes.
- Use code search/review, not active implementation-detail tests, to verify
  `ConversionHubModeTabs`, mode-query helpers, and cutover-only docs/tests are
  removed or retired.
- `pdm run fe-type-check`
- Live browser proof through the HuleEdu browser-session ceremony and
  shared-auth Docker service lane for canonical Exam Converter and Audio
  Transcription entrypoints:
  `pdm run python -m scripts.playwright_pr_0363_conversion_mode_deeplink --base-url http://localhost:5173`.
  The retained manifest must capture `/apps/exam-converter` and
  `/apps/audio-transcription` with empty query strings.
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Stop conditions

Stop and return to planning if cleanup requires any backend/API contract
change, generated-type change, backend app-id split, public Exam
route/capability change, or registry semantic change beyond removing stale
presentation language.

Stop before any HuleEdu Gateway/Sir Convert auth-edge rewrite, direct cookie
proof, credential POST shortcut, host-only backend proof, browser-authored
identity header, browser-direct Sir Convert call, or duplicated per-app auth
handling.

Stop before adding any Document Converter route, alias, host, runtime link,
proof target, or MVP behavior.

Stop before replacing `mode=exam|transcript` with any new compatibility query,
alias route, or hidden product-selector surface.

Stop if canonical Exam Converter and Audio Transcription cannot be proven
through `pdm run fe-dev-shared-auth`, the HuleEdu browser-session helper path,
and the shared-auth Docker service lane.

## Rollback plan

Restore the cutover-only compatibility path from `PR-0368` while preserving the
canonical app identities, then reopen this cleanup slice with the blocker
recorded.

## Implementation summary

`PR-0374` removed the mode-query presentation selector from the authenticated
Exam Converter host. Canonical `/apps/exam-converter` and
`/apps/audio-transcription` still pass explicit presentation identities, while
stale `/apps/documents.conversion_hub?mode=...` residue stays on the generic
backend app route and falls back to the shared Exam Converter host.

The cutover-only `conversionHubModeRoute` helper and `ConversionHubModeTabs`
component were retired. The former helper spec was replaced with route-behavior
coverage, not symbol-absence coverage. Home/sidebar/proof surfaces remain on
canonical query-free routes, and Document Converter remains inert.

## Validation

| Command | Outcome |
|---------|---------|
| `pdm run fe-test -- --run src/router/routes.spec.ts src/App.spec.ts src/views/apps/ExamConverterAuthenticatedView.modeRoute.spec.ts src/views/apps/conversionHubModeRoute.spec.ts src/views/HomeView.spec.ts src/components/layout/AuthSidebar.spec.ts` | Red before production cleanup: failed because `mode=transcript` still rendered the transcript host. Green after cleanup: passed, 35 tests. |
| `pdm run fe-type-check` | Passed. |
| `pdm run fe-lint` | Passed. |
| `pdm run test tests/unit/scripts/test_playwright_script_surface.py` | Passed, 3 tests. |
| `pdm run python -m scripts.playwright_pr_0363_conversion_mode_deeplink --base-url http://localhost:5173` | Passed; artifact `.artifacts/playwright-pr-0368-presentation-identity-split/20260622T221450Z/`. |
