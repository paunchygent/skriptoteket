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
- Date: 2026-06-13.
- Branch: `codex/skriptoteket-pr-0349-trust-alignment`.
- ST-21 transcript lane is active. `PR-0342` has accepted live Gateway proof;
  `ST-21-07` / `PR-0343` is implemented for durable saved `transcript_json`.
  `ST-21-08` / `PR-0344` through `PR-0348` are implemented for progress/cancel
  parity, formatter authority sync, saved speaker overlays, overlay-aware
  formatter replay, download, and Mina filer save. `PR-0349` live proof now has
  reviewed HuleEdu/Sir Convert trust alignment plus reviewed upload/admission
  progress remediation; the final Hemma live proof is still pending.
- Current lanes under `ST-21-03`: `PR-0330` is canceled after `PR-0338`;
  `PR-0331` is Codex-owned reviewed AI-facit export integrity and is ready.
- Current state: `ADR-0085` accepted; `PR-0318` through `PR-0323` done;
  `REV-PR-0318` through `REV-PR-0322` approved; Sir Convert `TASK-292` done;
  `PR-0325` live evidence exists; `PR-0326`, `PR-0327`, and `PR-0328` are
  implemented; `PR-0329` is done; `PR-0330` is canceled as a reviewed-AI phone
  strategy; `PR-0331` is ready with retained Hemma/public proof.
- Prior PR-0310 through PR-0314 history:
  `.codex/long-term-memory/entries/session-2026-05-11-pr-0310-through-pr-0314-phone-rules-history.md`.
- Prior PR-0325 through PR-0326 live-proof history:
  `.codex/long-term-memory/entries/session-2026-05-17-pr-0325-pr-0326-exam-converter-history.md`.
- Prior PR-0326 through PR-0331 AI-facit history:
  `.codex/long-term-memory/entries/session-2026-05-17-pr-0326-through-pr-0331-ai-facit-review-history.md`.
- Prior PR-0332 through PR-0342 correction/transcript history:
  `.codex/long-term-memory/entries/session-2026-06-12-pr-0332-through-pr-0342-correction-transcript-history.md`.
## Status
- Earlier ST-21-03 / PR-0325 through PR-0331 proof and contract history is
  retained in the governed PR/reference docs and long-term memory entries above.
  Keep the fresh-source/idempotency lessons from those proofs for future
  artifact checks.
- Corrected `PR-0331` item-type contract: matching and single-/multi-gap
  `Lucktext`/open-cloze are supported in the source-neutral IR and QTI/PDF
  export contract. PDF may render gapped items as free text, but accepted
  gapped key values must still be included. Do not treat current DigiExam
  adapter restrictions as product limitations.
- `PR-0332` through `PR-0341` are done across non-durable correction controls,
  durable correction sessions, replay/artifact authority, AI outcome reporting,
  and authoring/export boundary separation. Matching remains blocked until Sir
  Convert has an accepted matching-capable producer. Do not restore the old Task
  324 matching route in any form.
- `frontend/apps/skriptoteket/src/api/sirConvertOpenapi.d.ts` was regenerated
  from the current Sir Convert v2 OpenAPI snapshot for PR-0332. Skriptoteket's
  own `frontend/apps/skriptoteket/src/api/openapi.d.ts` was regenerated for
  `PR-0341` after removing `review_decision` / `conflict_family` from the
  local correction-session API surface.
- `PR-0331` evidence and cleanup details are retained in the PR/reference docs;
  current proof script is `scripts/playwright_pr_0331_reviewed_ai_facit_live.py`.
- `PR-0342` is done with accepted live proof:
  `docs/backlog/prs/pr-0342-st-21-05-transcript-intake-and-gateway-lifecycle-client.md`.
  Retained review
  `docs/backlog/reviews/review-transcript-gateway-live-proof-remediation.md`
  approved deployed proof for English and Swedish fixtures through
  Skriptoteket -> HuleEdu Gateway -> Sir Convert -> STT/diarization ->
  canonical `transcript_json`. No public/no-login/direct Sir Convert path,
  local STT/diarization, durable transcript save, or formatter output was
  added.
