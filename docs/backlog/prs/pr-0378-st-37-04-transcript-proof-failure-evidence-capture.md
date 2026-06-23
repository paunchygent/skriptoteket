---
type: pr
id: PR-0378
title: "ST-37-04 transcript proof failure evidence capture"
status: done
owners: "agents"
created: 2026-06-23
updated: 2026-06-23
stories:
  - "ST-37-04"
tags:
  - testing
  - playwright
  - auth-edge
  - sir-convert
  - observability
dependencies:
  - "PR-0376"
  - "PR-0377"
acceptance_criteria:
  - "Given the retained Audio Transcription proof mutates HuleEdu Gateway and Skriptoteket producer containers before running Playwright, when the proof fails, then the launcher captures bounded, redacted, pre-cleanup runtime evidence from the actual Gateway, web, and worker containers before restoring runtime state."
  - "Given proof failure root cause is not yet established, when the launcher writes `failure-summary.json`, then it includes structured runtime evidence and a coarse failure classification for Gateway, Skriptoteket web, Skriptoteket worker, Sir Convert readyz/remote-proof, tunnel/network, or unknown."
  - "Given proof artifacts can include sensitive operational output, when runtime evidence is captured, then logs are bounded, redacted, and written under `.artifacts/transcript-parity-proof-lane/<timestamp>/` without env dumps, secrets, cookies, bearer tokens, API keys, passwords, or media payloads."
  - "Given product behavior must not be changed before evidence exists, when this slice closes, then no Audio Transcription UI polling retry/resilience behavior is implemented; that idea remains deferred until retained evidence identifies an actual transient failure class."
---

# PR-0378: ST-37-04 Transcript Proof Failure Evidence Capture

## Problem

`PR-0376` and `PR-0377` made the retained Audio Transcription proof reach the
real Gateway-backed Playwright polling path. A live proof then failed with a
Gateway `502 EXTERNAL_SERVICE_ERROR` while the downstream Sir Convert job still
appeared to be running. That observation is not enough to classify the product
failure as a safe transient UI retry case: the launcher currently restores the
mutated containers before preserving enough runtime evidence from the actual
Gateway, web, and worker containers.

## Goal

Strengthen `pdm run transcript-parity-proof remote-proof` so proof failures
after runtime mutation capture bounded, redacted, pre-cleanup evidence from the
actual containers involved. The evidence should help distinguish Gateway,
Skriptoteket web, Skriptoteket worker, Sir Convert remote-proof/readyz,
tunnel/network, and unknown failure classes.

## Non-goals

- No product UI polling retry or resilience behavior.
- No Gateway transport, proxy, HuleEdu auth ceremony, Sir Convert runtime, or
  PR-0377 proof-script surface rename.
- No env dumps, secrets, media payloads, unbounded logs, or browser-held
  credentials.
- No attempt to fix the observed `502` root cause until retained evidence
  identifies the responsible failure class.

## Implementation plan

1. Add red-first launcher tests proving proof failure after runtime mutation
   collects evidence before cleanup, preserves the primary
   `transcript_parity_proof_failed` error, writes bounded/redacted artifacts,
   and records runtime evidence in `failure-summary.json`.
2. Add a small runtime evidence helper if needed so the already-large launcher
   does not absorb container log and inspect mechanics.
3. Capture evidence from the exact containers:
   - `huleedu_api_gateway_service`
   - `skriptoteket_web`
   - `skriptoteket_worker`
4. Use bounded `docker logs --tail ...` and lightweight container state
   inspection. Redact sensitive header, bearer, token, secret, password, and
   API-key forms before writing output.
5. Write evidence under `.artifacts/transcript-parity-proof-lane/<timestamp>/`
   and include relative artifact paths plus classification fields in
   `failure-summary.json`.
6. Keep cleanup running after evidence capture and preserve the primary failure
   when cleanup also fails.

## Test plan

- Red first:
  `pdm run test tests/unit/scripts/test_transcript_parity_proof_launcher.py -k "runtime_evidence"`
- Green:
  `pdm run test tests/unit/scripts/test_transcript_parity_proof_launcher.py -k "runtime_evidence"`
- Full launcher/dev-stack proof:
  `pdm run test tests/unit/scripts/test_dev_stack.py tests/unit/scripts/test_transcript_parity_proof_launcher.py`
- Adjacent proof-script suite if touched:
  `pdm run test tests/unit/scripts/test_audio_transcription_parity_progress_snapshot.py tests/unit/scripts/test_audio_transcription_parity_summary_truthfulness.py tests/unit/scripts/test_sir_convert_trust_lane_preflight.py tests/unit/scripts/test_playwright_script_surface.py`
- Close-out:
  `pdm run docs-validate`
  `pdm run handoff-validate`
  `git diff --check`

## Rollback plan

