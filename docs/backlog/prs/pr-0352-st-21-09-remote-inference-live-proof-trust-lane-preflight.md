---
type: pr
id: PR-0352
title: "ST-21-09 Remote inference live-proof trust-lane preflight"
status: done
owners: "agents"
created: 2026-06-14
updated: 2026-06-14
stories:
  - "ST-21-09"
tags:
  - proof
  - transcript
  - gateway
  - internal-identity
  - sir-convert
  - devops
dependencies:
  - "PR-0351"
  - "HuleEdu Gateway browser-session ceremony helpers"
  - "Sir Convert hosted model/runtime estate"
acceptance_criteria:
  - "Given the transcript proof uses remote Sir Convert compute, when the proof command starts, then it verifies the resolved proof lane before uploading media or creating a Sir Convert job."
  - "Given the local HuleEdu Gateway signer public-key fingerprint, remote Sir Convert verifier trust profile, or running product-backend producer target does not match the selected proof lane, when the default local proof command is run, then it exits with a typed trust-lane blocker before media upload or Sir Convert job submission."
  - "Given the default proof needs real Sir Convert hosted model/runtime compute, when local machine resources are considered, then the default uses a coherent remote-inference lane and does not require local hosting of STT, diarization, alignment, OCR/vision, LLM/enrichment, correction/replay, or future heavy model workers."
  - "Given a future agent intentionally uses a local Gateway to Hemma Sir Convert tunnel, when the mixed lane is selected, then the command requires an explicit opt-in flag plus verified public fingerprint/profile agreement before allowing upload."
  - "Given the preflight writes proof artifacts or console output, when trust-lane metadata is recorded, then it includes only redacted public configuration and public-key fingerprints, never private keys, tokens, cookies, passwords, transcript text, or source media content."
  - "Given implementation is complete, when review runs, then `REV-PR-0352` verifies the old ad hoc session guidance is replaced by enforced defaults, red-first tests, and governed docs."
---

# PR-0352: ST-21-09 Remote Inference Live-Proof Trust-Lane Preflight

## Problem

Transcript completion proof currently needs real Sir Convert speech-to-text,
diarization, and alignment compute, and other Conversion Hub proof paths may
need OCR/vision, LLM/enrichment, correction/replay, or future hosted
producer-model workers. Local machines should not be expected to host that
Sir Convert model/runtime estate.

The unsafe default is the mixed lane that has recurred during implementation:
local Skriptoteket and a local HuleEdu Gateway sign requests with a mutable
gitignored local internal identity, while Sir Convert is actually a Hemma/prod
remote service reached through a tunnel. If the local signer and Hemma verifier
trust profiles drift, Sir Convert rejects the request with
`auth_invalid_internal_identity` /
`invalid_internal_identity_signature` only after the proof is already underway.

The 2026-06-14 `PR-0351` local proof failures prove this is not maintainable as
session advice. Docker-backed evidence later pinned the concrete local blocker:
the proof and remote compute lane used `host.docker.internal:28085`, while the
running `skriptoteket_web` container still had
`SIR_CONVERT_A_LOT_V2_BASE_URL=http://host.docker.internal:8085`. The command
must know the lane before it starts, and the running product backend must be
verified before upload or producer submission.

## Goal

Make transcript live-proof lane coherence executable and default:

- heavy Sir Convert hosted model/runtime compute remains remote by default;
- the proof command preflights signer/verifier trust before upload;
- the proof command verifies the running local product-backend producer target
  before upload;
- local UI/backend proof either uses a sanctioned remote-inference proof lane
  with coherent trust or fails closed;
- a local-Gateway to Hemma-Sir-Convert tunnel is debug-only and explicit;
- failure artifacts explain the trust-lane blocker without exposing secrets.

## Non-goals

- No local Sir Convert model/runtime stack as the default proof requirement,
  including STT, diarization, alignment, OCR/vision, LLM/enrichment,
  correction/replay, or future hosted-model workers.
- No copying Hemma private keys, production signing material, cookies, tokens,
  or passwords into local runtime secrets.
- No direct browser Sir Convert proof or browser-visible upstream credentials.
- No bypass of the HuleEdu browser-session ceremony.
- No broad rework of transcript UI, export UX, or PR-0351 behavior.

## Implementation Plan

1. Use the testing skill before writing tests. Add red-first tests for the
   current regression class in a focused script/preflight test module.
2. Extract a small proof-lane preflight helper for
   `scripts.playwright_pr_0349_transcript_parity_live` with a top-level Google
   docstring describing its domain purpose and relationships.
3. Resolve the active lane from the same inputs the proof command uses:
   `--base-url`, dotenv path, HuleEdu Gateway target, Sir Convert backend
   readiness metadata, and public signer/verifier trust-profile metadata.
4. Fail before media upload or job creation when the lane is incoherent, with a
   typed blocker such as `sir_convert_trust_lane_mismatch`.
