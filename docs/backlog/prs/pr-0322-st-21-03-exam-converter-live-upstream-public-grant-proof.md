---
type: pr
id: PR-0322
title: "ST-21-03 Exam Converter live upstream public grant proof"
status: done
owners: "agents"
created: 2026-05-13
updated: 2026-05-13
stories:
  - "ST-21-03"
tags:
  - backend
  - frontend
  - public-access
  - conversion-hub
  - sir-convert
  - huleedu
  - proof
acceptance_criteria:
  - "Given PR-0320 implemented the public runtime lane locally, when this proof slice runs, then submit, poll, result, artifact manifest, and named download are exercised against real HuleEdu public grant authority and real Sir Convert verifier credentials without committing secrets or token values."
  - "Given public conversion authority must remain server-side, when the live proof is captured, then the browser only talks to Skriptoteket public endpoints and never receives HuleEdu signing material, Sir Convert credentials, raw `PublicConversionGrantV1`, raw `PublicArtifactReadLeaseV1`, or direct `convert.hule.education` route authority."
  - "Given anonymous behavior must be cookie-agnostic, when the proof is repeated with and without ambient authenticated cookies, then public submit, poll, manifest, and download outcomes stay equivalent and no account-owned records are created."
  - "Given public uploads are abuse-sensitive, when live proof runs, then payload rejection, target rejection, rate-limit or concurrency rejection, TTL expiry, missing upstream configuration, and direct unsupported public routes are proven fail-closed before or without unsafe upstream use."
  - "Given the runtime proof is a governed gate, when this slice closes, then sanitized evidence, command output, browser proof, forbidden-string production-bundle grep, and any upstream environment assumptions are retained in the review/handoff docs."
---

# PR-0322: ST-21-03 Exam Converter Live Upstream Public Grant Proof

## Problem

`PR-0320` shipped the Skriptoteket public Exam Converter runtime lane and keeps
HuleEdu/Sir Convert authority server-side, but its verification deliberately
stopped short of using real upstream public grant authority and Sir Convert
verifier credentials. The story and handoff name that live proof as the next
step, but there was no repo-native task governing the evidence shape.

## Goal

Prove the implemented public runtime against the approved upstream authority:
HuleEdu `TASK-0563` / decision `0045` / `PublicConversionGrantV1`, Sir Convert
`TASK-291`, and the Skriptoteket `PR-0321` metadata/grant bridge. The proof
must retain sanitized evidence that the public browser lane works end to end
while preserving the identity, authority, privacy, and no-account-persistence
contracts.

## Review Status

Retained review `REV-PR-0322` is `approved`.

The original blockers were remediated by Sir Convert `TASK-292` and
Skriptoteket `PR-0323`. HuleEdu remains the grant-only
`PublicConversionGrantV1` authority, Sir Convert now verifies the grant and
issues `PublicArtifactReadLeaseV1` after the public-grant job/artifact
boundary, and Skriptoteket keeps both parent grants and read leases server-side.

The live proof was rerun on 2026-05-13 using local live services and generated
local-only signing material under ignored `.artifacts/`. Sanitized positive,
negative, cookie-parity, no-account-persistence, TTL-expiry, and
forbidden-browser-authority evidence is retained in
`REV-PR-0322`.

## Dependencies

- Local runtime:
  `docs/backlog/prs/pr-0320-st-21-03-exam-converter-public-one-time-runtime-lane.md`
- Local metadata/grant bridge:
  `docs/backlog/prs/pr-0321-st-21-03-exam-converter-public-active-runtime-metadata-and-grant-contract.md`
- HuleEdu public grant authority:
  `/Users/olofs_mba/Documents/Repos/huleedu/docs/backlog/tasks/task-0563-define-public-exam-converter-grant-authority-for-sir-convert.md`
- HuleEdu accepted decision and contract:
  `/Users/olofs_mba/Documents/Repos/huleedu/docs/decisions/0045-public-exam-converter-grant-authority-for-sir-convert.md`
  and
  `/Users/olofs_mba/Documents/Repos/huleedu/docs/reference/ref-public-exam-converter-grant-v1-contract.md`
- Sir Convert public verifier lane:
  `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/backlog/tasks/task-291-define-public-exam-converter-grant-lane-for-digiexam-migration-bundles.md`
- Sir Convert runtime verifier/read-lease implementation:
  `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/backlog/tasks/task-292-implement-public-exam-converter-grant-verifier-and-read-leases.md`
- Sir Convert DigiExam artifact contract:
  `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/converters/digiexam-migration-service-api-artifact-contract.md`
- HuleEdu grant minting implementation:
  `/Users/olofs_mba/Documents/Repos/huleedu/docs/backlog/tasks/task-0565-implement-public-exam-converter-grant-minting-endpoint.md`
- Skriptoteket grant-only consumer alignment:
  `docs/backlog/prs/pr-0323-st-21-03-exam-converter-grant-only-consumer-alignment.md`

