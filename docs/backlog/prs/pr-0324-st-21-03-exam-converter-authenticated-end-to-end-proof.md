---
type: pr
id: PR-0324
title: "ST-21-03 Exam Converter authenticated end-to-end proof"
status: canceled
owners: "agents"
created: 2026-05-13
updated: 2026-06-18
stories:
  - "ST-21-03"
tags:
  - backend
  - frontend
  - authenticated
  - conversion-hub
  - sir-convert
  - huleedu
  - proof
acceptance_criteria:
  - "Given the public Exam Converter lane is approved, when this slice runs, then the authenticated lane proves submit, poll, result, artifact manifest, named download, and save-to-user-files through the HuleEdu Gateway product edge."
  - "Given authenticated conversion work is user-originated, when Skriptoteket calls conversion routes, then browser traffic uses Skriptoteket/HuleEdu Gateway paths and never sends Sir Convert service credentials, direct `convert.hule.education` calls, or a self-signed Skriptoteket identity context."
  - "Given authenticated state is account-owned, when save-to-user-files succeeds, then the proof retains sanitized evidence for owner-scoped file persistence and access checks without exposing student data, raw upstream tokens, or service credentials."
  - "Given unauthenticated users must not access the authenticated lane, when auth is missing or invalid, then submit, poll, manifest, download, and save-to-files fail closed without falling back to the public lane."
  - "Given public and authenticated lanes share teacher-facing conversion semantics, when artifacts and failures are projected, then target vocabulary, artifact labels, blocked/partial/manual-follow-up states, and correlation-id display remain compatible with the approved public proof."
---

# PR-0324: ST-21-03 Exam Converter Authenticated End-to-End Proof

## Problem

`PR-0318` introduced the authenticated Exam Converter adapter to the HuleEdu
Gateway `/sir-convert/v2/convert/...` edge, while `PR-0320` through `PR-0323`
settled and proved the anonymous public lane. `ST-21-03` still needs the
authenticated product proof that signed-in teachers can submit `.dxe` inputs,
retrieve artifacts, and save selected outputs to user files through the
Gateway-owned Sir Convert path.

Without this proof, the story would have an approved public one-time path but
no retained evidence that the authenticated persistence lane preserves the same
artifact semantics, uses the correct Gateway authority, and fails closed when
authentication is absent.

## Goal

Retain sanitized end-to-end evidence for the authenticated Exam Converter lane:

- submit a representative `.dxe` through the authenticated
  `documents.conversion_hub` flow;
- poll status, read result metadata, list the artifact manifest, and download a
  named artifact;
- save at least one generated artifact to user files and prove owner-scoped
  persistence/access behavior;
- prove missing-auth rejection on authenticated submit, status, manifest,
  download, and save-to-files actions;
- prove browser-visible traffic uses Skriptoteket/HuleEdu Gateway routes only;
  and
- compare artifact taxonomy with the approved public lane so teachers see one
  conversion product with different persistence and authority boundaries.

## Review Status

`REV-PR-0324` is still `changes_requested` until the authenticated live proof
is rerun and retained. The original preflight blockers were remediated by
`PR-0325`; the advisory/reviewed-completion follow-ups were then completed by
`PR-0326`, `PR-0328`, and `PR-0329`. The next rerun should use the same
byte-identical `.dxe` and prove advisory submit, valid AI-facit report delivery
including vision-backed `item-013`, reviewed overlay apply, refreshed
`effective_ir_json`, final target readiness, named download, save-to-user-files,
and missing-auth rejection through the HuleEdu Gateway path.

## Supersession Note (2026-06-18)

`PR-0359` cancels this slice as superseded. The original blocker was remediated
by `PR-0325`, and the Exam Converter intake/export direction has since been
narrowed by `ST-21-10`, `PR-0356`, and `PR-0357` to a source-only product
lane. Retained `REV-PR-0324` still explains why the first proof stopped, but
it is no longer the governing forward implementation slice.

## Dependencies

- Authenticated adapter slice:
  `docs/backlog/prs/pr-0318-st-21-03-authenticated-exam-converter-huleedu-sir-convert-edge.md`
- Public lane proof baseline:
  `docs/backlog/prs/pr-0322-st-21-03-exam-converter-live-upstream-public-grant-proof.md`
  and
  `docs/backlog/reviews/review-pr-0322-exam-converter-live-upstream-public-grant-proof.md`