- `PR-0343` is implemented:
  `docs/backlog/prs/pr-0343-st-21-07-durable-transcript-json-save-boundary.md`.
  It adds a typed `conversion_hub_saved_transcripts` aggregate, authenticated
  transcript job registration/save/readback routes, frontend save affordance,
  OpenAPI regeneration, migration coverage, and approved retained review
  `docs/backlog/reviews/review-pr-0343-durable-transcript-json-save-boundary.md`.
  Sir Convert Story 54 / Task 358 is now accepted for product-neutral TXT,
  Markdown, WebVTT, and SRT formatter artifacts. Overlay-aware exports are
  governed by new Sir Convert Story 56, HuleEdu ST-01-09/TASK-0675, and
  Skriptoteket ST-21-08.
- `PR-0344` is implemented:
  `docs/backlog/prs/pr-0344-st-21-08-transcript-lifecycle-observability-and-abort-feedback.md`.
  It replaces the narrow transcript `audioProgress` consumer shape with a
  strict typed progress snapshot, renders Swedish phase/percent/duration/chunk/
  heartbeat feedback, and adds abort states for pending, accepted, failed,
  rejected, and timed-out cancel attempts. Formatter replay, exports, and
  speaker overlays remain out of scope.
- `REV-PR-0344` is now approved:
  `docs/backlog/reviews/review-pr-0344-transcript-lifecycle-observability-and-abort-feedback.md`.
  Re-review confirmed the pre-id cancel queue now waits for a real Gateway
  cancel response before marking canceled/accepted, and malformed terminal
  `progress` payloads now fail closed.
- `PR-0345` and `PR-0346` are implemented:
  `docs/backlog/prs/pr-0345-st-21-08-formatter-authority-sync-and-artifact-selection.md` and
  `docs/backlog/prs/pr-0346-st-21-08-saved-transcript-speaker-overlay-aggregate.md`.
  `PR-0345` adds closed transcript artifact values/keys and rejects stale
  `not_implemented` formatter manifests. `PR-0346` adds owner-scoped speaker
  overlay persistence, API routes, and saved-transcript UI naming controls
  without mutating canonical `transcript_json`.
- `PR-0347` and `PR-0348` are implemented:
  `docs/backlog/prs/pr-0347-st-21-08-overlay-aware-formatter-replay-client.md`.
  `docs/backlog/prs/pr-0348-st-21-08-overlay-aware-download-and-mina-filer-save.md`.
  Replay now prepares owner-scoped saved transcript JSON plus overlays through
  HuleEdu Gateway, persists producer-owned TXT/MD/VTT/SRT refs, and exposes
  backend-authorized download/Mina filer save actions from those refs only.
- `REV-PR-0348` is approved:
  `docs/backlog/reviews/review-pr-0348-overlay-aware-download-and-mina-filer-save.md`.
  Re-review confirmed owner-scoped persisted-provenance checks for download/save;
  `PR-0349` live proof remains the closeout gate.
- `PR-0349` is implemented but not live-proof closed:
  `docs/backlog/prs/pr-0349-st-21-08-transcript-parity-live-proof-and-closeout.md`.
  HuleEdu `TASK-0676` and Sir Convert `task-361` are approved and the focused
  cross-repo trust-profile smoke is green. The old retained identity failure
  `.artifacts/playwright-pr-0349-transcript-parity-live/20260613T153843Z/`
  remains historical evidence only. The new upload/admission remediation adds
  visible pre-job upload progress, local upload abort, fresh proof-upload file
  names, and observed-network cancel-path classification; `REV-PR-0349` is
  approved for this remediation slice but not for final live parity.
## Verification
- Prior PR-0331 through PR-0336 verification details are retained in their
  governed PR/review docs and long-term memory entries.
- PR-0339 through PR-0348 verification details are retained in their governed
  PR/review docs.
- Current PR-0342 live proof:
  `.artifacts/transcript-live-gateway-proof/20260611T003730Z/proof-summary.json`
  and
  `.artifacts/transcript-live-gateway-proof/20260611T003748Z/proof-summary.json`
  show Gateway POST/result/artifacts/`transcript_json` statuses all `200`, UI
  terminal state `succeeded`, and canonical `transcript_json_v1` for English
  and Swedish fixtures.
- Current PR-0343 implementation proof:
  backend red test failed on missing transcript-save modules, then
  `pdm run test tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_saves.py tests/unit/web/conversion_hub/test_apps_conversion_hub_transcript_saves_api.py tests/integration/infrastructure/repositories/test_conversion_hub_saved_transcript_repository.py`
  passed with 8 tests. A follow-up hardening pass added owner+id saved-
  transcript readback at the repository query boundary; that same command first
  failed red before the repository method existed and now passes green.
