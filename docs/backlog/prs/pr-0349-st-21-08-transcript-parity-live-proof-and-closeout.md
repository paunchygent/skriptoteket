---
type: pr
id: PR-0349
title: "ST-21-08 Transcript parity live proof and closeout"
status: blocked
owners: "agents"
created: 2026-06-13
updated: 2026-06-13
stories:
  - "ST-21-08"
tags:
  - proof
  - browser
  - gateway
  - transcript
  - formatter
  - user-files
dependencies:
  - "PR-0344"
  - "PR-0345"
  - "PR-0346"
  - "PR-0347"
  - "PR-0348"
  - "HuleEdu TASK-0676"
  - "Sir Convert task-361"
acceptance_criteria:
  - "Given a teacher uploads large source media, when the multipart transfer is still in flight before Sir Convert returns a job id, then the transcript lane shows upload progress and allows local upload abort instead of appearing silent."
  - "Given a signed-in teacher uses the transcript lane through the HuleEdu browser-session ceremony, when a long-running job is submitted, then retained evidence shows truthful progress fields rendering through Gateway."
  - "Given cancel is requested for a running transcript job, when the product receives the abort outcome, then retained evidence shows clear cancel feedback and no invalid follow-up action."
  - "Given a saved transcript has speaker names, when TXT, Markdown, VTT, and SRT are exported, then retained evidence proves exported artifacts use overlay display names and do not fall back to `speaker_00` labels."
  - "Given overlay-aware artifacts are available, when download and save to Mina filer are used, then retained evidence proves both actions work through authorized artifact references."
  - "Given the parity proof closes, when docs and handoff are updated, then ST-21-08 records what is done and any future search/sharing/indexing work remains separate."
---

# PR-0349: ST-21-08 Transcript Parity Live Proof And Closeout

## Problem

The transcript lane spans three repos and cannot be considered parity-complete
without authenticated product evidence.

## Goal

Retain end-to-end proof for progress, cancel feedback, speaker overlays,
overlay-aware exports, downloads, and Mina filer saves.

## Non-goals

- No identity fallback, Sir Convert browser bypass, or direct product-backend
  credential shortcut.
- No direct Sir Convert browser proof.

## Implementation Plan

- Use the HuleEdu browser-session ceremony and repo proof helpers.
- Surface the pre-job multipart upload phase with upload progress and local
  upload abort so large files do not look like a silent conversion wait.
- Run a fresh transcript job and capture progress rendering.
- Exercise cancel feedback on a controlled job where cancellation is valid.
- Save canonical transcript JSON, name speakers, replay formatter exports, and
  verify TXT/Markdown/VTT/SRT artifact content uses display names.
- Download each artifact and save at least one representative artifact to Mina
  filer.
- Update ST-21-08, EPIC-21, reviews if created, `.codex/handoff.md`, and the
  development changelog as required by the repo.

## Test Plan

- Authenticated browser proof with retained sanitized artifacts.
- Focused frontend tests for upload progress, upload abort, and visible
  pre-job upload state.
- Focused regression tests touched by proof harness adjustments.
- Full docs/handoff validation and `git diff --check`.

## Evidence Log

### 2026-06-13 Cross-Repo Smoke And Blocked Live Proof Rerun

HuleEdu `TASK-0676` and Sir Convert `task-361` are approved upstream
dependencies for this closeout. The cross-repo trust-profile smoke is green,
but the live product proof still blocks at the runtime Sir Convert
internal-identity verifier:

- HuleEdu retained review approved `TASK-0676`:
  `/Users/olofs_mba/Documents/Repos/huleedu/docs/backlog/reviews/review-task-0676-01-ruthless-review-task-0676-internalidentitycontextv1-trust-profile.md`.
- Sir Convert retained review approved `task-361`:
  `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/backlog/reviews/review-46-ruthless-review-task-361-huleedu-internalidentitycontextv1-trust-profile-consumption.md`.
