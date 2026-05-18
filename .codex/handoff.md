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
- Date: 2026-05-19.
- Branch: `main`.
- Current lanes under `ST-21-03`: `PR-0330` is outside-designer layout-only;
  `PR-0331` is Codex-owned reviewed AI-facit export integrity and is ready.
- Current state: `ADR-0085` accepted; `PR-0318` through `PR-0323` done;
  `REV-PR-0318` through `REV-PR-0322` approved; Sir Convert `TASK-292` done;
  `PR-0325` live evidence exists; `PR-0326`, `PR-0327`, and `PR-0328` are
  implemented; `PR-0329` is done; `PR-0330` is ready as a small-screen layout
  strategy; `PR-0331` is ready with retained Hemma/public proof.
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
- `PR-0331` is ready:
  `docs/backlog/prs/pr-0331-st-21-03-exam-converter-reviewed-ai-facit-contract-affordance-reconciliation.md`.
  It is not part of `PR-0330` and is not for the outside designer.
- `PR-0331` RCA/contract map is updated:
  `docs/reference/ref-exam-converter-reviewed-ai-facit-contract-map-pr-0331.md`.
  Closeout proof shows reviewed keys survive projection, reviewed apply, target
  readiness, and PDF/QTI downloads on the public Hemma lane.
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
  Sir Convert Task 333 and HuleEdu TASK-0567 are now landed for non-matching
  unified corrections. `PR-0332` must keep using only the unified HuleEdu
  source-state/apply routes and must not preserve the old Task 324 matching
  route as a bridge, shim, alias, wrapper, adapter, or compatibility layer.
- `PR-0332` is done as the non-durable unified-correction consumer/projection
  slice. It consumes only Task 333-supported non-matching correction families:
  `point_correction`,
  `manual_choice_answer_key`, `manual_gap_open_cloze_answer_key`, and
  `item_text_patch`. `manual_matching_answer_key` stays blocked until Sir
  Convert Task 332 issues matching-capable producer state.
- `ADR-0087` is accepted by user-lead (2026-05-19) and `REV-ST-21-04` is
  approved. `ST-21-04` is ready and owns durable authenticated teacher
  correction sessions: Skriptoteket persists source-bound correction intents;
  Sir Convert remains stateless and applies the complete supported persisted
  set during replay/projection/export.
- `ST-21-04` implementation PR chain is created: `PR-0333` backend
  aggregate/persistence is ready; `PR-0334` API/types, `PR-0335` replay
  orchestration, `PR-0336` frontend readback, and `PR-0337` browser/artifact
  proof are blocked in order behind their predecessors.
- `frontend/apps/skriptoteket/src/api/sirConvertOpenapi.d.ts` was regenerated
  from the current Sir Convert v2 OpenAPI snapshot for PR-0332. Skriptoteket's
  own backend `openapi.d.ts` was not regenerated because this slice adds no
  Skriptoteket FastAPI routes or schema surface.
- `PR-0331` evidence and cleanup details are retained in the PR/reference docs;
  current proof script is `scripts/playwright_pr_0331_reviewed_ai_facit_live.py`.
## Verification
- Current `PR-0331` second cleanup passed:
  `pdm run fe-test -- --run src/views/apps/ExamConverterAuthenticatedFilesActionSlice.spec.ts src/views/apps/ExamConverterAuthenticatedReviewSlice.spec.ts src/views/apps/ExamConverterAuthenticatedUiInspectionFixtures.spec.ts`.
- Current `PR-0331` second cleanup passed: `pdm run fe-type-check`.
- Current `PR-0331` broader focused suite passed:
  `pdm run fe-test -- --run src/api/sirConvertGateway/client.spec.ts src/api/sirConvertGateway/completionContract.spec.ts src/api/sirConvertGateway/requestContext.spec.ts src/views/apps/ExamConverterAuthenticatedReviewSlice.spec.ts src/views/apps/ExamConverterAuthenticatedFilesActionSlice.spec.ts src/views/apps/ExamConverterAuthenticatedRuntimeBridgeSlice.spec.ts src/views/apps/ExamConverterAuthenticatedUiInspectionFixtures.spec.ts`.
