# Session Handoff
Keep this file updated so the next session can pick up work quickly.
## Editing Rules (do not break structure)
- Keep the headings and section order exactly as-is; only fill in content.
- Use short bullets; include key file paths (e.g., `src/...`, `docs/...`) and exact commands.
- Do not paste large code blocks; link to files.
- Never include secrets/tokens/passwords or personal data.
- Keep this file under 200 lines.
- When compacting this file, move non-session-vital history to
  `.codex/long-term-memory/entries/` first.
## Snapshot
- Date: 2026-05-18.
- Branch: `main`.
- Current lanes under `ST-21-03`: `PR-0330` is outside-designer layout-only;
  `PR-0331` is Codex-owned reviewed AI-facit plumbing/export-contract
  integrity.
- Current state: `ADR-0085` accepted; `PR-0318` through `PR-0323` done;
  `REV-PR-0318` through `REV-PR-0322` approved; Sir Convert `TASK-292` done;
  `PR-0325` live evidence exists; `PR-0326`, `PR-0327`, and `PR-0328` are
  implemented; `PR-0329` is done; `PR-0330` is ready as a small-screen layout
  strategy; `PR-0331` is in progress as a separate Codex-owned plumbing/export-
  contract task.
- Prior PR-0310 through PR-0314 history:
  `.codex/long-term-memory/entries/session-2026-05-11-pr-0310-through-pr-0314-phone-rules-history.md`.
- Prior PR-0325 through PR-0326 live-proof history:
  `.codex/long-term-memory/entries/session-2026-05-17-pr-0325-pr-0326-exam-converter-history.md`.
- Prior PR-0326 through PR-0331 AI-facit history:
  `.codex/long-term-memory/entries/session-2026-05-17-pr-0326-through-pr-0331-ai-facit-review-history.md`.
## Status
- `ST-21-03` defines the public one-time Exam Converter lane plus the
  authenticated artifact workflow under `EPIC-21`.
- Public lane authority is settled: HuleEdu mints `PublicConversionGrantV1`;
  Sir Convert verifies it, creates public-grant-owned jobs/artifacts, and
  issues `PublicArtifactReadLeaseV1`; Skriptoteket keeps authorities server-side.
- `PR-0324` authenticated proof remains blocked by retained
  `docs/backlog/reviews/review-pr-0324-exam-converter-authenticated-end-to-end-proof.md`.
- `PR-0325` implemented the authenticated host/runtime/save surface; key
  surfaces include `ExamConverterAuthenticatedView.vue`,
  `frontend/apps/skriptoteket/src/api/sirConvertGateway/`,
  `digiexamIrReviewParser.ts`, `useExamConverterReviewArtifacts.ts`, and
  `useExamConverterFileActions.ts`.
- Current-state export from `PR-0325` remains distinct from the
  reviewed-completion overlay path added in `PR-0326`; this distinction is now
  a UX and contract risk in `PR-0331`.
- `PR-0326` added the two-pass reviewed-completion consumer flow: advisory
  submit, AI-facit suggestions, reviewed overlay entries, and reviewed apply.
- `PR-0327` added the governed internal-browser fixture lane. Do not use
  throwaway query hooks or browser-local state injection for future checks.
- `PR-0328` added explicit provider-only advisory retry via bounded
  `advisoryRetryAttempt` in the client idempotency digest.
- `PR-0329` is done:
  `docs/backlog/prs/pr-0329-st-21-03-exam-converter-reviewed-ai-facit-handoff.md`.
  It proved valid `gap_fill` suggestions can build reviewed-completion overlays
  and reload readiness from the reviewed apply job bundle.
- `PR-0330` is ready:
  `docs/backlog/prs/pr-0330-st-21-03-exam-converter-small-screen-ai-facit-review-layout-strategy.md`.
  It defines phone (`<768px`) as a separate reduced companion layout, tablet/
  narrow-laptop (`768px-1199px`) as navigator/detail, and desktop (`>=1200px`)
  as table/detail. It must remain layout-only. Design package lives in
  `.codex/repomix_packages/`.
- `PR-0331` is in progress:
  `docs/backlog/prs/pr-0331-st-21-03-exam-converter-reviewed-ai-facit-contract-affordance-reconciliation.md`.
  It is not part of `PR-0330` and is not for the outside designer; highest-
  severity blocker is that teacher-approved AI suggestions appear to be removed
  or omitted before downloaded artifacts are generated.
- `PR-0331` RCA/contract map is started:
  `docs/reference/ref-exam-converter-reviewed-ai-facit-contract-map-pr-0331.md`.
  Working diagnosis: post-apply Skriptoteket projection ignored effective
  answer keys, exposed current-state export as a competing approval path, and
  that later source-only review-decision submit can replace reviewed-key
  downloads with manual-unkeyed artifacts.