- HuleEdu profile publisher passed for `local-auth-integration` and
  `hemma-production`:
  `pdm run run-local-pdm hemma-sir-convert-internal-identity-trust-profile --environment local-auth-integration`
  and
  `pdm run run-local-pdm hemma-sir-convert-internal-identity-trust-profile --environment hemma-production`.
  Both emitted sanitized profile metadata with canonical DER SPKI fingerprint
  `46aefc0edc2f71267e2df783ca27f4df2b0da269cc7e84b43cbe2de6ac7c1992`.
- Sir Convert approved Task 361 smoke passed:
  `pdm run pytest-root tests/sir_convert_a_lot/test_huleedu_internal_identity_trust_profile_v1.py tests/sir_convert_a_lot/test_structured_llm_settings_route_v2.py tests/sir_convert_a_lot/test_digiexam_migration_access_control_api_v2.py tests/sir_convert_a_lot/test_compose_contract.py tests/sir_convert_a_lot/test_local_compose_contract.py -q`
  with `39 passed`.

- HuleEdu shared PostgreSQL migrations verified at Alembic head for
  `batch_orchestrator_db`, `essay_lifecycle_db`, `cj_assessment_db`,
  `class_management_db`, `file_service_db`, `file_service_content_db`,
  `spellchecker_db`, `result_aggregator_db`, `nlp_db`,
  `batch_conductor_db`, `identity_db`, `email_db`, and `entitlements_db`:
  `HULEEDU_ENV_OVERLAY_FILE=output/tmp/pr0349-shared-postgres-migrations.env pdm run run-local-pdm db-lifecycle verify --all`.
- Skriptoteket dev DB migration state upgraded cleanly:
  `pdm run dev-stack db-upgrade`.
- Canonical local stacks were healthy:
  `HULEEDU_ENV_OVERLAY_FILE=output/tmp/pr0349-sir-convert-tunnel.env pdm run run-local-pdm auth-integration check`
  and `pdm run dev-stack ps`.
- Gateway was corrected from the closed default `host.docker.internal:8085` to
  the canonical tunnel backend `http://host.docker.internal:28085` through the
  HuleEdu env-overlay + `dev-recreate api_gateway_service` path. Container-side
  `/readyz` to that backend returned ready.
- A focused red/green harness remediation added blocked-run summary tests.
  Red evidence:
  `pdm run test tests/unit/scripts/test_playwright_pr_0349_summary_truthfulness.py`
  failed before implementation because the finalizer functions did not exist.
  Green focused command:
  `pdm run test tests/unit/scripts/test_playwright_pr_0349_summary_truthfulness.py tests/unit/scripts/test_playwright_script_surface.py tests/unit/scripts/test_conversion_hub_transcript_docs_guard.py`
  passed with `8 passed`.
- Retained browser proof artifact after the remediation:
  `.artifacts/playwright-pr-0349-transcript-parity-live/20260613T153843Z/proof-summary.json`.
  The summary keeps `status=failed` and now records the typed
  `sir_convert_internal_identity_rejected` object as the primary `failure`;
  the generic Playwright timeout is retained only as `raw_failure`.
- The artifact manifest now lists only captured files:
  `network.bounded.json`, `browser-console.bounded.json`, and `failure.png`.
- Retained network evidence:
  `.artifacts/playwright-pr-0349-transcript-parity-live/20260613T153843Z/network.bounded.json`
  records `POST /sir-convert/v2/convert/jobs?wait_seconds=0` as HTTP `401`
  with `error_code=auth_invalid_internal_identity` and
  `reason=invalid_internal_identity_signature`.
- Read-only Hemma/Sir Convert verification showed the local HuleEdu public-key
  fingerprint `b1e569219f6045be01bd89a1907e515c9a9d5c2e800bc2dacf593027a3d7b4b2`
  does not match the Sir Convert prod trusted public-key fingerprint
  `db96ea08a821bb9eb8a7fbd24ca9f5730834f5018af945b1a1200118c9e11f63`.