5. Make the default documented completion-path proof use coherent remote
   inference:
   - production/Hemma browser-session proof for Hemma compute; or
   - a named remote proof gateway lane whose signer is trusted by the remote
     Sir Convert verifier.
6. Keep local-Gateway to Hemma-Sir-Convert tunnel support only behind an
   explicit debugging flag, and still require matching public
   fingerprint/profile verification.
7. Persist proof-lane guidance in the relevant runbook/docs and
   `.codex/handoff.md`; remove or soften stale wording that implies agents
   should manually "repair the local trust lane" from memory.
8. Create `REV-PR-0352` and run independent review before marking done. The
   implementer and reviewer must not be the same agent.

## Implementation Summary

Implementation is complete, live-proofed locally and natively on Hemma
production, and approved by independent `REV-PR-0352`.

- Added `scripts/_sir_convert_trust_lane_preflight.py` as the proof-lane
  preflight module. It resolves public lane metadata from CLI, environment,
  dotenv, and optional readyz metadata; allows production/Hemma remote proof by
  default; requires explicit opt-in for local-Gateway to Hemma-Sir-Convert
  tunnel debugging; and requires matching public signer/verifier fingerprints
  before any mixed tunnel upload may proceed.
- Updated `scripts/playwright_pr_0349_transcript_parity_live.py` to run the
  preflight before copying source media or launching Playwright. It also
  captures Docker-backed local product-backend evidence and blocks if the
  running `web` container producer lane differs from the verified proof lane.
  A preflight blocker writes a redacted `proof-summary.json` and exits with the
  blocker kind, for example `sir_convert_trust_lane_unresolved`,
  `sir_convert_trust_lane_mismatch`, or
  `sir_convert_running_producer_lane_mismatch`.
- Added focused unit tests in
  `tests/unit/scripts/test_sir_convert_trust_lane_preflight.py` for mismatch
  blocking, explicit mixed-tunnel opt-in, successful matching debug lane,
  production/Hemma remote proof allowance, redacted failure summaries, and the
  full script exit path proving no media copy occurs before either a resolved
  preflight blocker or a running-container producer-lane mismatch.
- Added `scripts/_proof_live_monitoring.py` and extended sanitized evidence
  summaries so retained local proof artifacts include `backend-container.json`,
  `backend-live.log`, and `backend-monitor.json`. The 2026-06-15 follow-up also
  makes native Hemma production proof capture safe `service-monitoring.json`
  plus bounded `service-logs/*.log` for the proof interval across Skriptoteket,
  HuleEdu Gateway/auth, and Sir Convert containers, without retaining container
  environment variables.
- Closed the downstream async formatter-export consumer gap exposed by the
  production proof path: `SirConvertTranscriptFormatterProducerV2` now accepts
  `202 Accepted`, polls `GET /v2/convert/jobs/{job_id}` until terminal state,
  and only then reads result/artifact bytes. Red-first coverage lives in
  `tests/unit/infrastructure/curated_apps/apps/conversion_hub/test_sir_convert_transcript_formatter_producer.py`.
- Kept remote hosted model/runtime compute as the normal proof assumption; no
  local Sir Convert model/runtime stack or secret-copy path was introduced.

## Red-First Test Plan

Add tests before production code that prove:

- a local signer fingerprint pointed at a remote Hemma/Sir Convert verifier
  fingerprint is rejected before any upload/job-submit function is called;
- a running local product-backend container pointed at a stale producer URL is
  rejected before proof media is copied;
- matching signer/verifier profile metadata allows the proof to proceed to the
  existing browser proof flow;
- the explicit mixed-lane debug flag is required for local-Gateway to
  Hemma-Sir-Convert tunnel mode;
- preflight output and proof-summary fields include no private key material,
  tokens, cookies, passwords, transcript text, or source media content;
- the existing `auth_invalid_internal_identity` summary classifier remains
  truthful for historical artifacts, but new default runs should report a
  preflight blocker instead of a post-submit upstream rejection.

Red evidence captured before production code:

```bash
pdm run test tests/unit/scripts/test_sir_convert_trust_lane_preflight.py
```

Result: failed during collection with
`ModuleNotFoundError: No module named 'scripts._sir_convert_trust_lane_preflight'`.

Green focused evidence after implementation:

```bash
pdm run test tests/unit/scripts/test_sir_convert_trust_lane_preflight.py
pdm run test tests/unit/scripts/test_sir_convert_trust_lane_preflight.py tests/unit/scripts/test_playwright_pr_0349_summary_truthfulness.py tests/unit/scripts/test_playwright_script_surface.py
pdm run python -m py_compile scripts/_sir_convert_trust_lane_preflight.py scripts/playwright_pr_0349_transcript_parity_live.py
pdm run lint
pdm run typecheck
```

Results:

- `tests/unit/scripts/test_sir_convert_trust_lane_preflight.py`: 20 passed.
- Focused script bundle: 28 passed.
- `py_compile`: passed.
- `pdm run lint`: passed, including format, Ruff, migration coverage, and
  hazard shortcard guard.
- `pdm run typecheck`: passed.