## Non-goals

- Adding new public runtime behavior beyond what `PR-0320` already shipped.
- Exposing secrets, raw grants, read leases, upstream hosts, or token payloads in
  retained proof artifacts.
- Reopening authenticated save-to-user-files implementation scope.
- Turning the scoped public Exam Converter lane into general public Conversion
  Hub access.
- Treating local mock upstream responses as sufficient live proof.

## Implementation Summary

Executed on 2026-05-13 after HuleEdu `TASK-0565`, Sir Convert `TASK-292`, and
Skriptoteket `PR-0323` were in place.

- Prepared a live-proof environment using secret-backed configuration for the
  HuleEdu public grant authority and Sir Convert verifier/read-lease runtime.
  Credential values, token values, token payloads, signing keys, and API keys
  were kept out of governed docs.
- Used a representative `.dxe` input and exercised the Skriptoteket public API
  namespace only:
  `/api/v1/public/apps/documents.conversion_hub/exam-converter/...`.
- Proved submit, status polling, result retrieval, artifact manifest, and named
  artifact download across Skriptoteket, HuleEdu Gateway, and Sir Convert.
- Repeated status, manifest, and download calls with a synthetic ambient cookie
  and observed equivalent public behavior without account-owned persistence.
- Captured fail-closed evidence for invalid target, missing `.dxe`, unsupported
  public root, missing job artifact manifest, anonymous rate limiting, and
  expired public grants.
- Built the production SPA bundle and grepped it for direct upstream authority
  strings, service API keys, raw public grant/read-lease contract names, and
  local upstream development ports.

## Test Plan

- Focused backend proof commands for public submit/status/result/manifest/named
  download using real HuleEdu public grant authority and Sir Convert verifier
  configuration.
- Browser proof that the public route renders, submits, polls, and downloads
  through Skriptoteket public URLs only.
- Cookie-parity proof for submit, poll, manifest, and download with and without
  ambient authenticated cookies.
- Persistence proof that no Vault/MyFiles rows, owner-scoped conversion jobs,
  guest recovery records, or account history entries are created.
- Negative proof for invalid payloads, unsupported targets, missing `.dxe`,
  rate/concurrency rejection, TTL expiry, missing upstream config, and
  unsupported public app routes.
- Production bundle grep:
  `convert.hule.education`, `X-API-Key`, `SIR_CONVERT_A_LOT_V2_API_KEY`,
  `127.0.0.1:9010`, `PublicConversionGrantV1`, and
  `PublicArtifactReadLeaseV1` must not appear.
- `pdm run lint`
- `pdm run typecheck`
- `pdm run fe-test` with touched frontend specs
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run fe-build`
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Proof Results

Positive public proof passed:

- submit returned `200` and a local public job id;
- status returned `200` with `succeeded`;
- result returned `200` with the local artifact manifest URL;
- manifest returned `200` with nine artifact entries and no raw grant/read
  lease fields;
- named `ir_json` download returned `200`, `application/json`, filename
  `digiexam-ir.json`, and 22025 bytes.

Cookie-parity proof passed for status, manifest, and named download.

No-account-persistence proof passed: `conversion_hub_jobs` and `tool_runs`
remained at `0`; pre-existing `user_vault_files` and `user_vault_usage` counts
were unchanged by the public path.

Forbidden browser-authority grep returned no matches for
`convert.hule.education`, `X-API-Key`, `SIR_CONVERT_A_LOT_V2_API_KEY`,
`127.0.0.1:9010`, `PublicConversionGrantV1`, or
`PublicArtifactReadLeaseV1`.

## Stop Conditions

- Stop if the proof requires browser-visible Sir Convert credentials, direct
  `convert.hule.education` browser calls, raw public grants, raw artifact-read
  leases, or HuleEdu signing material.
- Stop if Skriptoteket expects HuleEdu's mint response to include
  `public_artifact_read_lease` or `artifact_read_lease`; HuleEdu is grant-only,
  and Sir Convert is the read-lease issuer after it verifies the grant and
  creates the public-grant-owned job/artifact boundary.
- Stop if Sir Convert runtime verifier/read-lease implementation evidence is
  absent from the current checkout; completed contract docs are not sufficient
  for this live proof slice.
- Stop if public endpoints behave differently because a user is logged in.
- Stop if live conversion can only be proven by widening general Conversion Hub
  public access.
- Stop if the only available upstream path is mock/fake authority rather than
  real HuleEdu public grant authority and real Sir Convert verifier acceptance.
- Stop if representative inputs contain student identity, scores, wrong answers,
  or performance history that cannot be sanitized for retained evidence.

## Rollback Plan

No runtime rollback should be needed because this slice is proof-only. If the
proof exposes a contract regression, mark `PR-0322` blocked, reopen `PR-0320`
with a retained review finding, and disable the public runtime affordance until
the failing boundary has a governed remediation slice.
