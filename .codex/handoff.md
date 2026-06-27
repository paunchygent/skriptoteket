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
- Date: 2026-06-27.
- Branch: `main`.
- Latest closed work: `PR-0396`.
- Active worktree slice: `ST-37-05` shared save/export naming follow-ups; keep `PR-0369` blocked unless a concrete app-presentation API need appears.
## Status
- `EPIC-37` is active. `PR-0358` through `PR-0362` are done and govern the current product direction, Sir Convert boundary, shell plan, and app presentation sequence.
- `PR-0363` is done and approved by `REV-PR-0363`. Its mode-query bridge was historical cutover scaffolding and has been superseded by `PR-0374`.
- `PR-0365` is done. `frontend/apps/skriptoteket/src/components/layout/AuthSidebar.vue`,
  `frontend/apps/skriptoteket/src/components/layout/AuthSidebar.spec.ts`, and
  `scripts/authenticated_shell_navigation.py` now keep the
  persistent sidebar/mobile drawer utility-first with `Hem`, `Mina filer`,
  `Föreslå verktyg`, `Katalog`, and `Profil`; keep `Hjälp` owned only by the
  top auth bar; keep contributor/admin links below the utility block; and keep
  duplicate app links plus `Mina körningar`/`Dokumentkonvertering` out of
  persistent nav. `ST-37-03` is now done with retained shared-auth proof at
  `.artifacts/playwright-pr-0365-authenticated-shell-navigation/20260619T212625Z/`.
- `PR-0364` is done and approved by `REV-PR-0364`; detailed proof and post-deploy correction history was compacted to `.codex/long-term-memory/entries/session-2026-06-19-pr-0364-auth-home-proof-compaction.md`. Keep the authenticated-home app symbols from `frontend/apps/skriptoteket/src/components/home/homeWorkApps.ts`.
- `PR-0366` through `PR-0373` app presentation, public landing, registry, and
  dev-stack proof history is compacted to `.codex/long-term-memory/entries/session-2026-06-23-st-37-04-handoff-compaction.md`.
- Protected HuleEdu Gateway/browser-session proof must use Docker
  `skriptoteket_web` on `hule-network` with alias `skriptoteket-web`; do not
  use host Uvicorn for this lane.
- `PR-0368` is done and approved by `REV-PR-0368`:
  `docs/reference/ref-pr-0368-auth-edge-inventory-and-proof-plan.md`,
  `frontend/apps/skriptoteket/src/router/routes.ts`,
  `frontend/apps/skriptoteket/src/views/apps/ExamConverterAuthenticatedView.vue`,
  `frontend/apps/skriptoteket/src/components/home/homeWorkApps.ts`, focused
  route/host/home specs, and
  `scripts/authenticated_app_identity_split.py` now split
  `/apps/exam-converter` and `/apps/audio-transcription` while preserving the
  shared `documents.conversion_hub` backend/runtime and public Exam Converter
  route.
- `PR-0374` is implemented:
  `frontend/apps/skriptoteket/src/views/apps/ExamConverterAuthenticatedView.vue`
  now ignores stale `mode` query residue and defaults the generic
  `documents.conversion_hub` host to Exam Converter; canonical
  `/apps/exam-converter` and `/apps/audio-transcription` remain query-free;
  `frontend/apps/skriptoteket/src/views/apps/conversionHubModeRoute.ts` and
  `frontend/apps/skriptoteket/src/views/apps/ConversionHubModeTabs.vue` are
  removed; `frontend/apps/skriptoteket/src/views/apps/conversionHubModeRoute.spec.ts`
  now covers route behavior instead of the retired helper.
- `PR-0375` is done and approved by `REV-PR-0375`:
  `docs/backlog/prs/pr-0375-st-37-04-document-converter-backend-backed-mvp-planning.md`
  defines the Document Converter MVP as an authenticated-only scoped
  `documents.conversion_hub/document-converter` backend contract with one result
  artifact, server-authoritative download/save, retry/replay semantics, and no
  route/registry/runtime activation.
- `PR-0376` and `PR-0377` are done and approved by `REV-PR-0376` and
  `REV-PR-0377`: the transcript proof launcher removes operator port guessing
  for the fenced `remote-proof` lane, and active reusable proof scripts now use
  domain names and domain proof metadata instead of PR/task identifiers.