### Acceptance State

- Signed-in teacher reaches the transcript lane through the HuleEdu
  browser-session ceremony: proven locally before submit.
- Truthful progress rendering through Gateway: not proven; submit is rejected
  before a job exists.
- Cancel feedback on a valid controlled job: not proven; no cancellable job is
  created after the rejected submit.
- Save canonical transcript JSON: not proven in this PR-0349 run.
- Rename speakers via saved transcript overlay UI/API: not proven in this
  PR-0349 run.
- Replay export TXT, Markdown, VTT, and SRT: not proven in this PR-0349 run.
- Exported artifact content overlay-label check: not proven in this PR-0349
  run.
- Download overlay-aware artifacts and save representative artifact to Mina
  filer: not proven in this PR-0349 run.

The signer/trust mismatch above is historical evidence only. Do not treat that
earlier `401 auth_invalid_internal_identity` proof as the current `PR-0349`
blocker.

### 2026-06-13 Post-Trust Upload/Admission RCA And Remediation

After the HuleEdu/Sir Convert trust-profile fix was deployed to Hemma, the
production transcript submit no longer failed at internal identity
verification. HuleEdu Gateway forwarded the signed request and Sir Convert
accepted it, but the first `POST /v2/convert/jobs?wait_seconds=0` response
headers arrived only after the multipart submit path completed. Retained logs
showed fresh submit-response latencies around `35.232s` and `34.080s` for the
16 MiB proof fixture, while Gateway's previous 30-second outbound read timeout
returned `502 EXTERNAL_SERVICE_ERROR` before Sir Convert's response reached
Skriptoteket.

That was not a 34-second conversion-processing wait. Sir Convert's production
public API lane is enqueue-only (`RUN_JOBS_ON_SUBMIT=0`), and
`wait_seconds=0` does not long-poll for conversion completion. The root cause
was that the browser product treated multipart upload transfer and admission as
an invisible part of "job creation." For large source media, the browser cannot
receive a Sir Convert job id until the browser -> Gateway -> Sir Convert
multipart body has transferred and Sir Convert has parsed enough of the
request to admit the job. A 500 MiB upload can therefore plausibly spend
minutes before the first job response unless upload is represented as its own
user-visible phase.

Remediation in this PR-0349 slice:

- `submitTranscriptJob` now supports a typed multipart upload transport with
  `onUploadProgress` and `AbortSignal` for the transcript upload path.
- The browser client uses `XMLHttpRequest.upload.onprogress` for multipart
  transcript submits when upload progress or abort is requested; other Gateway
  calls keep the existing `fetch` path.
- `useTranscriptGatewayRuntime` now exposes a pre-job `uploadState`, resets it
  after Sir Convert returns a job id, and aborts the local upload when cancel is
  pressed before a job id exists.
- `TranscriptWorkspaceShell` renders the upload phase and byte/percent progress
  before Sir Convert progress fields exist, then renders the existing queued /
  transcribing / diarizing progress once a job is admitted.
- The live proof script now accepts truthful cancel evidence from either a
  Sir Convert `/cancel` response after job admission or a local `upload_abort`
  before job admission.
- The live proof script copies the fixture to per-run cancel/main filenames
  under the retained artifact directory so deterministic idempotency does not
  replay an already-terminal job on repeated proof attempts.

Focused validation:

- `pdm run fe-test -- --run frontend/apps/skriptoteket/src/api/sirConvertGateway/transcriptClient.spec.ts frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/useTranscriptGatewayRuntime.spec.ts frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/TranscriptWorkspaceShell.spec.ts frontend/apps/skriptoteket/src/views/apps/ConversionHubTranscriptMode.spec.ts`
  passed with `30 passed`.