- Current PR-0343 migration proof:
  `pdm run test 'tests/integration/test_migration_revision_coverage_idempotent.py::test_uncovered_migration_revision_is_idempotent[c4e8f0a2d6b9]' --override-ini addopts='' -m docker`
  passed.
- Current PR-0343 frontend/static proof:
  `pdm run fe-test -- src/views/apps/ConversionHubTranscriptMode.spec.ts src/api/conversionHubTranscriptSaves.spec.ts src/views/apps/conversion-hub-transcript/TranscriptWorkspaceShell.spec.ts src/api/sirConvertGateway/transcriptClient.spec.ts`,
  `pdm run lint`, `pdm run typecheck`, `pdm run fe-type-check`,
  `pdm run fe-lint`, `pdm run fe-build`, and `pdm run fe-gen-api-types`
  passed. The save-client spec pins raw canonical `transcript_json`
  preservation. `pdm run fe-dev` is running at `http://localhost:5173/`.
  In-app browser transport closed during route navigation, and the SPA package
  has no Playwright CLI binary, so no authenticated browser screenshot was
  captured in this turn.
- Current PR-0344 through PR-0348 proof details are retained in their PR/review
  docs. The key green gates were focused backend/frontend transcript tests,
  migration idempotency for `d7c9a1e4b6f2` and `e1f2a3b4c5d6`, OpenAPI/type
  generation, lint, typecheck, frontend typecheck/lint/build, docs/handoff
  validation, and `git diff --check`.
- Current PR-0349 migration proof:
  `HULEEDU_ENV_OVERLAY_FILE=output/tmp/pr0349-shared-postgres-migrations.env pdm run run-local-pdm db-lifecycle verify --all`
  passed for 13 HuleEdu shared PostgreSQL DBs, and
  `pdm run dev-stack db-upgrade` passed for Skriptoteket.
- Current PR-0349 retained historical blocked proof:
  `pdm run python -m scripts.playwright_pr_0349_transcript_parity_live --base-url http://127.0.0.1:5173 --dotenv .env --timeout-seconds 1200`
  wrote
  `.artifacts/playwright-pr-0349-transcript-parity-live/20260613T153843Z/proof-summary.json`
  with primary `failure.type=sir_convert_internal_identity_rejected`, HTTP
  `401`, `blocker_error_code=auth_invalid_internal_identity`, and
  `blocker_reason=invalid_internal_identity_signature`; manifest lists only
  `network.bounded.json`, `browser-console.bounded.json`, and `failure.png`.
- Current PR-0349 cross-repo smoke: HuleEdu profile publisher passed for
  `local-auth-integration` and `hemma-production` with fingerprint
  `46aefc0edc2f71267e2df783ca27f4df2b0da269cc7e84b43cbe2de6ac7c1992`;
  Sir Convert Task 361 focused suite passed with `39 passed`.
- Current PR-0349 upload/admission proof gates: `pdm run fe-test -- --run frontend/apps/skriptoteket/src/api/sirConvertGateway/transcriptClient.spec.ts frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/useTranscriptGatewayRuntime.spec.ts frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/TranscriptWorkspaceShell.spec.ts frontend/apps/skriptoteket/src/views/apps/ConversionHubTranscriptMode.spec.ts` passed with 30 tests; `pdm run test tests/unit/scripts/test_playwright_script_surface.py tests/unit/scripts/test_conversion_hub_transcript_docs_guard.py tests/unit/scripts/test_playwright_pr_0349_summary_truthfulness.py` passed with 10 tests; `pdm run fe-type-check`, `pdm run docs-validate`, and `git diff --check` passed.
## How to Run
```bash
pdm run fe-test -- --run src/api/conversionHubTranscriptFormatterArtifactActions.spec.ts src/views/apps/conversion-hub-transcript/TranscriptWorkspaceShell.spec.ts
pdm run test tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_saves.py tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_artifact_actions.py tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_replay.py tests/unit/web/conversion_hub/test_apps_conversion_hub_transcript_saves_api.py
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
- Transcript formatter/export follow-ups must persist only from saved canonical
  `transcript_json` or accepted Sir Convert formatter/replay artifacts, not
  source audio, local re-transcription, browser-local formatting, or invented
  parallel transcript truth.
## Next Steps
- Commit/push the reviewed upload/admission remediation, deploy Skriptoteket to
  Hemma, then rerun `PR-0349` live proof through progress, cancel feedback,
  durable save, speaker rename, replay export, download, and Mina filer save.