- `PR-0378` is done and approved by `REV-PR-0378`:
  `docs/backlog/prs/pr-0378-st-37-04-transcript-proof-failure-evidence-capture.md`
  adds bounded, redacted, pre-cleanup evidence capture from
  `huleedu_api_gateway_service`, `skriptoteket_web`, and
  `skriptoteket_worker` when the retained transcript proof fails after lane
  mutation. Evidence lands under
  `.artifacts/transcript-parity-proof-lane/<timestamp>/runtime-evidence/`
  and is linked from `failure-summary.json`. Product UI polling retry behavior
  is explicitly deferred until retained proof evidence identifies an actual
  transient failure class.
- `PR-0379` is done and approved by `REV-PR-0379`: it adds the local
  authenticated backend/API Document Converter contract under
  `/api/v1/apps/documents.conversion_hub/document-converter/...`, keeps the
  frontend route/card inert, keeps `PR-0369` blocked, and now enforces the
  governed upload boundary on the scoped submit route with filename
  suffix/content-type checks plus capped upload reads via
  `src/skriptoteket/web/uploads.py`.
- `PR-0380` is done as the corrected Document Converter product-contract queue:
  simple lanes run inside the Skriptoteket app boundary, Sir Convert is
  reserved for automatically detected heavy/OCR/complex PDF paths, general
  batch input targets up to 10 source documents or project entries, HTML/CSS to
  PDF needs project input plus separate/combined output and 24-hour temporary
  PDF preview, and route-visible UI waits for image mockup, HTML/CSS mockup,
  and copy-lock approval.
- `PR-0381` is done and approved by `REV-PR-0381`: the scoped Document
  Converter submit route accepts up to 10 validated uploads, automatically
  routes simple local lanes versus explicit Sir Convert producer decisions,
  stores local outputs server-side by local job id, centralizes reusable
  document rendering/extraction adapters, refreshes generated API types, and
  keeps `/apps/document-converter` inactive.
- `PR-0382` is done and approved by `REV-PR-0382`: it added the route-inactive
  HTML/CSS project preview contract and binary preview download types.
- `PR-0384` is done and approved by `REV-PR-0384`: `/apps/document-converter` is an
  authenticated Vue route before generic `/apps/:appId`, the home card links to
  it, and the dedicated UI consumes scoped project-preview endpoints with
  locked Swedish copy and only `separate_pdfs` / `combined_pdf`.
- `PR-0386` is done and approved by `REV-PR-0386`; `PR-0387` is done and approved by `REV-PR-0387`; `PR-0388` is approved by `REV-PR-0388`. WeasyPrint `69.0` is locked, the `web` image was rebuilt with BuildKit, and the live Grid-heavy proof succeeds through the approved best-effort path: native Grid first, app-owned compatibility retry only after WeasyPrint's internal Grid `AssertionError`.
- `PR-0385` is in correction after product review: the saved-file backend boundary
  remains owner-scoped/server-authoritative, but the visible history rail and
  inner `Arbetssätt` selector are removed; mode selection is now tabs above the
  workspace, the file lane is `Filkonvertering`, current-result state is private
  route continuity, and local uploads can be ordered batches up to 10 files.
  Multi-source `Mina filer` batches and combined general file-conversion output
  remain deferred until backend contracts exist. See
  `docs/backlog/reviews/review-pr-0385-document-converter-files-and-history-follow-up.md`.
## Verification
- Current retained proof regeneration is green for the scoped best-effort
  preview contract:
  - Skriptoteket Vite listens on `:5173` via `pdm run fe-dev-shared-auth`;
    HuleEdu auth UI listens on `:5174` via
    `pdm run run-local-pdm auth-integration fe-dev`.
  - `/opt/homebrew/bin/pdm run python -m scripts.authenticated_home_work_apps`
    succeeded with `.artifacts/authenticated-home-work-apps/20260626T031626Z/`.
  - `manifest.redacted.json` records `grid_layout_fixture_rendered=true`,
    expected visible text, visible CSS/image accents, missing-resource text,
    nonblank rendered PDF PNGs, and no raw external URL or filesystem path text.
  - Docker logs for `2026-06-26T03:16:20Z` through `2026-06-26T03:18:30Z`
    show native WeasyPrint Grid `AssertionError`, app-owned compatibility
    retry, preview POST/artifact GET `200`, and no final `422` or
    `FileNotFoundError`.
