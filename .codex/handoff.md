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
- Date: 2026-06-23.
- Branch: `main`.
- Latest closed slice: `PR-0378` under `ST-37-04`.
- Active slice: `PR-0375` remains the separate Document Converter
  backend-backed MVP planning owner.
- Prior PR-0310 through PR-0356 history lives in `.codex/long-term-memory/entries/`.
## Status
- `EPIC-37` is active. `PR-0358` through `PR-0362` are done and govern the
  current product direction, Sir Convert boundary, shell plan, and app
  presentation sequence.
- `PR-0363` is done and approved by `REV-PR-0363`. Its mode-query bridge was
  historical cutover scaffolding and has been superseded by `PR-0374`.
- `PR-0365` is done. `frontend/apps/skriptoteket/src/components/layout/AuthSidebar.vue`,
  `frontend/apps/skriptoteket/src/components/layout/AuthSidebar.spec.ts`, and
  `scripts/authenticated_shell_navigation.py` now keep the
  persistent sidebar/mobile drawer utility-first with `Hem`, `Mina filer`,
  `Föreslå verktyg`, `Katalog`, and `Profil`; keep `Hjälp` owned only by the
  top auth bar; keep contributor/admin links below the utility block; and keep
  duplicate app links plus `Mina körningar`/`Dokumentkonvertering` out of
  persistent nav. `ST-37-03` is now done with retained shared-auth proof at
  `.artifacts/playwright-pr-0365-authenticated-shell-navigation/20260619T212625Z/`.
- `PR-0364` is done and approved by `REV-PR-0364`; detailed proof and
  post-deploy correction history was compacted to
  `.codex/long-term-memory/entries/session-2026-06-19-pr-0364-auth-home-proof-compaction.md`.
  Keep the authenticated-home app symbols from
  `frontend/apps/skriptoteket/src/components/home/homeWorkApps.ts`.
- `PR-0366` through `PR-0373` app presentation, public landing, registry, and
  dev-stack proof history is compacted to
  `.codex/long-term-memory/entries/session-2026-06-23-st-37-04-handoff-compaction.md`.
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
- `PR-0375` is created:
  `docs/backlog/prs/pr-0375-st-37-04-document-converter-backend-backed-mvp-planning.md`
  keeps Document Converter inert until a real backend-backed MVP, Sir Convert
  contract, artifact/download/save/replay semantics, and shared-auth proof plan
  are reviewed.
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
## Verification
- Current local shared-auth runtime as of PR-0368 implementation:
  - HuleEdu Gateway container `huleedu_api_gateway_service` healthy on
    `http://localhost:8080`.
  - Skriptoteket Docker service `skriptoteket_web` running and reachable from
    Gateway as `http://skriptoteket-web:8000`.
  - HuleEdu login UI listens on `:5174`; Skriptoteket Vite listens on `:5173`
    via the repaired `pdm run fe-dev-shared-auth` PDM env map.
- Gateway-to-Skriptoteket Docker check passed:
  `docker exec huleedu_api_gateway_service curl -sS -i --max-time 10 http://skriptoteket-web:8000/healthz`.