- Corrected `PR-0331` item-type contract: matching and single-/multi-gap
  `Lucktext`/open-cloze are supported in the source-neutral IR and QTI/PDF
  export contract. PDF may render gapped items as free text, but accepted
  gapped key values must still be included. Do not treat current DigiExam
  adapter restrictions as product limitations.
- `PR-0331` governance correction: teacher-owned correction/edit workflow is
  not a product decision made inside `PR-0331`. Accepted `ADR-0086` and
  independent `PR-0332` now govern stems/prompts, points, choice keys, and
  gapped/open-cloze teacher correction overlays. Matching remains future work
  until Sir Convert Task 332 provides a real matching-capable producer.
- `ADR-0086` is accepted and `REV-PR-0332` is approved. Task 322 and Task 323
  remain useful producer prerequisites; Task 324's matching route is
  superseded/abandoned by accepted Sir Convert ADR-0011 and completed Task 327.
  New `PR-0332` correction work must wait for Sir Convert Task 333 and HuleEdu
  TASK-0567 for non-matching unified corrections, and must not preserve the old
  route as a bridge, shim, alias, wrapper, adapter, or compatibility layer.
- User-supplied `PR-0331` evidence was copied to:
  `.artifacts/pr-0331-user-evidence/`.
- Local artifact inspection found:
  - `examnet-import (1).pdf` is six pages and exports key-bearing items as
    manual/free-text.
  - The PDF includes forbidden internal fallback copy:
    `Manuell bedömning. Ursprunglig lucktext utan betrodda accepterade värden.`
  - `qti-package (1).zip` contains eight item XML files plus one image resource.
  - Sampled QTI XML lacks `correctResponse`; lucktext items use
    `extendedTextInteraction`, and sampled choice item lacks correct choices.
- Initial `PR-0331` code cleanup started:
  - `examConverterAuthenticatedGapFillReviewFixtures.ts` now keeps source
    `ir_json` and `migration_manifest` source-missing after reviewed apply;
    reviewed keys live in `effective_ir_json`.
  - `digiexamIrQuestionReviewProjection.ts` consumes reviewed effective keys
    when projecting rows, suppressing stale missing `Facit` and advisory robot
    state for accepted items.
  - `digiexamIrReviewParser.ts` suppresses accepted-current-state overlay
    eligibility for reviewed apply bundles that contain effective answer keys.
- Second `PR-0331` code cleanup:
  - `ExamConverterFilesReadinessList.vue` no longer renders raw producer reason
    codes such as `unsupported_target_shape`.
  - `ExamConverterReviewDecisionGate.vue` uses `Skapa filer` for the
    current-state export path instead of generic approval wording, and its
    tooltip says unreviewed AI suggestions are not used.
  - `ExamConverterAiReviewActionPanel.vue` and
    `ExamConverterQuestionReviewShell.vue` use `Använd förslag`,
    `Använd alla förslag`, and `Skapa filer med facit` so local AI-facit
    selection is not confused with file creation.
  - After user correction, the fake local-only reject path was removed:
    `Lämna`/`Avvisa förslag`, `left_manual`, and `leaveSuggestion` are no
    longer active UI/state code.
- Remaining code pointers for `PR-0331`:
  - `useExamConverterAiFacitReview.ts` builds reviewed overlay items.
  - `useExamConverterReviewArtifacts.ts` loads optional `effective_ir_json`.
- `PR-0331` durable live proof script is added:
  `scripts/playwright_pr_0331_reviewed_ai_facit_live.py`, with artifact checks
  in `scripts/_pr_0331_reviewed_ai_facit_artifacts.py`.
## Verification
- Current `PR-0331` second cleanup passed:
  `pdm run fe-test -- --run src/views/apps/ExamConverterAuthenticatedFilesActionSlice.spec.ts src/views/apps/ExamConverterAuthenticatedReviewSlice.spec.ts src/views/apps/ExamConverterAuthenticatedUiInspectionFixtures.spec.ts`.
- Current `PR-0331` second cleanup passed: `pdm run fe-type-check`.
- Current `PR-0331` broader focused suite passed:
  `pdm run fe-test -- --run src/api/sirConvertGateway/client.spec.ts src/api/sirConvertGateway/completionContract.spec.ts src/api/sirConvertGateway/requestContext.spec.ts src/views/apps/ExamConverterAuthenticatedReviewSlice.spec.ts src/views/apps/ExamConverterAuthenticatedFilesActionSlice.spec.ts src/views/apps/ExamConverterAuthenticatedRuntimeBridgeSlice.spec.ts src/views/apps/ExamConverterAuthenticatedUiInspectionFixtures.spec.ts`.