- `pdm run fe-type-check` passed.
- `pdm run test tests/unit/scripts/test_playwright_pr_0349_summary_truthfulness.py`
  passed with `2 passed`.
- `pdm run python -m py_compile scripts/playwright_pr_0349_transcript_parity_live.py`
  passed.
- `git diff --check` passed.

### 2026-06-13 Replay/Export Disabled RCA And Client Remediation

Latest retained artifact:
`.artifacts/playwright-pr-0349-transcript-parity-live/20260613T181847Z/`.

After the HuleEdu/Sir Convert trust-profile remediation landed, the sanctioned
Hemma browser-session path progressed through upload, truthful running
progress, cancel, durable transcript save, and saved-transcript readback. The
new blocker was inside Skriptoteket client state, not in InternalIdentity,
SHA/fingerprint alignment, or Sir Convert replay backend behavior:

- `.artifacts/playwright-pr-0349-transcript-parity-live/20260613T181847Z/proof-summary.json`
  shows transcript upload, cancel, progress, and save succeeded before the run
  failed waiting for
  `[data-test="transcript-formatter-replay-button"]` to become enabled.
- `.artifacts/playwright-pr-0349-transcript-parity-live/20260613T181847Z/network.bounded.json`
  records `GET .../speaker-overlays` with `overlay_count=0`, then `PUT
  .../speaker-overlays` with `overlay_count=0`, and no
  `/formatter-replay/prepare` or `/formatter-replay/complete` requests.
- The retained `failure.png` shows the false-success UI state:
  `Talarnamn sparade.` and `Exportfiler kan skapas.` were rendered while the
  replay button stayed disabled and transcript segments still displayed
  `SPEAKER_00` / `SPEAKER_01`.

RCA:

- `ConversionHubTranscriptHost.vue` set `savedTranscriptId` / `saveStatus`
  before the initial `loadSpeakerOverlays()` request completed. That rendered
  editable overlay inputs while the background `GET /speaker-overlays` was
  still in flight.
- If the teacher or retained proof typed names during that load, the later
  empty `GET /speaker-overlays` response overwrote the newer browser-local
  entries.
- `handleSaveSpeakerOverlays()` then accepted an empty persisted overlay list
  and still marked `speakerOverlayStatus='saved'`, which made the panel claim
  export files could be created even though `canRequestFormatterReplay` stayed
  false because `speakerOverlayEntries.length === 0`.

Remediation in this slice:

- `ConversionHubTranscriptHost.vue` now waits for the initial
  `loadSpeakerOverlays()` readback before marking the transcript save complete
  and rendering editable speaker inputs, so the background load cannot clobber
  new local edits.
- Empty `PUT /speaker-overlays` responses now leave
  `speakerOverlayStatus='idle'` instead of false `saved` success.
- `TranscriptFormatterReplayPanel.vue` now renders truthful idle copy:
  `Spara talarnamnen innan exportfiler skapas.` whenever replay is still
  disabled.
- `ConversionHubTranscriptHost.spec.ts` adds DOM-first proof for the race,
  empty-overlay false-success state, and replay enablement only after non-empty
  persisted overlays.

Focused validation:

- Red:
  `pdm run fe-test -- --run frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/ConversionHubTranscriptHost.spec.ts frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/TranscriptWorkspaceShell.spec.ts`
  failed with 2 host-spec assertions before the patch:
  overlay inputs rendered before readback completed, and empty overlay saves
  still showed `Talarnamn sparade.`.
- Green:
  that same command passed with `12 passed`.
- `pdm run fe-type-check` passed.

### 2026-06-13 Formatter Replay Prepare Segment-Extraction RCA

Latest retained artifact:
`.artifacts/playwright-pr-0349-transcript-parity-live/20260613T194529Z/`.

The client-state remediation above worked: the live proof progressed through
upload/STT, transcript save, initial overlay readback, and persisted speaker
overlays. The next blocker was backend replay preparation, not identity,
fingerprint trust, overlay persistence, or the Sir Convert replay backend:

