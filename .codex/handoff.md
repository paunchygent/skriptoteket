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
- Date: 2026-05-17.
- Branch: `main`.
- Current lane: `PR-0329` Exam Converter reviewed AI-facit handoff under
  `ST-21-03`.
- Current state: `ADR-0085` accepted; `PR-0318` through `PR-0323` done;
  `REV-PR-0318` through `REV-PR-0322` approved; Sir Convert `TASK-292` done;
  `PR-0325` live evidence exists; `PR-0326`, `PR-0327`, and `PR-0328` are
  implemented. `PR-0329` is ready to fix the remaining review/apply UI
  handoff before rerunning `PR-0324` with the same byte-identical `.dxe`.
- Prior PR-0310 through PR-0314 history was compacted to
  `.codex/long-term-memory/entries/session-2026-05-11-pr-0310-through-pr-0314-phone-rules-history.md`.
- Prior PR-0325 live-proof details and PR-0326 task setup were compacted to
  `.codex/long-term-memory/entries/session-2026-05-17-pr-0325-pr-0326-exam-converter-history.md`.
## Status
- `ST-21-03` defines the public one-time Exam Converter lane plus the
  authenticated artifact workflow under `EPIC-21`.
- Public lane authority is now settled: HuleEdu mints only
  `PublicConversionGrantV1`; Sir Convert verifies that grant, creates
  public-grant-owned jobs/artifacts, and issues `PublicArtifactReadLeaseV1`;
  Skriptoteket keeps both authorities server-side.
- `PR-0323` aligned the Skriptoteket consumer with the grant-only HuleEdu shape:
  `src/skriptoteket/infrastructure/curated_apps/apps/conversion_hub/public_exam_converter_grants.py`
  no longer expects HuleEdu read leases, and
  `public_exam_converter_sir_convert_client_v2.py` owns parent-grant/read-lease
  Sir Convert calls.
- `PR-0322` live proof is approved in
  `docs/backlog/reviews/review-pr-0322-exam-converter-live-upstream-public-grant-proof.md`.
  Local proof artifacts are ignored under `.artifacts/pr-0322-live-proof/`.
- `PR-0324` authenticated proof is blocked by retained
  `docs/backlog/reviews/review-pr-0324-exam-converter-authenticated-end-to-end-proof.md`.
  Proof preflight found no authenticated bespoke Exam Converter host surface,
  no authenticated DigiExam artifact-bundle runtime surface, and no
  save-to-user-files path for downloaded Sir Convert named artifacts.
- `PR-0325` is the implemented authenticated remediation: host shell, local
  `.dxe`/optional result-PDF intake, runtime bridge, read-only artifact review,
  accepted-current-state gate, artifact download, and user-file save wiring.
  Durable slice details and live proof are retained in long-term memory.
- Key PR-0325 frontend surfaces:
  `ExamConverterAuthenticatedView.vue`,
  `frontend/apps/skriptoteket/src/api/sirConvertGateway/`,
  `digiexamIrReviewParser.ts`, `useExamConverterReviewArtifacts.ts`, and
  `useExamConverterFileActions.ts`.
- `PR-0325` also included the Task 306 Sir Convert consumer sync:
  regenerated `sirConvertOpenapi.d.ts`, added a reviewed-completion lineage
  fixture, removed obsolete terminal-result `target_availability` parsing, and
  removed Tailwind's production Vite plugin from Vitest's jsdom config.
- Accepted-current-state `Godkänn` from PR-0325 remains distinct from the
  reviewed-completion overlay path required by PR-0326.
- Sir Convert follow-up is still required before real long-running ETA can be
  shown; Skriptoteket must consume additive upstream progress later instead of
  treating browser-local progress as authoritative.
- Implemented
  `docs/backlog/prs/pr-0326-st-21-03-exam-converter-authenticated-llm-enrichment-consumer-sync.md`
  as the authenticated two-pass reviewed-completion consumer slice: first submit
  requests advisory local-LLM suggestions, UI shows AI-suggested facit in the
  right question panel plus compact `Godkänn alla`/`Skapa filer` affordances,
  reviewed decisions become `reviewed_completion_answer_key` overlay entries,
  and second submit applies the overlay before PDF/QTI readiness can change.
- `PR-0327` is implemented: a dev/test-only internal-browser fixture lane
  renders real authenticated Exam Converter post-conversion states after normal
  HuleEdu login. Do not use throwaway query hooks or browser-local state
  injection for future checks.
- `PR-0328` captures the current live proof blocker: authenticated testing as
  `paunchygent@gmail.com` replayed stale Sir Convert job
  `jobv2_c93420ae30f441cc8e4013cd2d` through deterministic idempotency. Its
  completion report had 17 items, 8 eligible machine-marked items, all 8 with
  `provider_request_failed`, and 0 answer payloads; current Qwen
  in-container JSON Schema probe succeeds, and newer Sir jobs have valid
  candidates.