- PR-0365 / PR-0372 retained browser proof and screenshots are recorded in
  their PR/review docs and artifact directories; keep the Docker-service proof
  lane intact for authenticated surfaces.
  - PR-0368/PR-0374 detailed red/green/live proof history is compacted to
    `.codex/long-term-memory/entries/session-2026-06-23-st-37-04-handoff-compaction.md`.
  - PR-0376 implementation:
    `pdm run transcript-parity-proof remote-proof` is the normal launcher for
    the retained Audio Transcription transcript parity proof. It validates the
    fenced Sir Convert remote-proof lane on `38085` before invoking the retained
    `scripts/audio_transcription_parity_live.py` Playwright proof. If
    `http://127.0.0.1:38085/readyz` is initially unreachable, it opens an owned
    `ssh -M -S <run-dir>/remote-proof-ssh.sock ... -L 38085:127.0.0.1:38085 hemma`
    tunnel and later stops only that control-socket tunnel; if the endpoint is
    already reachable, it does not open or stop a tunnel. Launcher artifacts are
    written under `.artifacts/transcript-parity-proof-lane/`; new proof artifacts
    are written under `.artifacts/audio-transcription-parity-live/`. Review-fix
    pass restores HuleEdu Gateway and Skriptoteket `web`/`worker` without
    proof-lane overlay env after success or proof failure; HuleEdu restore,
    Skriptoteket restore when those services were actually sent through
    proof-lane recreate, and owned tunnel teardown are attempted independently.
    Skriptoteket web/worker mutation and restore use the supported
    selected-service wrapper: `pdm run dev-stack recreate web worker`. HuleEdu
    `run-local-pdm` calls are invoked with a cross-repo sanitized env so they do
    not inherit Skriptoteket PDM/venv/PYTHONPATH state. After Gateway recreate,
    the launcher treats `pdm run run-local-pdm auth-integration check --timeout-seconds 15`
    as a bounded readiness wait with three attempts before Skriptoteket
    proof-lane mutation or proof upload; persistent auth failure restores
    HuleEdu and any owned tunnel without running Skriptoteket restore. On launcher failure,
    inspect `.artifacts/transcript-parity-proof-lane/<timestamp>/failure-summary.json`
    for bounded/redacted child-command output and cleanup diagnostics.
  - PR-0377 implementation:
    Active reusable proof scripts now use domain module names:
    `scripts/audio_transcription_parity_live.py`,
    `scripts/authenticated_app_identity_split.py`,
    `scripts/authenticated_home_work_apps.py`, and
    `scripts/authenticated_shell_navigation.py`. Historical retained
    `.artifacts/playwright-pr-*` evidence directories were not deleted.
    Active proof summary metadata uses
    `proof_kind=audio_transcription_parity_live`.
  - PR-0378 red/green:
    `pdm run test tests/unit/scripts/test_transcript_parity_proof_launcher.py -k "runtime_evidence"`
    failed red because no container evidence commands ran before cleanup, then
    passed green; review-fix JSON-log secret redaction also failed red, then
    passed green with 2 selected tests. `pdm run test tests/unit/scripts/test_dev_stack.py tests/unit/scripts/test_transcript_parity_proof_launcher.py`
    passed with 24 tests, and the adjacent proof-script suite passed with
    36 tests. `pdm run transcript-parity-proof remote-proof` passed on
    2026-06-23 with launch artifact
    `.artifacts/transcript-parity-proof-lane/20260623T064940Z/` and proof
    artifact `.artifacts/audio-transcription-parity-live/20260623T065005Z/`.
    The proof recorded `status=passed`, `service_profile=remote-proof`,
    matching Gateway/trusted fingerprints, transcript success, formatter
    exports, downloads, and Mina filer save. Cleanup restored Gateway to
    `http://host.docker.internal:8085`, Skriptoteket web/worker to
    `http://host.docker.internal:28085`, and closed local `38085`.
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

# Focused ST-37-04 checks.
pdm run fe-test -- --run src/router/routes.spec.ts src/App.spec.ts src/views/apps/ExamConverterAuthenticatedView.modeRoute.spec.ts src/views/apps/conversionHubModeRoute.spec.ts src/views/HomeView.spec.ts src/components/layout/AuthSidebar.spec.ts
pdm run test tests/unit/test_docker_dev_shared_auth_contract.py
pdm run test tests/unit/scripts/test_playwright_script_surface.py
pdm run test tests/unit/scripts/test_audio_transcription_parity_progress_snapshot.py tests/unit/scripts/test_audio_transcription_parity_summary_truthfulness.py tests/unit/scripts/test_sir_convert_trust_lane_preflight.py
pdm run test tests/unit/scripts/test_transcript_parity_proof_launcher.py
pdm run transcript-parity-proof remote-proof
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
- If PR-0364/PR-0365 preflight fails with `missing_identity_projection`, first
  verify the export path. The running HuleEdu auth-integration lane currently
  matches
  `/Users/olofs_mba/Documents/Repos/huleedu/.artifacts/skriptoteket-auth-bootstrap/local-shared-verify-export.json`;
  `local-verify-export.json` targets a different Identity DB generation and
  reproduces a false `identity_linking_required` failure.
- If Gateway `:8080` appears occupied by Docker while no container publishes
  it, suspect stale Docker Desktop port-proxy state; restart Docker Desktop and
  recreate the affected HuleEdu services before blaming app code.
- `REV-PR-0363` is approved. Keep the Docker-service proof lane intact for
  `PR-0364` and `PR-0365`.
## Next Steps
- Start `PR-0375` when ready to plan the real Document Converter MVP; do not
  create a Document Converter route, host, registry capability, runtime link,
  or proof target before that planning package is approved.
- Continue with `PR-0369` backend/API contract review only if a concrete
  route-visible or Document Converter planning finding proves it is needed.
- `PR-0277` remains open for `REV-PR-0277` plus fresh Teams unfurl proof.