- `proof-summary.json` records `save_transcript.status=200`,
  `transcript_json.segment_count=27`, `transcript_json.speaker_label_count=2`,
  and `speaker_overlays.status=200` with `overlay_count=2`.
- `network.bounded.json` records `POST
  /api/v1/apps/documents.conversion_hub/transcripts/{id}/formatter-replay/prepare`
  returning HTTP `422`, `error_code=VALIDATION_ERROR`, message
  `Transcript JSON must contain at least one segment.`
- No `/formatter-replay/complete` request was sent because the proof was
  waiting for the prepare response.

RCA:

- Transcript save validation accepted the saved transcript payload by checking
  canonical segments with the save contract: prefer `transcript.segments` when
  present, otherwise accept top-level `segments`.
- Formatter replay prepare had its own stricter speaker-label extractor and
  only inspected `transcript.segments` after resolving the nested `transcript`
  object.
- A transcript JSON shape accepted and persisted by save could therefore be
  rejected later by replay prepare even though it had non-empty segments,
  speaker labels, text, timestamps, and persisted overlays.

Remediation in this slice:

- Added `conversion_hub_transcript_json_contract.py` as the shared
  application-handler contract for strict, non-empty transcript segment and
  canonical speaker-label extraction.
- Wired transcript save, speaker overlay validation, and formatter replay
  prepare to the shared extractor so saved transcript shapes cannot diverge
  before replay.
- Kept fail-closed validation for empty or missing segments, invalid segment
  objects, missing speaker labels, missing text, and invalid timestamps.
- Added a red-first regression test that saves a top-level `segments`
  transcript, persists two overlays, and prepares formatter replay from that
  saved record.

Focused validation:

- Red:
  `pdm run test tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_replay_saved_shapes.py`
  failed before the production patch with `Transcript JSON must contain at
  least one segment.`
- Green:
  the same command passed with `1 passed`.
- `pdm run test tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_replay_saved_shapes.py tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_replay.py tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_saves.py tests/unit/web/conversion_hub/test_apps_conversion_hub_transcript_saves_api.py`
  passed with `22 passed`.
- `pdm run typecheck` passed.

### 2026-06-13 Formatter Replay Complete Result-Envelope RCA

Latest retained artifact:
`.artifacts/playwright-pr-0349-transcript-parity-live/20260613T201049Z/`.

The replay-prepare remediation above worked. The live proof progressed through
saved transcript readback, persisted `overlay_count=2`, successful
`/formatter-replay/prepare`, successful Sir Convert replay submit, and
successful Sir Convert replay artifact listing for exactly `transcript_txt`,
`transcript_md`, `transcript_vtt`, and `transcript_srt`. The new blocker was
Skriptoteket completion parsing:

- `network.bounded.json` records `POST
  /api/v1/apps/documents.conversion_hub/transcripts/{id}/formatter-replay/complete`
  returning HTTP `503`, `error_code=SERVICE_UNAVAILABLE`, message
  `Sir Convert replay result is malformed.`
- The preceding Sir Convert replay job succeeded with HTTP `200`.
- The preceding Sir Convert replay artifact manifest succeeded with HTTP `200`
  and exactly the four requested formatter artifact keys.

RCA:

- Sir Convert `/v2/convert/jobs/{job_id}/result` returns the normal Service API
  v2 result envelope: `api_version`, `job_id`, `status`, and
  `result.warnings` wrap the strict replay `result.artifact` and
  `result.conversion_metadata`.
- Skriptoteket completion parsing modeled only a bare `{result: ...}` object
  with `extra="forbid"`.
- The valid Service API v2 envelope was therefore rejected before persisted
  local replay job/artifact refs could be written.
- This is not identity/fingerprint trust, overlay persistence, replay prepare,
  or replay execution; those stages had already succeeded in the retained live
  proof.