- `PR-0328` is implemented: provider-only advisory failures now show the
  approved retry affordance (`Det gick inte att ta fram ett facitförslag.` +
  Lucide retry icon / `Försök igen`), use browser-runtime-local
  `advisoryRetryAttempt` starting at 1, add
  `advisory_retry_attempt:<n>` only to the client idempotency digest, preserve
  the same Sir Convert job spec/options, avoid automatic retry, and increment
  only after a completed retry returns the same provider-only failure class.
- `PR-0329` is done:
  `docs/backlog/prs/pr-0329-st-21-03-exam-converter-reviewed-ai-facit-handoff.md`.
  It added teacher-visible Lucktext rows for valid `gap_fill` AI-facit
  suggestions, proved accepted `item-013` suggestions build
  `reviewed_completion_answer_key` overlays, and proved refreshed file
  readiness comes from the reviewed apply job bundle rather than the advisory
  bundle.
## Verification
- PR-0325 verification history is retained in
  `.codex/long-term-memory/entries/session-2026-05-17-pr-0325-pr-0326-exam-converter-history.md`.
- Current PR-0326 implementation closeout:
  - `pdm run fe-test -- --run src/api/sirConvertGateway/client.spec.ts src/api/sirConvertGateway/completionContract.spec.ts src/api/sirConvertGateway/requestContext.spec.ts src/views/apps/ExamConverterAuthenticatedReviewSlice.spec.ts src/views/apps/ExamConverterAuthenticatedFilesActionSlice.spec.ts src/views/apps/ExamConverterAuthenticatedRuntimeBridgeSlice.spec.ts`
    passed, 6 files / 41 tests.
  - `pdm run fe-type-check`
  - `pdm run fe-lint`
  - `pdm run fe-build` passed with the existing unrelated Vite large-chunk
    warning.
  - Production bundle grep found no forbidden Sir Convert direct-host,
    credential, internal-identity, raw prompt/provider, or student-answer
    markers.
  - `pdm run docs-validate`
  - `pdm run handoff-validate`
  - `git diff --check`
  - Live authenticated Gateway proof remains for the `PR-0324` rerun because
    deployed Sir Convert still has to prove `answer_key_completion_report`
    delivery through HuleEdu Gateway.
- PR-0327 closeout:
  - `docs/backlog/prs/pr-0327-st-21-03-exam-converter-authenticated-internal-browser-ui-inspection-lane.md`
    created and closed as done.
  - `docs/runbooks/runbook-agent-browser-automation.md` now documents the
    internal-browser path and the upload-gated fixture requirement.
  - Focused Vitest passed: `pdm run fe-test -- --run src/views/apps/ExamConverterAuthenticatedUiInspectionFixtures.spec.ts src/views/apps/ExamConverterAuthenticatedReviewSlice.spec.ts src/views/apps/ExamConverterAuthenticatedFilesActionSlice.spec.ts src/router/routes.spec.ts`
    (4 files / 26 tests).
  - `pdm run fe-type-check`, `pdm run fe-lint`, `pdm run fe-build`,
    `pdm run docs-validate`, `pdm run handoff-validate`, and
    `git diff --check` passed.
  - `fe-build` ran on system Node `v26.0.0` without the Node `DEP0205`
    `module.register()` warning after the checked-in Tailwind pnpm patch.
  - Production bundle grep found no fixture-route or fixture-id strings:
    `complete-qti-blocked`, `complete-qti-ready`, `missing-facit`,
    `ai-facit-review`, `exam-converter-ui-inspection`, `ui-fixtures`.
  - Internal browser proof:
    `complete-qti-blocked` at 1512x900 showed success, no partial warning,
    visible QTI reason, and no exact main-content `Granska` action;
    `missing-facit` at 1512x900 preserved the desktop table + inspector;
    `missing-facit` at 1024x768 used the designed narrow-laptop composition
    with compact setup band, question navigator (`192px`), visible inspector
    (`430px`), and no horizontal document overflow.
  - Current visual proof files:
    `.artifacts/pr-0327-ui-proof/missing-facit-1024x768-designed-navigator-inspector.png`
    and
    `.artifacts/pr-0327-ui-proof/missing-facit-1512x900-table-inspector-preserved.png`.
