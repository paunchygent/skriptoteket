# Session Handoff
Keep this file updated so the next session can pick up work quickly.
## Editing Rules (do not break structure)
- Keep the headings and section order exactly as-is; only fill in content.
- Use short bullets; include key file paths (e.g., `src/...`, `docs/...`) and exact commands.
- Do not paste large code blocks; link to files.
- Never include secrets/tokens/passwords or personal data.
- Keep this file under 200 lines.
- When compacting this file, move non-session-vital history to `.codex/long-term-memory/entries/` first.
## Snapshot
- Date: 2026-06-15.
- Branch: `main`.
- Sir Convert `task-363` is complete, reviewed, deployed, and consumed by Skriptoteket. Producer contract revision: `4b09baa989d38f582573a810f045e50c676139a9`.
- Skriptoteket `PR-0350` is implemented, reviewed, merged, pushed, and deployed. It removes the browser-owned formatter replay saga and replaces it with product-owned `POST/GET /formatter-exports` state over saved transcripts.
- Production wiring fix `14f4b3af` makes Hemma use internal Sir Convert base `http://sir_convert_a_lot_prod:8085`; `https://convert.hule.education` is the reserved public edge and returned `421` during the first live proof attempt.
- Prior PR-0310 through PR-0342 history lives in
  `.codex/long-term-memory/entries/session-2026-05-11-pr-0310-through-pr-0314-phone-rules-history.md`,
  `.codex/long-term-memory/entries/session-2026-05-17-pr-0325-pr-0326-exam-converter-history.md`,
  `.codex/long-term-memory/entries/session-2026-05-17-pr-0326-through-pr-0331-ai-facit-review-history.md`, and
  `.codex/long-term-memory/entries/session-2026-06-12-pr-0332-through-pr-0342-correction-transcript-history.md`.
## Status
- `REV-PR-0350` is approved:
  `docs/backlog/reviews/review-pr-0350-product-owned-transcript-replay-export-boundary.md`.
- `PR-0350` code replaced browser replay prepare/submit/poll/download/base64/
  complete with backend-owned Sir Convert replay submission, manifest/artifact
  verification, persisted product export state, and Swedish pending/running/
  succeeded/failed UI.
- `PR-0351` is implemented and `REV-PR-0351` is approved. It consumes the
  Task-364 progress-field contract, autosaves completed transcripts, removes
  the generic manual `Spara` gate, removes old per-artifact export rows, keeps
  selected-format actions as `Ladda ner` and `Mina filer`, and gates export on
  complete persisted speaker overlays.
- Skriptoteket-owned legacy replay/export UI and parser code was removed. The
  remaining `replay` strings in the transcript formatter export path are
  upstream Sir Convert literal contract values:
  `transcript_formatter_replay_v1`,
  `transcript_replay_bundle_manifest.json`, and
  `transcript_json_to_transcript_bundle_replay_v2`.
- `ST-21-08`, `EPIC-21`, `PR-0351`, and `.codex/handoff.md` were updated with
  PR-0351 closeout evidence and the successful local live proof.
- `ST-21-09` and `PR-0352` now govern remediation for the recurring local
  HuleEdu Gateway/Sir Convert trust-lane drift: keep Sir Convert's hosted
  model/runtime estate remote, but make signer/verifier lane coherence a
  default preflight before upload or producer job creation.
- `PR-0352` / `ST-21-09` is done and approved by `REV-PR-0352`. New helper:
  `scripts/_sir_convert_trust_lane_preflight.py`; proof hook:
  `scripts/playwright_pr_0349_transcript_parity_live.py`; focused tests:
  `tests/unit/scripts/test_sir_convert_trust_lane_preflight.py`.
- Follow-up commit `2fa27cfb` fixes the production formatter-export failure by
  making `SirConvertTranscriptFormatterProducerV2` accept `202 Accepted`, poll
  `/v2/convert/jobs/{job_id}`, then read result/artifacts.
- `PR-0353` is ready under `ST-26-07` for the 2026-06-14 Hemma production
  Playwright browser-install `[DEP0169]` warning. It requires removing the
  warning in a traced BuildKit production build while preserving
  Klassrumskartan 1200x630 share-preview PNG generation in-container.
- `PR-0354` is done for `ST-21-08` transcript UI remediation:
  `docs/backlog/prs/pr-0354-st-21-08-transcript-export-selector-and-responsive-layout-remediation.md`.
  It fixes selected export-chip readability, removes unstable post-upload
  progress counters, recovers stale formatter idempotency jobs, autosaves
  speaker-name edits, and proves responsive layout.