Remediation in this slice:

- `parse_replay_result` now accepts the real Service API v2 replay result
  envelope and requires `api_version=v2`, `status=succeeded`, strict replay
  artifact metadata, strict replay conversion metadata, and `warnings` as a
  list of strings.
- The parser now validates that the `/result` envelope `job_id` matches the
  completion request `sir_convert_job_id` before artifact refs are persisted.
- Artifact manifest parsing remains strict: requested artifact keys must be
  present as available producer refs with correct content type, size, digest,
  and retrieval path, and malformed, duplicate, unknown, unavailable, or
  missing artifacts still fail closed.

Focused validation:

- Red:
  `pdm run test tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_replay_result_envelope.py`
  failed before the patch because the valid Service API v2 fields
  `api_version`, `job_id`, `status`, and `result.warnings` were rejected as
  extra inputs.
- Changes-requested red:
  the same focused test module failed before the follow-up parser patch because
  missing `result.warnings` did not raise `DomainError` and allowed replay
  completion to persist.
- Green:
  `pdm run test tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_replay_result_envelope.py tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_replay.py`
  passed with malformed coverage for missing/non-list warnings, wrong result
  status, malformed artifact metadata, and malformed conversion metadata.

### 2026-06-13 Formatter Artifact Download RCA

Latest retained artifact:
`.artifacts/playwright-pr-0349-transcript-parity-live/20260613T203933Z/`.

The replay-complete parser remediation above worked. The live proof reached
upload/STT/save, initial overlay readback, persisted overlay save, replay
prepare, Sir Convert replay submit, Sir Convert replay result, Sir Convert
artifact listing, and Skriptoteket replay completion. The remaining blocker was
artifact download:

- `network.bounded.json` records `GET
  /api/v1/apps/documents.conversion_hub/transcripts/{id}/formatter-artifacts/transcript_txt/download`
  returning HTTP `503`, message `Failed to download named v2 artifact.`
- Browser console records only the same backend `503`; this was not a
  Playwright download timeout.
- The persisted artifact ref came from the Sir Convert artifact listing, so the
  producer ref itself existed and passed Skriptoteket manifest validation.

RCA:

- Replay jobs and artifact listing are created through the HuleEdu Gateway
  while the browser session carries the teacher owner identity.
- Skriptoteket later tried to download the named Sir Convert artifact directly
  from the backend using only its server-side transport identity.
- Sir Convert named artifact reads are owner-scoped. API-key transport is not a
  substitute for the browser-session owner that produced the artifact.
- The contract mismatch was therefore between the producer context that listed
  and persisted the artifact ref and the consumer context used for backend
  download/save actions.

Remediation in this slice:

- The frontend now requires a HuleEdu Gateway artifact receipt on each selected
  replay artifact download before `/formatter-replay/complete`.
- Skriptoteket completion no longer trusts a browser-posted artifact manifest.
  Artifact refs are derived from backend-verified HuleEdu detached RS256
  receipts over job id, artifact key, content type, size, SHA-256, retrieval
  path, issuer, audience, subject, and TTL.
- Browser-forwarded bytes are accepted only as a transport cache after receipt
  verification, exact key matching, content-type matching, byte-size matching,
  SHA-256 matching, and per-artifact plus total replay byte-budget checks.
- Backend download and Mina save now serve only those validated persisted bytes;
  ref-only rows fail closed.
- The direct backend Sir Convert artifact download dependency was removed from
  transcript formatter artifact actions, preserving owner provenance instead of
  adding an API-key identity fallback.

Focused validation:

- Red:
  `pdm run test tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_artifact_payloads.py`
  initially reproduced the live failure as `DomainError: Failed to download
  named v2 artifact.` when the action still attempted a direct backend producer
  read.