- PR-0328 closeout:
  - Focused Vitest passed: `pdm run fe-test -- --run src/api/sirConvertGateway/requestContext.spec.ts src/views/apps/ExamConverterAuthenticatedAdvisoryRetry.spec.ts src/views/apps/ExamConverterAuthenticatedRuntimeBridgeSlice.spec.ts src/views/apps/ExamConverterAuthenticatedReviewSlice.spec.ts src/views/apps/ExamConverterAuthenticatedUiInspectionFixtures.spec.ts src/router/routes.spec.ts`
    (6 files / 37 tests).
  - `pdm run fe-type-check`, `pdm run fe-lint`, and `pdm run fe-build` passed;
    build retained the existing Vite large-chunk warning.
  - Production bundle grep found no fixture-route or fixture-id strings:
    `provider-only-advisory-failure`, `complete-qti-blocked`,
    `complete-qti-ready`, `missing-facit`, `ai-facit-review`,
    `exam-converter-ui-inspection`, `ui-fixtures`.
  - Internal browser proof via HuleEdu login opened
    `/apps/documents.conversion_hub/exam-converter/ui-fixtures/provider-only-advisory-failure`
    and verified visible retry panel/action, approved text, `Försök igen`, one
    Lucide SVG icon, and no `AI-facit` or provider wording inside the retry
    panel.
  - `pdm run docs-validate`, `pdm run handoff-validate`, and
    `git diff --check` passed.
- PR-0329 closeout:
  - Focused Vitest passed: `pdm run fe-test -- --run src/api/sirConvertGateway/client.spec.ts src/api/sirConvertGateway/completionContract.spec.ts src/api/sirConvertGateway/requestContext.spec.ts src/views/apps/ExamConverterAuthenticatedReviewSlice.spec.ts src/views/apps/ExamConverterAuthenticatedRuntimeBridgeSlice.spec.ts src/views/apps/ExamConverterAuthenticatedFilesActionSlice.spec.ts src/views/apps/ExamConverterAuthenticatedAdvisoryRetry.spec.ts src/views/apps/ExamConverterAuthenticatedUiInspectionFixtures.spec.ts`
    (8 files / 52 tests).
  - `pdm run fe-type-check`, `pdm run fe-lint`, and `pdm run fe-build` passed;
    build retained the existing Vite large-chunk warning.
  - Real-service local proof used HuleEdu auth edge + Sir Convert dev:
    `pdm run run-local-pdm auth-integration check` passed; `pdm run dev-check`
    in `sir-convert-a-lot` passed; Sir Convert `/readyz` returned
    `ready=true` with `service_profile=local_cpu_dev`.
  - Restarted `pdm run fe-dev` with local auth env (`VITE_HULEEDU_AUTH_BASE_URL`,
    `VITE_HULEEDU_AUTH_ENTRY_URL`, `VITE_DEV_PROXY_TARGET`) pointing to
    `http://localhost:8080`; the earlier remote-auth redirect is rejected proof.
  - Playwright proof opened
    `/apps/documents.conversion_hub/exam-converter/ui-fixtures/ai-facit-review`
    through `localhost:5173 -> localhost:8080 -> localhost:5174 -> localhost:5173`,
    observed AI-facit, confirmed `huleedu_session` and no `skriptoteket_session`, and saved
    `.artifacts/pr-0329-auth-edge-live/exam-converter-ai-facit-review-auth-edge.png`.
  - Authenticated browser fetch to `/sir-convert/v2/convert/jobs/does-not-exist`
    returned `404 job_not_found` through `api-gateway-service` with a
    correlation id; unauthenticated fetch returned `401`, proving the
    `/sir-convert` product edge is gated rather than bypassed.
## How to Run
```bash
pdm run pytest tests/unit/web/test_public_apps_exam_converter_runtime.py tests/unit/infrastructure/curated_apps/apps/conversion_hub/test_public_exam_converter_upstream_clients.py -q
pdm run fe-test -- --run src/views/apps/ExamConverterPublicView.spec.ts src/views/PublicAppHostView.spec.ts src/views/AppHostView.spec.ts
pdm run fe-type-check
pdm run fe-lint
pdm run fe-build
pdm run docs-validate
pdm run handoff-validate
git diff --check
```
## Known Issues / Risks
- Live authenticated facitförslag proof should not reuse stale
  `provider_request_failed` advisory reports. `PR-0328` now provides the
  explicit bounded retry attempt in the client idempotency digest for
  provider-only advisory failures.
## Next Steps
- Rerun/unblock `PR-0324` authenticated proof: use the same byte-identical
  `.dxe`, prove advisory first submit, explicit retry if stale provider-only
  replay appears, valid `answer_key_completion_report` delivery including
  vision-backed `item-013`, reviewed facitförslag overlay submit, reviewed
  apply artifacts, and final PDF/QTI readiness through HuleEdu Gateway.
- Do not reopen the public grant/read-lease lane unless HuleEdu or Sir Convert
  changes the accepted contract.