- `PR-0355` is done, approved, pushed to `main`, and deployed at `fe56307c`:
  `docs/backlog/prs/pr-0355-st-21-08-transcript-cancel-slot-rail-remediation.md`.
  It reserves the `Avbryt` row above `Starta transkribering`, removes the
  checkbox-like square icon, updates the empty upload copy, and has local
  remote-proof E2E evidence. Independent retained review
  `docs/backlog/reviews/review-pr-0355-transcript-cancel-slot-rail-remediation.md`
  is approved.
- `PR-0356` is done, approved, pushed to `main`, and deployed at `fe56307c`:
  authenticated Exam Converter intake is now source-only, early PDF/QTI target
  controls are removed, authenticated submit/retry always request default
  artifacts without `graded_result_pdf`, and `PR-0357` is the governed
  public-lane cleanup follow-up.
## Verification
- Archived PR-0351 through PR-0354 proof detail now lives in
  `.codex/long-term-memory/entries/session-2026-06-15-pr-0351-pr-0354-proof-compaction.md`
  so this handoff can stay focused on the current PR-0355/PR-0356 work.
- Green PR-0355 checks: `pdm run fe-test -- --run src/views/apps/conversion-hub-transcript/TranscriptWorkflowRailShell.spec.ts`,
  `pdm run fe-test -- --run src/views/apps/conversion-hub-transcript/TranscriptWorkspaceShell.spec.ts`,
  `pdm run fe-type-check`, and `pdm run docs-validate`. Required local dev E2E
  passed via `pdm run python -m scripts.playwright_pr_0349_transcript_parity_live --base-url http://127.0.0.1:5173 --dotenv .env --sir-convert-proof-lane hemma-remote-proof --sir-convert-gateway-backend-url http://host.docker.internal:28085 --sir-convert-producer-backend-url http://host.docker.internal:28085 --sir-convert-ready-url http://127.0.0.1:28085/readyz --gateway-signer-fingerprint 46aefc0edc2f71267e2df783ca27f4df2b0da269cc7e84b43cbe2de6ac7c1992 --sir-convert-trusted-fingerprint 46aefc0edc2f71267e2df783ca27f4df2b0da269cc7e84b43cbe2de6ac7c1992 --timeout-seconds 1200`;
  retained artifact:
  `.artifacts/playwright-pr-0349-transcript-parity-live/20260615T141002Z/proof-summary.json`.
- Red then green PR-0356 focused frontend/request-context bundle:
  first `pdm run fe-test -- --run src/views/apps/ExamConverterAuthenticatedView.spec.ts src/views/apps/ExamConverterAuthenticatedRuntimeBridgeSlice.spec.ts src/views/apps/ExamConverterAuthenticatedConversionSlice.spec.ts src/views/apps/ExamConverterAuthenticatedFilesActionSlice.spec.ts src/views/apps/ExamConverterAuthenticatedUiInspectionFixtures.spec.ts src/api/sirConvertGateway/requestContext.spec.ts src/api/sirConvertGateway/completionContract.spec.ts`
  failed with 3 expectation mismatches while the source-only slice was mid-edit;
  final overseer rerun passed with 7 files / 55 tests.
- Green PR-0356 frontend gates: `pdm run fe-type-check`, `pdm run fe-lint`,
  and `pdm run fe-build`; build retained the existing Vite dynamic/static import
  note plus large-chunk warnings.
- Green PR-0356 invalid-replacement regression:
  `pdm run fe-test -- --run src/views/apps/ExamConverterAuthenticatedView.spec.ts`
  passed with 1 file / 20 tests after preserving the current `.dxe` across
  invalid `.pdf`, `.docx`, and multi-`.dxe` replacement attempts.
- Green PR-0356 authenticated fixture proof through the sanctioned HuleEdu
  browser-session helper:
  `pdm run python -m scripts.playwright_pr_0356_source_only_fixture_proof --base-url http://127.0.0.1:5173 --dotenv .env`
  wrote
  `.artifacts/playwright-pr-0356-source-only-fixture-proof/20260614T233419Z/manifest.redacted.json`
  plus `complete-qti-ready-{desktop,compact}.png` and
  `missing-facit-{desktop,compact}.png`. Desktop `1512x900` and compact
  `1024x768` both prove no optional marked-PDF/supporting upload or target
  selector, while the fixture tabs still show ready PDF/QTI save/download
  actions and the missing-facit review shell.