Remove the runtime evidence collection helper, launcher call site, and focused
tests. The launcher then returns to writing only its existing failure summary
before cleanup.

## Deferred Product Behavior

The previous UI polling retry idea is explicitly deferred. A product retry
policy may be planned only after retained proof evidence identifies the observed
failure as an actual transient class that is safe to tolerate in the
Audio Transcription runtime.

## Implementation summary

- Removed the unaccepted product UI polling retry experiment from
  `useTranscriptGatewayRuntime.ts` and its focused spec; this slice does not
  change Audio Transcription runtime polling behavior.
- Added `scripts/_transcript_parity_runtime_evidence.py` for bounded,
  redacted runtime evidence capture.
- `scripts/transcript_parity_proof_launcher.py` now captures runtime evidence
  only when the primary failure is `transcript_parity_proof_failed` after both
  HuleEdu Gateway and Skriptoteket producer runtime mutation have occurred.
- Evidence is captured before cleanup restore/recreate commands run, and
  cleanup still runs afterward while preserving the primary failure.
- Evidence targets the actual containers:
  `huleedu_api_gateway_service`, `skriptoteket_web`, and
  `skriptoteket_worker`.
- Evidence artifacts are written under
  `.artifacts/transcript-parity-proof-lane/<timestamp>/runtime-evidence/`.
  Each container gets bounded `*.inspect.txt` and `*.logs.txt` artifacts.
- Logs use `docker logs --tail 160` plus a 4,000-character artifact cap. Text is
  redacted before writing with the launcher redaction helpers for
  `Authorization`, `Cookie`, `Set-Cookie`, bearer tokens, secret/token/password
  assignments, API keys, and matching secret-like environment values.
- Review-fix pass for `REV-PR-0378` added line-oriented JSON parsing before
  artifact writes. JSON log objects are recursively redacted for sensitive keys
  including `authorization`, `proxy_authorization`, `cookie`, `set_cookie`,
  `session`, `csrf`, `xsrf`, `bearer`, `token`, `secret`, `password`,
  `passwd`, `api_key`, `x_api_key`, and private-key variants, while non-JSON
  lines still use the plain-text/header/bearer fallback redaction.
- `failure-summary.json` now includes a structured `runtime_evidence` object
  with artifact paths, return codes, truncation flags, and a coarse
  classification such as `gateway`, `skriptoteket_web`,
  `skriptoteket_worker`, `sir_convert_remote_proof_readyz`,
  `tunnel_network`, or `unknown`.

## Validation

| Command | Outcome |
|---------|---------|
| `pdm run test tests/unit/scripts/test_transcript_parity_proof_launcher.py -k "runtime_evidence"` | Red before implementation: failed because no `docker inspect` / `docker logs --tail 160` evidence commands ran before cleanup. |
| `pdm run test tests/unit/scripts/test_transcript_parity_proof_launcher.py -k "runtime_evidence"` | Green after implementation: passed, 1 selected test. |
| `pdm run test tests/unit/scripts/test_transcript_parity_proof_launcher.py -k "runtime_evidence"` | Review-fix red before JSON sanitizer: failed because structured JSON log secret values remained in `runtime-evidence/*.logs.txt`. |
| `pdm run test tests/unit/scripts/test_transcript_parity_proof_launcher.py -k "runtime_evidence"` | Review-fix green after JSON sanitizer: passed, 2 selected tests. |
| `pdm run test tests/unit/scripts/test_dev_stack.py tests/unit/scripts/test_transcript_parity_proof_launcher.py` | Passed, 24 tests. |
| `pdm run test tests/unit/scripts/test_audio_transcription_parity_progress_snapshot.py tests/unit/scripts/test_audio_transcription_parity_summary_truthfulness.py tests/unit/scripts/test_sir_convert_trust_lane_preflight.py tests/unit/scripts/test_playwright_script_surface.py` | Passed, 36 tests. |
| `pdm run transcript-parity-proof remote-proof` | Close-out rerun initially failed early with `huleedu_auth_integration_check_failed` after the launcher recreated the Gateway; immediate `pdm run run-local-pdm auth-integration check --timeout-seconds 15` from the HuleEdu repo passed. Second run passed. Launch artifact: `.artifacts/transcript-parity-proof-lane/20260623T070624Z/`. Proof artifact: `.artifacts/audio-transcription-parity-live/20260623T070653Z/proof-summary.json` with `status=passed`, `service_profile=remote-proof`, matching Gateway/trusted fingerprints, transcript success, formatter exports, downloads, and Mina filer save. Cleanup restored Gateway to `http://host.docker.internal:8085`, Skriptoteket web/worker to `http://host.docker.internal:28085`, and closed local `38085`. |
| `pdm run docs-validate` | Passed. |
| `pdm run handoff-validate` | Passed. |
| `git diff --check` | Passed. |
