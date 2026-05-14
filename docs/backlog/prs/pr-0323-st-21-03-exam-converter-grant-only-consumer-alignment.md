---
type: pr
id: PR-0323
title: "ST-21-03 Exam Converter grant-only consumer alignment"
status: done
owners: "agents"
created: 2026-05-13
updated: 2026-05-13
stories:
  - "ST-21-03"
tags:
  - backend
  - public-access
  - conversion-hub
  - sir-convert
  - huleedu
acceptance_criteria:
  - "Given HuleEdu TASK-0565 is grant-only, when Skriptoteket mints a public Exam Converter grant, then it consumes only `public_conversion_grant`, expiry, and artifact TTL metadata from HuleEdu and never expects HuleEdu to return `PublicArtifactReadLeaseV1`."
  - "Given Sir Convert TASK-292 issues public artifact-read leases after verifying the grant, when Skriptoteket submits a public job, then it stores the Sir Convert manifest lease from the submit response and stores exact named-artifact leases from the manifest response server-side only."
  - "Given public authority must remain server-side, when Skriptoteket polls, reads results, reads manifests, or downloads artifacts, then it forwards the parent public conversion grant to Sir Convert and forwards artifact-read leases only on server-to-server artifact calls."
  - "Given the public browser must not see upstream authority, when Skriptoteket projects manifests, then raw public grants, raw read leases, Sir Convert credentials, and direct upstream hosts are stripped from browser responses."
  - "Given PR-0322 is the live proof slice, when this PR closes, then PR-0322 can be rerun without local contract drift between HuleEdu grant-only authority, Sir Convert read-lease issuance, and Skriptoteket's public runtime consumer."
---

# PR-0323: ST-21-03 Exam Converter Grant-Only Consumer Alignment

## Problem

`PR-0322` correctly blocked because Skriptoteket still modeled HuleEdu as both
grant issuer and artifact-read lease issuer. HuleEdu `TASK-0565` is explicitly
grant-only, while Sir Convert `TASK-292` is the runtime verifier and
`PublicArtifactReadLeaseV1` issuer.

## Goal

Align the Skriptoteket public Exam Converter runtime with the accepted
cross-repo contract before rerunning the PR-0322 live proof:

- HuleEdu mints only `PublicConversionGrantV1`.
- Sir Convert returns the manifest read lease on submit and per-artifact read
  leases in the manifest payload.
- Skriptoteket stores all upstream authority server-side and projects only
  public job ids, local URLs, artifact metadata, and status to the browser.

## Scope

- Update the HuleEdu grant authority client and protocol to consume the
  grant-only response shape.
- Include the public upload MIME-type set in the grant mint request.
- Generate or pass a governed registered-backend client assertion for HuleEdu
  without exposing assertion material to browsers.
- Update the Sir Convert public Exam Converter protocol/client to:
  - read the submit response's `public_artifact_read_lease`;
  - send both `X-Public-Conversion-Grant` and
    `X-Public-Artifact-Read-Lease` for artifact manifest and named download
    calls;
  - retain exact artifact read leases only in server-side transient state.
- Update public runtime handler state so manifest and named artifact leases are
  stored and refreshed server-side without leaking to browser responses.
- Keep the public SPA and browser contract unchanged except for preserving the
  absence of raw upstream authority.

## Non-goals

- Do not mint grants locally in Skriptoteket.
- Do not verify Sir Convert's public grant signature in Skriptoteket.
- Do not expose raw grants, read leases, Sir Convert API keys, HuleEdu assertion
  secrets, or direct upstream URLs to browser-visible responses.
- Do not expand the public lane beyond `digiexam_dxe ->
  examnet_migration_bundle`.
- Do not rerun PR-0322 live proof until focused local consumer tests pass.

## Implementation Summary

Implemented on 2026-05-13.

- `PublicExamConverterGrantRequest` now sends the upload MIME-type set to
  HuleEdu, and the HuleEdu client consumes only the grant-only response:
  `public_conversion_grant`, expiry, and artifact TTL metadata.
- Skriptoteket now signs the registered-backend client assertion server-side
  when a secret-backed assertion profile is configured, preserving the static
  assertion fallback for local operator handoff.
- A dedicated public Sir Convert client owns the Exam Converter parent-grant
  and read-lease header contract instead of expanding the generic v2 client.
- Submit stores the Sir Convert manifest read lease returned after grant
  verification; manifest reads collect exact per-artifact leases; downloads use
  only the exact artifact-key lease.
- Browser-facing manifest projection strips raw public grants,
  `PublicArtifactReadLeaseV1` tokens, Sir Convert credentials, and direct
  upstream hosts.

## Verification

- `pdm run pytest tests/unit/web/test_public_apps_exam_converter_runtime.py tests/unit/infrastructure/curated_apps/apps/conversion_hub/test_public_exam_converter_upstream_clients.py -q`
  (6 passed)
- `pdm run lint`
- `pdm run typecheck`
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`