- PR-0365 / PR-0372 retained browser proof and screenshots are recorded in
  their PR/review docs and artifact directories; keep the Docker-service proof
  lane intact for authenticated surfaces.
  - PR-0368/PR-0378 detailed proof history is compacted to `.codex/long-term-memory/entries/session-2026-06-23-st-37-04-handoff-compaction.md`.
  - Older PR-0379 through PR-0386 verification details are compacted to `.codex/long-term-memory/entries/session-2026-06-26-pr-0388-handoff-compaction.md`.
  - `PR-0385` pre-correction focused local proof was green. Correction proof now includes Document Converter Vitest with `DocumentConverterProjectResult.spec.ts`, `DocumentConverterSingleFileView.spec.ts`, and `documentConverterFileApi.spec.ts`; rerun backend/API, build, docs/handoff, and final diff gates before marking complete.
  - `PR-0385` live authenticated proof is green after A2 title-row mode selector correction; `pdm run run-local-pdm auth-integration check` passed in HuleEdu and `pdm run python -m scripts.authenticated_home_work_apps --timeout-seconds 90` passed with `.artifacts/authenticated-home-work-apps/20260627T014512Z/manifest.redacted.json`.
  - `PR-0396` is done and approved by `REV-PR-0396`: backend naming/API tests passed with `34 passed`, Document Converter Vitest focused specs passed with `20 passed`, `fe-gen-api-types`, `lint`, `typecheck`, `fe-type-check`, `fe-lint`, `fe-build`, `handoff-validate`, `docs-validate`, and `git diff --check` passed locally. `fe-build` retained the existing large-chunk warnings.
  - `PR-0396` live authenticated proof passed through the HuleEdu browser-session lane with `pdm run python -m scripts.authenticated_home_work_apps --timeout-seconds 90`; artifact `.artifacts/authenticated-home-work-apps/20260627T041926Z/manifest.redacted.json` records desktop/compact Document Converter route captures, automatic project preview, rendered nonblank PDF page, expected text/CSS/image accents, and no raw external URL or filesystem path text.
  - PR-0388 focused backend proof is green locally and was rerun during retained
    re-review:
    `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib /opt/homebrew/bin/pdm run test tests/unit/application/curated_apps/test_document_converter_project_manifest.py tests/unit/infrastructure/documents/test_document_converter_project_previews.py tests/unit/infrastructure/documents/test_document_converter_project_renderer_best_effort.py`
    plus `tests/unit/cli/test_cleanup_document_converter_project_previews.py`
    passed with `43 passed`, including direct grid-heavy renderer fixtures,
    best-effort missing/blocked assets, traceback-scoped Grid fallback,
    visible text preservation, and cleanup CLI import coverage.
    `/opt/homebrew/bin/pdm run test tests/unit/scripts/test_playwright_script_surface.py`
    `pdm run fe-test -- --run src/views/apps/document-converter/DocumentConverterView.spec.ts`
    `pdm run fe-type-check`, `pdm run fe-lint`, `pdm run fe-build`,
    `pdm run lint`, and `pdm run typecheck` passed.
    Earlier red live-proof artifacts remain at
    `.artifacts/authenticated-home-work-apps/20260625T225535Z/`,
    `.artifacts/authenticated-home-work-apps/20260625T225726Z/`, and
    `.artifacts/authenticated-home-work-apps/20260625T225910Z/`, where
    `document-converter-preview-response.json` captured `422 VALIDATION_ERROR`
    while the grid-heavy fixture still hit a WeasyPrint `AssertionError`.
    Fresh rerun after the WeasyPrint 69/image rebuild and import repair
    succeeded at `.artifacts/authenticated-home-work-apps/20260626T031626Z/`.