- Green:
  focused application-handler tests now reject unsigned self-consistent browser
  payloads, reject malformed payloads and byte-budget breaches, then complete a
  signed-receipt replay, persist validated bytes, and download/save to Mina.
- Green:
  focused frontend tests verify Gateway artifact receipt headers are required
  and included with base64 payloads in replay completion.

### 2026-06-13 Artifact Receipt Re-Review Remediation

The re-review found that the first payload-persistence remediation still trusted
browser self-consistency: `artifact_manifest` and `artifact_payloads` arrived in
the same completion request. A forged but internally consistent payload could
therefore be persisted as a producer artifact.

The remediation now preserves the invariant that producer-owned artifact bytes
must be fetched in the same owner authority lane or be bound to backend-
verifiable delegated authority:

- `/formatter-replay/complete` no longer accepts `artifact_manifest`.
- Each artifact payload must include a HuleEdu-signed receipt with
  `schema_version=huleedu.sir_convert_artifact_receipt.v1` and
  `aud=skriptoteket`.
- The backend verifies the detached RS256 signature against the configured
  HuleEdu internal identity trust keys before deriving artifact refs or
  persisting bytes.
- Missing/forged receipts, bad base64, duplicate/missing keys, content-type
  mismatch, size mismatch, checksum mismatch, over-budget payloads, and
  ref-only rows all fail closed without persisted job/artifact bytes.

Residual: the retained live Gateway artifact download response does not yet
prove these receipt headers exist. Fresh Hemma proof remains blocked until the
Gateway emits the signed receipt contract or a HuleEdu-owned delegated fetch
contract replaces it.

### 2026-06-13 Receipt Subject Binding Re-Review Remediation

The follow-up re-review found that signed receipts were verified but not bound
to the current authenticated HuleEdu projection subject. A receipt for subject A
could therefore be submitted by subject B if the receipt job/key/payload checks
matched B's local replay completion.

Remediation:

- `HuleEduAppUserProjection` now carries the resolved signed
  `realm_subject_id`.
- `/formatter-replay/complete` depends on
  `require_app_user_projection_api`, keeps app access checks on the local
  `User`, and forwards the signed projection subject into the completion
  handler.
- The completion handler rejects every verified artifact receipt whose `sub`
  differs from the current projection subject before deriving artifact refs or
  persisting any job/artifact bytes.
- The fail-closed test covers a real RS256-verified receipt whose `sub` differs
  from the current projection subject and asserts no replay job or artifact rows
  are written.

Focused validation:

- `pdm run test tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_artifact_payloads.py -k different_huleedu_subject`
  passed with `1 passed, 7 deselected`.
- `pdm run test tests/unit/web/conversion_hub/test_apps_conversion_hub_transcript_saves_api.py -k complete_formatter_replay`
  passed with `1 passed, 8 deselected`.
- `pdm run test tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_artifact_payloads.py tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_artifact_actions.py tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_replay.py tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_replay_completion.py tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_replay_result_envelope.py tests/unit/web/conversion_hub/test_apps_conversion_hub_transcript_saves_api.py`
  passed with `33 passed`.
- `pdm run test tests/unit/web/test_profile_app_continuation_api.py tests/unit/web/test_profile_app_continuation_dependencies_api.py tests/unit/web/test_profile_app_continuation_context_api.py`
  passed with `38 passed`.
- `pdm run fe-test -- --run frontend/apps/skriptoteket/src/api/conversionHubTranscriptFormatterReplay.spec.ts frontend/apps/skriptoteket/src/api/sirConvertGateway/transcriptReplayClient.spec.ts`
  passed with `6 passed`.
- `pdm run typecheck`, `pdm run lint`, `pdm run fe-type-check`,
  `pdm run fe-lint`, `pdm run docs-validate`, `pdm run handoff-validate`, and
  `git diff --check` passed.

## Rollback Plan

Leave PR-0344 through PR-0348 behavior intact and keep ST-21-08 open with the
failed proof recorded as the blocker.