- Current `PR-0331` second cleanup passed: `pdm run fe-lint` and
  `pdm run docs-validate`.
- Current PR-0332 point/manual-choice/manual-gap correction slice passed
  focused Vitest for `ExamConverterAuthenticatedCorrectionSlice.spec.ts` and
  `ExamConverterAuthenticatedReviewSlice.spec.ts` (2 files / 16 tests).
- Current PR-0332 point/manual-choice/manual-gap correction slice passed
  broader focused Vitest (9 files / 56 tests), `pdm run fe-type-check`,
  `pdm run fe-lint`, `pdm run fe-build` with the existing Vite chunk-size
  warning, `pdm run docs-validate`, `pdm run handoff-validate`, and
  `git diff --check`.
- Previous PR-0332 point/manual-choice correction slice passed focused Vitest
  (9 files / 55 tests), `pdm run fe-type-check`, `pdm run fe-lint`, and
  `pdm run fe-build` with the existing Vite chunk-size warning.
- Current `PR-0331` governance correction proof:
  `frontend/apps/skriptoteket/node_modules/.bin/openapi-typescript /Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/_generated/openapi/sir-convert-a-lot-v2.openapi.json -o /tmp/sirConvertOpenapi.current.d.ts`
  and `diff -u frontend/apps/skriptoteket/src/api/sirConvertOpenapi.d.ts /tmp/sirConvertOpenapi.current.d.ts`
  produced no diff.
- Current `PR-0331` script-surface proof passed:
  `pdm run python -m py_compile scripts/playwright_pr_0331_reviewed_ai_facit_live.py scripts/_pr_0331_reviewed_ai_facit_artifacts.py`
  plus `pdm run test tests/unit/scripts/test_playwright_script_surface.py` and
  `pdm run lint`.
- Current `PR-0331` live script reached authenticated Skriptoteket/HuleEdu/Sir
  Convert, then failed fast before reviewed apply because
  `answer_key_completion_report` returned zero valid suggestions:
  `provider_config_missing` for items 1-3 and `unsupported_assets` for item 13.
  Evidence:
  `.artifacts/playwright-pr-0331-reviewed-ai-facit-live/20260518T174149Z/`.
## How to Run
```bash
pdm run fe-test -- --run src/api/sirConvertGateway/client.spec.ts src/api/sirConvertGateway/completionContract.spec.ts src/api/sirConvertGateway/requestContext.spec.ts src/views/apps/ExamConverterAuthenticatedReviewSlice.spec.ts src/views/apps/ExamConverterAuthenticatedFilesActionSlice.spec.ts src/views/apps/ExamConverterAuthenticatedRuntimeBridgeSlice.spec.ts
pdm run fe-type-check
pdm run fe-lint
pdm run fe-build
pdm run docs-validate
pdm run handoff-validate
git diff --check
```
## Known Issues / Risks
- The live `PR-0331` proof script now exists, but final downloaded PDF/QTI
  artifact proof is blocked until Sir Convert runs with a configured provider
  that returns valid AI-facit suggestions.
- Exported artifacts must not expose internal fallback/parser diagnostics.
- Teacher edit of prompts/stems and correct keys is not governed by `PR-0331`;
  accepted `ADR-0086` and in-progress `PR-0332` own those correction controls.
- User correction: rejected AI suggestions and global
  rejection must become an explicit, non-confusing contract before PDF/QTI
  generation; the old local-only reject path has been removed.
- User correction: if corrected reviewed-apply artifacts
  drop any reviewed choice, matching, or gapped/open-cloze keys, Codex owns
  fixing Sir Convert source now rather than adding a downstream warning-only
  workaround.
## Next Steps
- Keep lane boundaries strict: `PR-0330` outside-designer layout, `PR-0331`
  Codex plumbing/export contract.
- Continue `PR-0331`: rerun the durable live Playwright proof against auth edge,
  Sir Convert, and a correctly configured provider-backed runtime. Local tests,
  generated-type no-diff proof, and provider-missing evidence are not final
  acceptance.
- Keep `PR-0332` separate from `PR-0331`; do not continue the Task 324 route.
  Next dependency is Sir Convert Task 333, then HuleEdu TASK-0567, then
  Skriptoteket consumer migration for non-matching corrections only. Matching
  remains blocked on Sir Convert Task 332.
- Implement `PR-0330` separately as phone/tablet/desktop layout strategy; rerun
  `PR-0324` proof only after reviewed-key export behavior is understood.