- PR-0356 fixed overseer review is accepted in
  `docs/backlog/reviews/review-pr-0356-source-only-intake-export-owned-formats.md`
  after Goodall fixed the browser-proof gap and invalid-replacement state loss.
- Hemma deploy for `fe56307c` passed from log
  `/home/paunchygent/apps/skriptoteket/.artifacts/hemma-deploy-20260615-154707.log`.
  Remote checkout is `fe56307c`, `skriptoteket-web` and `skriptoteket-worker`
  are healthy, public `https://skriptoteket.hule.education/healthz` returned
  `{"status":"healthy","message":"Service is healthy"}`, and the deploy smoke
  artifact is
  `/home/paunchygent/apps/skriptoteket/.artifacts/pr-0146-seat-export-cutover-20260615-154707/smoke-result.json`.
## How to Run
```bash
pdm run test tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_exports.py tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_artifact_actions.py tests/unit/web/conversion_hub/test_apps_conversion_hub_transcript_saves_api.py tests/unit/scripts/test_playwright_pr_0349_summary_truthfulness.py
pdm run test tests/unit/scripts/test_sir_convert_trust_lane_preflight.py tests/unit/scripts/test_playwright_pr_0349_summary_truthfulness.py tests/unit/scripts/test_playwright_script_surface.py
pdm run fe-test -- --run src/api/sirConvertGateway/transcriptClient.spec.ts src/api/sirConvertGateway/transcriptProgressParsers.spec.ts src/views/apps/conversion-hub-transcript/TranscriptWorkspaceShell.spec.ts src/views/apps/conversion-hub-transcript/TranscriptWorkspaceShell.pr0351.spec.ts src/views/apps/conversion-hub-transcript/ConversionHubTranscriptHost.spec.ts src/views/apps/conversion-hub-transcript/ConversionHubTranscriptHost.pr0351.spec.ts src/api/conversionHubTranscriptFormatterArtifactActions.spec.ts src/views/apps/conversion-hub-transcript/useTranscriptGatewayRuntime.spec.ts
pdm run fe-gen-api-types
pdm run lint
pdm run typecheck
pdm run fe-type-check
pdm run fe-lint
pdm run fe-build
pdm run docs-validate
pdm run handoff-validate
git diff --check
pdm run hemma-deploy
pdm run hemma-deploy-monitor -- /home/paunchygent/apps/skriptoteket/.artifacts/hemma-deploy-YYYYMMDD-HHMMSS.log
# On Hemma, create .artifacts/proof-env/prod-transcript-<stamp>.env from HuleEdu
# bootstrap credentials without printing secret values, then run:
ssh hemma "cd /home/paunchygent/apps/skriptoteket && /home/paunchygent/.local/bin/pdm run python -m scripts.playwright_pr_0349_transcript_parity_live --audio-file /home/paunchygent/apps/sir-convert-a-lot/build/verification/stt-sidecar-live-fixtures/source-media/english-dialogue-two-speakers.mp3 --base-url https://skriptoteket.hule.education --dotenv .artifacts/proof-env/prod-transcript-YYYYMMDDTHHMMSSZ.env --artifact-root .artifacts/playwright-pr-0352-transcript-parity-native --sir-convert-proof-lane hemma-production --timeout-seconds 1200 --no-capture-local-backend-logs"
```
## Known Issues / Risks
- For native Hemma proof, create a gitignored/ignored dotenv under
  `.artifacts/proof-env/` from HuleEdu Hemma bootstrap credentials without
  printing secrets. Use the user-owned
  `.artifacts/playwright-pr-0352-transcript-parity-native` artifact root; the
  older `.artifacts/playwright-pr-0349-transcript-parity-live` directory is
  root-owned on Hemma from a prior run.
- Production formatter export must not use `https://convert.hule.education` as
  server-side producer base; that public edge is reserved/fail-closed.
- Production builds currently warn during `pdm run playwright install
  --with-deps chromium` because Playwright `1.58.0` browser downloads run on a
  vendored Node 24 driver path that reaches legacy `url.parse()` via proxy
  detection. `PR-0353` governs remediation; do not remove Playwright from the
  production image unless thumbnail rendering is rehomed or replaced.
- Keep transcript formatter/export follow-ups product-owned: saved canonical
  `transcript_json`, saved overlays, accepted Sir Convert artifacts, no browser
  submit/poll/download/base64/complete saga.
## Next Steps
- Separate follow-up: implement `PR-0353` after PR-0352 closeout to
  remove production Playwright `DEP0169` build warnings without breaking
  `ST-26-07` share-preview thumbnails.