## How to Run
```bash
# Reuse or start HuleEdu auth integration first, then ensure Skriptoteket uses Docker web.
pdm run dev-stack web-start

# Start/reuse Skriptoteket Vite with protected API traffic proxied to HuleEdu Gateway.
pdm run fe-dev-shared-auth

# If the HuleEdu login UI is not already serving on :5174, start it from the HuleEdu repo.
(cd /Users/olofs_mba/Documents/Repos/huleedu && pdm run run-local-pdm auth-integration fe-dev)

# Verify Gateway can resolve the product backend by Docker alias.
docker exec huleedu_api_gateway_service curl -sS -i --max-time 10 http://skriptoteket-web:8000/healthz

# Focused ST-37-04 / PR-0381-0384 checks.
pdm run test tests/unit/application/curated_apps/test_document_converter_project_manifest.py tests/unit/application/curated_apps/handlers/test_document_converter_project_previews.py tests/unit/infrastructure/documents/test_document_converter_project_previews.py tests/unit/web/conversion_hub/test_apps_document_converter_project_preview_api.py
pdm run test tests/unit/web/conversion_hub/test_apps_document_converter_api.py tests/unit/web/conversion_hub/test_apps_document_converter_batch_api.py tests/unit/application/curated_apps/handlers/test_document_converter_producer_routing.py tests/unit/application/curated_apps/handlers/test_document_converter_local_artifact_actions.py tests/unit/application/curated_apps/handlers/test_document_converter_artifact_saves.py
pdm run test tests/unit/web/conversion_hub/test_apps_conversion_hub_api.py tests/unit/application/curated_apps/handlers/test_conversion_hub_jobs.py tests/unit/application/curated_apps/handlers/test_conversion_hub_artifact_saves.py tests/unit/web/conversion_hub/test_apps_conversion_hub_transcript_saves_api.py tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_artifact_actions.py
pdm run test tests/unit/web/conversion_hub/test_apps_document_converter_api.py tests/unit/application/curated_apps/handlers/test_document_converter_artifact_saves.py
pdm run test tests/unit/web/conversion_hub/test_apps_conversion_hub_api.py tests/unit/application/curated_apps/handlers/test_conversion_hub_jobs.py tests/unit/application/curated_apps/handlers/test_conversion_hub_artifact_saves.py
pdm run fe-test -- --run src/components/ui/UiSegmentedTileToggle.spec.ts src/router/routes.spec.ts src/views/HomeView.spec.ts src/views/apps/document-converter/documentConverterProjectPreviewApi.spec.ts src/views/apps/document-converter/DocumentConverterView.spec.ts
pdm run test tests/unit/test_docker_dev_shared_auth_contract.py
pdm run test tests/unit/scripts/test_playwright_script_surface.py
pdm run test tests/unit/scripts/test_audio_transcription_parity_progress_snapshot.py tests/unit/scripts/test_audio_transcription_parity_summary_truthfulness.py tests/unit/scripts/test_sir_convert_trust_lane_preflight.py
pdm run test tests/unit/scripts/test_transcript_parity_proof_launcher.py
pdm run fe-type-check
pdm run fe-lint
pdm run docs-validate
pdm run handoff-validate
git diff --check

```
## Known Issues / Risks
- Do not start host `pdm run dev`/Uvicorn for Gateway-authenticated backend dev
  tests or browser proof. Gateway app continuation uses Docker DNS
  `skriptoteket-web:8000`, so host Uvicorn reproduces a false failure.
- For local shared-auth proof, use only
  `/Users/olofs_mba/Documents/Repos/huleedu/.artifacts/skriptoteket-auth-bootstrap/local-shared-verify-export.json`.
  The active proof script rejects unsupported HuleEdu subject-export names.
- If Gateway `:8080` appears occupied by Docker while no container publishes
  it, suspect stale Docker Desktop port-proxy state; restart Docker Desktop and
  recreate the affected HuleEdu services before blaming app code.
- Hemma/server activity is paused by user instruction. Do not run Hemma deploy,
  monitors, SSH, or transcript remote-proof commands until explicitly re-allowed.
- Keep the Docker-service proof lane intact for `PR-0364` and `PR-0365`.
## Next Steps
- Next governed step: keep broader shared extraction in `PR-0391`/`PR-0392`; `PR-0393` through `PR-0395` remain separate app/file adoption slices.
- Keep `PR-0369` blocked unless later route-visible work proves a concrete backend/API app-presentation contract need.
- `PR-0277` remains open for `REV-PR-0277` plus fresh Teams unfurl proof.
