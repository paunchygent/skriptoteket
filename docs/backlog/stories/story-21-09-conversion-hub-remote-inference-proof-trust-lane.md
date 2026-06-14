---
type: story
id: ST-21-09
title: "Conversion Hub remote inference proof trust lane"
status: in_progress
owners: "agents"
created: 2026-06-14
updated: 2026-06-14
epic: "EPIC-21"
dependencies:
  - "ST-21-06"
  - "ST-21-08"
  - "HuleEdu Sir Convert Gateway internal identity trust profile"
  - "Sir Convert hosted model/runtime estate"
acceptance_criteria:
  - "Given local developer machines must not host the Sir Convert model/runtime estate, when a Conversion Hub proof needs real model-backed producer work, then the proof path uses remote Sir Convert compute rather than local hosting of STT, diarization, alignment, OCR/vision, LLM/enrichment, or future heavy model workers."
  - "Given a transcript proof uses remote Sir Convert compute, when the local signer identity, remote Sir Convert verifier trust profile, or product-backend formatter producer target is not the same sanctioned lane, then the default proof command blocks before media upload or job creation with a deterministic trust-lane diagnostic."
  - "Given future agents run the documented default transcript live proof, when they use local Skriptoteket UI/backend with remote compute, then the command selects a sanctioned remote-inference proof lane or fails closed instead of silently using a local HuleEdu Gateway signer or stale local product-backend producer target against a Hemma Sir Convert verifier."
  - "Given a mixed local-Gateway to Hemma-Sir-Convert tunnel is needed for debugging, when it is used, then it requires explicit opt-in plus public-key fingerprint/profile verification and records only redacted public metadata."
  - "Given the remediation is complete, when docs, tests, and handoff are reviewed, then the trust-lane invariant is discoverable from governed backlog/docs and enforced by tooling rather than remembered from a prior failed session."
ui_impact: "No direct teacher-facing UI impact; this hardens live proof and agent workflow defaults for the transcript lane."
data_impact: "No production data model impact; proof artifacts gain deterministic preflight status metadata."
---

# ST-21-09: Conversion Hub Remote Inference Proof Trust Lane

## Context

Conversion Hub live proof depends on real Sir Convert hosted producer
runtime. Transcript proof currently exercises speech-to-text, diarization, and
alignment, while other Conversion Hub paths may exercise OCR/vision,
LLM/enrichment, correction/replay, or future heavy model workers. None of that
hosted model/runtime estate is a reasonable default for a local developer
machine.

The recurring live-proof failure is therefore not solved by making every local
proof host Sir Convert's hosted runtime estate. The robust default is remote
inference with a coherent internal identity lane.

On 2026-06-14, an early local `PR-0351` transcript proof loaded the HuleEdu
browser-session route and captured progress/cancel surfaces, then failed
before transcript completion because the Gateway path reached Sir Convert with
a misaligned internal identity:
`POST /sir-convert/v2/convert/jobs?wait_seconds=0` returned
`auth_invalid_internal_identity` /
`invalid_internal_identity_signature`.
The failure artifact is retained at
`.artifacts/playwright-pr-0349-transcript-parity-live/20260614T082007Z/proof-summary.json`.

Later Docker-backed local proof diagnosed the durable failure mode more
precisely: the local proof preflight could target the sanctioned remote-proof
tunnel while the running `skriptoteket_web` product backend still held
`SIR_CONVERT_A_LOT_V2_BASE_URL=http://host.docker.internal:8085`, so formatter
export used a stale local CPU-debug producer lane. The retained no-mutation
guard artifact is
`.artifacts/playwright-pr-0349-transcript-parity-live/20260614T164128Z/proof-summary.json`.

That class of failure must become a tooling-level preflight/runtime-container
blocker and a documented default, not session memory.

## Scope

- Define the sanctioned Conversion Hub live-proof lanes for local UI/backend
  with remote Sir Convert hosted-model compute, with transcript proof as the
  first enforced consumer.
- Make the default proof command fail closed before upload/job creation when a
  local signer is pointed at a remote verifier that does not trust it or when
  the running local product backend still targets a different formatter
  producer lane.
- Preserve the production/Hemma proof path as the normal completion-path proof
  when remote compute and Hemma trust are required.
- Allow a mixed local-Gateway tunnel only as explicit debugging with
  fingerprint/profile verification.
- Persist the lane-selection rule in backlog/docs, handoff, and tests so
  future agents discover it before running proof.

## Non-Goals

- No local hosting of Sir Convert's heavy model/runtime estate as the default
  proof requirement, including STT, diarization, alignment, OCR/vision,
  LLM/enrichment, correction/replay workers, or future model workers.
- No copying Hemma private keys or production signer secrets to local
  developer machines.
- No direct browser calls to Sir Convert and no browser-visible service
  credentials.
- No product-backend credential POST shortcuts, local session-cookie shortcuts,
  or proof derived from direct upstream calls.
- No success claim based on a proof that bypasses the HuleEdu browser-session
  ceremony.

## Implementation Slices

- `PR-0352` is implemented and live-proofed locally and on Hemma production,
  and is awaiting independent review approval. It adds the transcript
  live-proof trust-lane preflight and makes remote inference with coherent
  trust the default behavior.

## Evidence

- Local remote-proof STT E2E proof passed with retained artifact
  `.artifacts/playwright-pr-0349-transcript-parity-live/20260614T184817Z/proof-summary.json`.
- Native Hemma production STT E2E proof passed with retained artifact
  `/home/paunchygent/apps/skriptoteket/.artifacts/playwright-pr-0352-transcript-parity-native/20260614T191738Z/proof-summary.json`.
- Container-log evidence for the successful native proof is retained at
  `/home/paunchygent/apps/skriptoteket/.artifacts/pr-0352-native-proof-logs/20260614T191737Z/`.