- HuleEdu auth-edge contract:
  `/Users/olofs_mba/Documents/Repos/huleedu/docs/backlog/stories/story-01-07-expose-sir-convert-artifact-bundle-routes-through-huleedu-auth-edge.md`
  and
  `/Users/olofs_mba/Documents/Repos/huleedu/docs/backlog/tasks/task-0561-cut-skriptoteket-artifact-bundle-adapter-to-huleedu-sir-convert-edge.md`
- Sir Convert authenticated artifact-bundle runtime:
  `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/backlog/tasks/task-282-implement-digiexam-migration-service-runtime-artifact-bundle-routes.md`
  and
  `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/converters/digiexam-migration-service-api-artifact-contract.md`
- Sir Convert identity profile:
  `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/reference/ref-sir-convert-internalidentitycontextv1-authorization-profile.md`

## Non-goals

- Do not reopen the approved public grant/read-lease lane unless HuleEdu or Sir
  Convert changes the accepted contract.
- Do not add new conversion targets, editable DOCX, QTI authoring, or bulk
  migration workflow.
- Do not expose Sir Convert API keys, raw `InternalIdentityContextV1` tokens,
  HuleEdu session material, direct upstream hosts, or student-identifying
  evidence in retained docs.
- Do not implement broad runtime changes inside this proof slice. If the proof
  finds an authenticated runtime gap, stop and create a narrow remediation PR.
- Do not prove authenticated behavior by calling Sir Convert directly from the
  browser or by bypassing the HuleEdu Gateway ceremony.

## Implementation Plan

1. Confirm current HuleEdu Gateway and Sir Convert authenticated runtime
   handoff without committing secrets or token values.
2. Start the local proof environment with Skriptoteket, HuleEdu Gateway, Sir
   Convert, and the required dev database/file storage surfaces.
3. Use a representative sanitized `.dxe` input and an authenticated browser
   session established through the HuleEdu browser-session ceremony.
4. Exercise the authenticated `documents.conversion_hub` Exam Converter flow:
   submit, poll, read result metadata, list artifact manifest, download a named
   artifact, and save at least one artifact to user files.
5. Capture missing-auth rejection for each authenticated action without using
   public-route fallback behavior.
6. Inspect browser-visible bundle/API traffic for forbidden authority strings:
   direct Sir Convert hosts, `convert.hule.education` browser calls, service
   API keys, raw identity-context tokens, and local upstream dev ports.
7. Compare artifact taxonomy against `REV-PR-0322`: selected targets, artifact
   labels, `not_requested`, blocked, partial, and manual-follow-up projection
   should remain compatible.
8. Retain sanitized proof in a new `REV-PR-0324` review, then update this PR,
   `ST-21-03`, `EPIC-21`, `docs/index.md`, and `.codex/handoff.md`.

## Test Plan

- Focused backend proof for authenticated submit/status/result/manifest/named
  download through Skriptoteket and the HuleEdu Gateway path.
- Browser proof for the authenticated Conversion Hub Exam Converter flow,
  including save-to-user-files.
- Missing-auth proof for submit, status, manifest, named download, and
  save-to-files.
- Persistence proof that saved artifacts are owner-scoped and that unrelated
  accounts cannot access the saved file handles.
- Forbidden browser-authority grep over the production SPA bundle for
  `convert.hule.education`, `X-API-Key`, `SIR_CONVERT_A_LOT_V2_API_KEY`,
  `InternalIdentityContextV1`, direct Sir Convert upstream hosts, and local
  upstream dev ports.
- `pdm run lint`
- `pdm run typecheck`
- Focused backend tests for touched authenticated conversion/user-file paths
- Focused frontend tests for touched Conversion Hub/Exam Converter surfaces
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run fe-build`
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Stop Conditions

- Stop if the authenticated proof requires browser-visible Sir Convert
  credentials, raw HuleEdu identity material, direct upstream browser calls, or
  local session-cookie shortcuts.
- Stop if HuleEdu Gateway does not mint `aud=sir-convert-a-lot` identity for
  the route-appropriate authenticated Sir Convert calls.
- Stop if save-to-user-files cannot be proven without exposing student PII,
  wrong answers, scores, or performance history in retained evidence.
- Stop if public fallback behavior is used to make an authenticated proof pass.
- Stop if the artifact taxonomy diverges from the approved public lane in a way
  that needs product or contract decisions.

## Rollback Plan

No runtime rollback should be needed because this slice is proof-first. If the
proof exposes a contract or implementation gap, mark `PR-0324` blocked, retain
the finding in `REV-PR-0324`, and create a narrow remediation PR before
rerunning the authenticated proof.