Local live proof after remediation:

```bash
pdm run python -m scripts.playwright_pr_0349_transcript_parity_live --base-url http://127.0.0.1:5173 --dotenv .env --sir-convert-proof-lane hemma-remote-proof --sir-convert-gateway-backend-url http://host.docker.internal:28085 --sir-convert-producer-backend-url http://host.docker.internal:28085 --sir-convert-ready-url http://127.0.0.1:28085/readyz --gateway-signer-fingerprint 46aefc0edc2f71267e2df783ca27f4df2b0da269cc7e84b43cbe2de6ac7c1992 --sir-convert-trusted-fingerprint 46aefc0edc2f71267e2df783ca27f4df2b0da269cc7e84b43cbe2de6ac7c1992 --timeout-seconds 1200
```

Result: passed. Retained artifact:
`.artifacts/playwright-pr-0349-transcript-parity-live/20260614T184817Z/proof-summary.json`.
The proof shows trust-lane preflight passed, remote compute stayed on the
`remote-proof` lane, the completed transcript autosaved, formatter export
returned four artifacts, all four downloads returned `200`, and Mina filer save
returned `200`.

Native Hemma production proof after deploying Sir Convert
`159e82d5e674213ba58d5e2d959e8baba383dadb` and Skriptoteket
`2fa27cfb85c8e64d9d0a9e9fb15c26091a09946e`:

```bash
ssh hemma
cd /home/paunchygent/apps/skriptoteket
/home/paunchygent/.local/bin/pdm run python -m scripts.playwright_pr_0349_transcript_parity_live \
  --audio-file /home/paunchygent/apps/sir-convert-a-lot/build/verification/stt-sidecar-live-fixtures/source-media/english-dialogue-two-speakers.mp3 \
  --base-url https://skriptoteket.hule.education \
  --dotenv .artifacts/proof-env/prod-transcript-20260614T191737Z.env \
  --artifact-root .artifacts/playwright-pr-0352-transcript-parity-native \
  --sir-convert-proof-lane hemma-production \
  --timeout-seconds 1200 \
  --no-capture-local-backend-logs
```

Result: passed. Retained artifact:
`/home/paunchygent/apps/skriptoteket/.artifacts/playwright-pr-0352-transcript-parity-native/20260614T191738Z/proof-summary.json`.
Container-log evidence for the same interval is retained at:
`/home/paunchygent/apps/skriptoteket/.artifacts/pr-0352-native-proof-logs/20260614T191737Z/`.
The retained proof shows `trust_lane_preflight.status=passed`,
`lane_kind=hemma_production`, `remote_compute=true`, `mixed_tunnel=false`,
autosaved `transcript_json_v1` with 27 segments and two speaker labels, two
speaker overlays, formatter export artifact count 4, TXT/MD/VTT/SRT downloads
all `200`, and Mina filer save `200`.

The matching container evidence shows Skriptoteket production returned `200`
for `POST /formatter-exports`, all four formatter-artifact downloads, and
`POST /formatter-artifacts/transcript_txt/save`. Sir Convert production logs
show the STT job accepted as `202`, polled through
`GET /v2/convert/jobs/{job_id}`, result/artifacts read as `200`, formatter
fast lane `transcript_json -> transcript_bundle` completed with
`status=succeeded`, and all four formatter artifacts read as `200`.

Focused commands expected for the implementation slice:

```bash
pdm run test tests/unit/scripts/test_sir_convert_trust_lane_preflight.py
pdm run test tests/unit/scripts/test_playwright_pr_0349_summary_truthfulness.py tests/unit/scripts/test_playwright_script_surface.py
pdm run test tests/unit/infrastructure/curated_apps/apps/conversion_hub/test_sir_convert_transcript_formatter_producer.py tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_exports.py tests/unit/infrastructure/curated_apps/apps/conversion_hub/test_sir_convert_client_v2.py
pdm run lint
pdm run typecheck
pdm run docs-validate
pdm run handoff-validate
git diff --check
```

If the production/Hemma completion proof is rerun, use the HuleEdu
browser-session credential helper without printing secret values and retain the
sanitized artifact path in this PR and handoff.

## Acceptance Proof

The task is not complete until there is retained evidence that:

- the formerly broken local mixed lane is rejected before
  `/sir-convert/v2/convert/jobs` is attempted;
- remote inference remains the normal way to exercise real Sir Convert
  hosted-model work;
- local model/runtime hosting is not introduced as a prerequisite;
- the default proof command or documented wrapper cannot silently re-enter the
  ad hoc mixed trust lane;
- local STT E2E proof passes with retained Docker-backed product-backend
  evidence;
- native Hemma production proof passes after the git-backed changes are
  deployed;
- `REV-PR-0352` approves the remediation.

## Rollback Plan

If the preflight blocks a valid lane, revert only the lane-selection/preflight
change and keep the historical proof artifacts and docs. Do not restore
silent mixed-lane execution as the default, do not introduce local heavy
model/runtime hosting, and do not copy remote signing secrets locally.