- Current `PR-0331` second cleanup passed: `pdm run fe-lint` and
  `pdm run docs-validate`.
- Current PR-0332 unified non-matching correction slice passed focused Vitest
  for `src/api/sirConvertGateway/client.spec.ts` and
  `src/views/apps/ExamConverterAuthenticatedCorrectionSlice.spec.ts` (2 files /
  19 tests), `pdm run fe-type-check`, and `pdm run fe-lint`.
- Current PR-0332 correction UX refinement: teacher-authored item text, point,
  and answer-key commits use correction-local applying state, not
  `startConversion()`, with focused correction/review tests, typecheck, lint,
  and internal-browser `missing-facit` smoke passing.
- Previous PR-0332 point/manual-choice/manual-gap correction slice passed
  broader focused Vitest (9 files / 56 tests), `pdm run fe-type-check`,
  `pdm run fe-lint`, `pdm run fe-build` with the existing Vite chunk-size
  warning, `pdm run docs-validate`, `pdm run handoff-validate`, and
  `git diff --check`.
- Current `PR-0331` governance correction proof:
  `frontend/apps/skriptoteket/node_modules/.bin/openapi-typescript /Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/_generated/openapi/sir-convert-a-lot-v2.openapi.json -o /tmp/sirConvertOpenapi.current.d.ts`
  and `diff -u frontend/apps/skriptoteket/src/api/sirConvertOpenapi.d.ts /tmp/sirConvertOpenapi.current.d.ts`
  produced no diff.
- Current `PR-0331` script-surface proof passed:
  `pdm run python -m py_compile scripts/playwright_pr_0331_reviewed_ai_facit_live.py scripts/_pr_0331_reviewed_ai_facit_artifacts.py`
  plus `pdm run test tests/unit/scripts/test_playwright_script_surface.py` and
  `pdm run lint`.
- Current `PR-0331` Hemma/public proof passed after Sir Convert revision
  `166fea9140ac2e5709aa30f5b432ffe1e53fe2c3` fixed OpenAI vision image URLs.
  Evidence:
  `.artifacts/playwright-pr-0331-reviewed-ai-facit-live/20260518T192044Z/`.
  The proof forced fresh idempotency keys, recorded `idempotent_replay=false`
  for both POSTs, reviewed four suggestions including item-013 gap-fill,
  downloaded PDF/QTI, found no forbidden artifact text, and retained QTI
  correct responses.
## How to Run
```bash
pdm run fe-test -- --run src/api/sirConvertGateway/client.spec.ts src/views/apps/ExamConverterAuthenticatedCorrectionSlice.spec.ts
pdm run fe-type-check
pdm run fe-lint
pdm run fe-build
pdm run docs-validate
pdm run handoff-validate
git diff --check
```
## Known Issues / Risks
- The `PR-0331` live proof script now forces fresh Sir Convert idempotency keys
  and uses Playwright request context for public-edge artifact reads; keep this
  behavior so future proofs cannot pass by replaying stale advisory jobs.
- Exported artifacts must not expose internal fallback/parser diagnostics.
- Teacher edit of prompts/stems and correct keys is not governed by `PR-0331`;
  accepted `ADR-0086` and done `PR-0332` own non-durable correction controls;
  accepted `ADR-0087`/ready `ST-21-04` own durable correction sessions.
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
- `PR-0331` is ready for review/closeout; keep the retained Hemma/public proof
  as the final acceptance evidence for reviewed AI-facit artifact integrity.
- Keep `PR-0332` separate from `PR-0331`; do not continue the Task 324 route.
  Non-matching Skriptoteket consumer migration now uses the unified Task
  333/TASK-0567 routes only. Matching remains blocked on Sir Convert Task 332.
- Next governed implementation slice is `PR-0333`: correction-session backend
  aggregate and persistence. Do not start API/replay/frontend proof slices until
  their ordered predecessors land.
- Implement `PR-0330` separately as phone/tablet/desktop layout strategy; rerun
  `PR-0324` proof only after reviewed-key export behavior is understood.
